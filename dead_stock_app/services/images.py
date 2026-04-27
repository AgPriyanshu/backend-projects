import os
import uuid

from shared.infrastructure import InfraManager

CONTENT_TYPE_TO_EXT = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}

PRESIGN_TTL_SECONDS = 3600


def build_original_key(item_id, content_type: str) -> str:
    ext = CONTENT_TYPE_TO_EXT.get(content_type)
    if not ext:
        raise ValueError(f"Unsupported content_type: {content_type}")
    return f"dead-stock/items/{item_id}/originals/{uuid.uuid4()}.{ext}"


def presign_put(item_id, content_type: str) -> dict:
    key = build_original_key(item_id, content_type)
    url = InfraManager.object_storage.generate_presigned_url(
        key=key,
        method="PUT",
        expiration=PRESIGN_TTL_SECONDS,
    )
    return {
        "url": url,
        "key": key,
        "expires_in": PRESIGN_TTL_SECONDS,
        "headers": {"Content-Type": content_type},
        "bucket": os.environ.get("S3_BUCKET"),
    }


def delete_object(key: str) -> bool:
    try:
        return InfraManager.object_storage.delete_object(key=key)
    except Exception:
        return False
