import base64
import json
import logging

from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D
from django.contrib.postgres.search import SearchQuery
from django.db.models import Q

from ..models import InventoryItem, SearchLog

logger = logging.getLogger(__name__)

VALID_SORTS = {"distance", "recent", "price"}
DEFAULT_LIMIT = 20
MAX_LIMIT = 100
DEFAULT_RADIUS_KM = 10


def _encode_cursor(sort: str, last_value, last_id: str) -> str:
    payload = {"sort": sort, "v": last_value, "id": last_id}
    return base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()


def _decode_cursor(cursor: str) -> dict | None:
    try:
        payload = json.loads(base64.urlsafe_b64decode(cursor.encode()))

        if {"sort", "v", "id"} <= payload.keys():
            return payload
    except Exception:
        pass
    return None


def build_search_qs(
    q: str = "",
    lat: float | None = None,
    lng: float | None = None,
    radius_km: float = DEFAULT_RADIUS_KM,
    category_slug: str = "",
    min_price: float | None = None,
    max_price: float | None = None,
    sort: str = "distance",
    cursor: str = "",
    limit: int = DEFAULT_LIMIT,
) -> tuple[list, str | None]:
    """
    Returns (items_list, next_cursor).
    Geo queries annotate each item with a .distance attribute (Distance object).
    """
    if sort not in VALID_SORTS:
        sort = "distance"

    limit = min(limit, MAX_LIMIT)
    fetch = limit + 1

    qs = (
        InventoryItem.objects.filter(status=InventoryItem.Status.ACTIVE)
        .select_related("shop", "category")
        .prefetch_related("images")
    )

    point = None
    if lat is not None and lng is not None:
        point = Point(lng, lat, srid=4326)
        qs = qs.filter(shop__location__dwithin=(point, D(km=radius_km)))
        qs = qs.annotate(distance=Distance("shop__location", point))

    if q:
        qs = qs.filter(
            Q(search_vector=SearchQuery(q, config="simple"))
            | Q(name_normalized__trigram_similar=q.lower())
        )

    if category_slug:
        qs = qs.filter(category__slug=category_slug)

    if min_price is not None:
        qs = qs.filter(price__gte=min_price)

    if max_price is not None:
        qs = qs.filter(price__lte=max_price)

    decoded = _decode_cursor(cursor) if cursor else None

    if sort == "distance" and point is not None:
        qs = qs.order_by("distance", "id")

        if decoded and decoded.get("sort") == "distance":
            last_dist = float(decoded["v"])
            last_id = decoded["id"]
            qs = qs.filter(
                Q(distance__gt=D(m=last_dist))
                | Q(distance=D(m=last_dist), id__gt=last_id)
            )
    elif sort == "price":
        qs = qs.order_by("price", "id")

        if decoded and decoded.get("sort") == "price":
            last_price = decoded["v"]
            last_id = decoded["id"]
            qs = qs.filter(
                Q(price__gt=last_price) | Q(price=last_price, id__gt=last_id)
            )
    else:
        sort = "recent"
        qs = qs.order_by("-created_at", "id")

        if decoded and decoded.get("sort") == "recent":
            last_ts = decoded["v"]
            last_id = decoded["id"]
            qs = qs.filter(
                Q(created_at__lt=last_ts) | Q(created_at=last_ts, id__gt=last_id)
            )

    items = list(qs[:fetch])
    has_next = len(items) > limit

    if has_next:
        items = items[:limit]

    next_cursor = None

    if has_next and items:
        last = items[-1]

        if sort == "distance" and point is not None:
            dist = getattr(last, "distance", None)
            last_val = round(dist.m, 3) if dist else 0.0
        elif sort == "price":
            last_val = float(last.price) if last.price is not None else 0.0
        else:
            last_val = last.created_at.isoformat()

        next_cursor = _encode_cursor(sort, last_val, str(last.id))

    return items, next_cursor


def log_search(
    query: str,
    result_count: int,
    lat: float | None = None,
    lng: float | None = None,
    user=None,
) -> None:
    try:
        point = (
            Point(lng, lat, srid=4326)
            if lat is not None and lng is not None
            else None
        )
        SearchLog.objects.create(
            query=query,
            result_count=result_count,
            location=point,
            user=user if (user and user.is_authenticated) else None,
        )
    except Exception:
        logger.exception("Failed to log search.")
