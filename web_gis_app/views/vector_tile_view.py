"""Serve Mapbox Vector Tiles (MVT) for vector datasets via PostGIS ST_AsMVT."""

import logging

import mercantile
from django.db import connection
from django.http import HttpResponse
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Dataset

logger = logging.getLogger(__name__)


class VectorTileView(APIView):
    """
    Serve MVT tiles for a vector dataset.

    GET /web-gis/datasets/<dataset_id>/vector-tiles/<z>/<x>/<y>.mvt
    """

    permission_classes = [AllowAny]

    def get(self, request, pk, z, x, y):
        """Return a binary MVT tile for the given ZXY coordinates."""
        try:
            dataset = Dataset.objects.get(pk=pk)
        except Dataset.DoesNotExist:
            return Response(
                {"error": "Dataset not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if dataset.type != "vector":
            return Response(
                {"error": "Dataset is not a vector dataset."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Convert tile coordinates to Web Mercator (EPSG:3857) bounds.
        tile = mercantile.Tile(x=x, y=y, z=z)
        bounds = mercantile.xy_bounds(tile)

        tile_envelope = (
            f"ST_MakeEnvelope({bounds.left}, {bounds.bottom}, "
            f"{bounds.right}, {bounds.top}, 3857)"
        )

        sql = f"""
            SELECT ST_AsMVT(tile_data, 'features', 4096, 'geom')
            FROM (
                SELECT
                    f.id::text AS id,
                    f.properties,
                    ST_AsMVTGeom(
                        ST_Transform(f.geometry, 3857),
                        {tile_envelope},
                        4096,
                        256,
                        true
                    ) AS geom
                FROM feature f
                WHERE f.dataset_id = %s
                  AND ST_Intersects(
                      ST_Transform(f.geometry, 3857),
                      {tile_envelope}
                  )
            ) AS tile_data
            WHERE geom IS NOT NULL
        """

        try:
            with connection.cursor() as cursor:
                cursor.execute(sql, [str(pk)])
                row = cursor.fetchone()

            mvt_data = bytes(row[0]) if row and row[0] else b""

            return HttpResponse(
                mvt_data,
                content_type="application/x-protobuf",
                status=200,
            )

        except Exception as e:
            logger.exception("Error generating vector tile z=%s/x=%s/y=%s: %s", z, x, y, e)
            return Response(
                {"error": f"Failed to generate tile: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
