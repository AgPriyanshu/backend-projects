from __future__ import annotations

from typing import Optional

from django.contrib.gis.geos import GEOSGeometry

from shared.workflows import Operation

from ...models import Feature, ProcessingJob
from ..helpers import create_staging_dataset, report_progress
from .schemas import BasePayload, BufferOpPayload


class BufferOp(Operation[BufferOpPayload, dict]):
    """Create a PostGIS buffer around every feature in the input dataset."""

    name = "buffer_op"

    def execute(self, *args, **kwargs) -> dict:
        job = ProcessingJob.objects.get(pk=self.payload.job_id)
        staging = create_staging_dataset(job.user)

        distance_meters = self._to_meters(self.payload.distance, self.payload.units)

        report_progress(self.ctx, 10, "Buffering features...")

        features = Feature.objects.filter(dataset_id=self.payload.input_dataset_id)
        total = features.count()

        if total == 0:
            self.ctx["pending_feature_dataset_id"] = str(staging.id)
            return {"feature_count": 0}

        batch = []

        for index, feature in enumerate(features.iterator()):
            buffered = self._buffer_geometry(feature.geometry, distance_meters)
            batch.append(
                Feature(
                    dataset=staging,
                    geometry=buffered,
                    properties=feature.properties,
                )
            )

            if len(batch) >= 500:
                Feature.objects.bulk_create(batch)
                batch = []

            if index % 50 == 0:
                report_progress(
                    self.ctx,
                    10 + int(80 * (index + 1) / total),
                    f"Buffered {index + 1}/{total} features",
                )

        if batch:
            Feature.objects.bulk_create(batch)

        self.ctx["pending_feature_dataset_id"] = str(staging.id)

        return {"feature_count": total}

    @staticmethod
    def _to_meters(distance: float, units: str) -> float:
        if units == "kilometers":
            return distance * 1000
        if units == "degrees":
            # Rough conversion: 1 degree ~= 111 km at the equator.
            return distance * 111_000

        return distance

    @staticmethod
    def _buffer_geometry(geom, distance_meters: float):
        """Buffer a 4326 geometry using PostGIS via a raw SQL round-trip."""

        from django.db import connection

        srid = geom.srid or 4326

        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT encode(ST_AsEWKB("
                "  ST_Buffer(ST_GeomFromEWKT(%s)::geography, %s)::geometry"
                "), 'hex')",
                [f"SRID={srid};{geom.wkt}", distance_meters],
            )
            row = cursor.fetchone()

        return GEOSGeometry(row[0])


class ClipVectorOpPayload(BasePayload):
    clip_dataset_id: str


class ClipVectorOp(Operation[ClipVectorOpPayload, dict]):
    """Clip input features by the union of features in a clip dataset."""

    name = "clip_vector_op"

    def execute(self, *args, **kwargs) -> dict:
        job = ProcessingJob.objects.get(pk=self.payload.job_id)
        staging = create_staging_dataset(job.user)

        report_progress(self.ctx, 10, "Clipping features...")

        from django.db import connection

        # Insert intersection features directly via SQL for performance.
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO feature (id, dataset_id, geometry, properties, created_at, updated_at)
                SELECT
                    gen_random_uuid(),
                    %s,
                    ST_Multi(ST_Intersection(a.geometry, clip.geom)),
                    a.properties,
                    NOW(),
                    NOW()
                FROM feature a
                CROSS JOIN (
                    SELECT ST_Union(geometry) AS geom FROM feature WHERE dataset_id = %s
                ) AS clip
                WHERE a.dataset_id = %s
                  AND ST_Intersects(a.geometry, clip.geom)
                  AND NOT ST_IsEmpty(ST_Intersection(a.geometry, clip.geom))
                """,
                [
                    str(staging.id),
                    self.payload.clip_dataset_id,
                    self.payload.input_dataset_id,
                ],
            )

        self.ctx["pending_feature_dataset_id"] = str(staging.id)
        report_progress(self.ctx, 90, "Clip complete")

        return {}


class DissolveOpPayload(BasePayload):
    dissolve_field: Optional[str] = None


class DissolveOp(Operation[DissolveOpPayload, dict]):
    """Merge features via ST_Union, optionally grouped by a properties field."""

    name = "dissolve_op"

    def execute(self, *args, **kwargs) -> dict:
        job = ProcessingJob.objects.get(pk=self.payload.job_id)
        staging = create_staging_dataset(job.user)

        report_progress(self.ctx, 10, "Dissolving features...")

        if (
            Feature.objects.filter(dataset_id=self.payload.input_dataset_id).count()
            == 0
        ):
            self.ctx["pending_feature_dataset_id"] = str(staging.id)
            return {"feature_count": 0}

        from django.db import connection

        if self.payload.dissolve_field:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO feature (id, dataset_id, geometry, properties, created_at, updated_at)
                    SELECT
                        gen_random_uuid(),
                        %s,
                        ST_Multi(ST_Union(geometry)),
                        jsonb_build_object(%s, properties->>%s),
                        NOW(),
                        NOW()
                    FROM feature
                    WHERE dataset_id = %s
                    GROUP BY properties->>%s
                    HAVING ST_Union(geometry) IS NOT NULL
                    """,
                    [
                        str(staging.id),
                        self.payload.dissolve_field,
                        self.payload.dissolve_field,
                        self.payload.input_dataset_id,
                        self.payload.dissolve_field,
                    ],
                )
        else:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO feature (id, dataset_id, geometry, properties, created_at, updated_at)
                    SELECT
                        gen_random_uuid(),
                        %s,
                        ST_Multi(ST_Union(geometry)),
                        '{}'::jsonb,
                        NOW(),
                        NOW()
                    FROM feature
                    WHERE dataset_id = %s
                    HAVING ST_Union(geometry) IS NOT NULL
                    """,
                    [str(staging.id), self.payload.input_dataset_id],
                )

        self.ctx["pending_feature_dataset_id"] = str(staging.id)
        report_progress(self.ctx, 90, "Dissolve complete")

        return {}


class CentroidOpPayload(BasePayload):
    pass


class CentroidOp(Operation[CentroidOpPayload, dict]):
    """Compute a centroid point for every feature."""

    name = "centroid_op"

    def execute(self, *args, **kwargs) -> dict:
        job = ProcessingJob.objects.get(pk=self.payload.job_id)
        staging = create_staging_dataset(job.user)

        report_progress(self.ctx, 10, "Computing centroids...")

        from django.db import connection

        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO feature (id, dataset_id, geometry, properties, created_at, updated_at)
                SELECT
                    gen_random_uuid(),
                    %s,
                    ST_Centroid(geometry),
                    properties,
                    NOW(),
                    NOW()
                FROM feature
                WHERE dataset_id = %s
                """,
                [str(staging.id), self.payload.input_dataset_id],
            )

        self.ctx["pending_feature_dataset_id"] = str(staging.id)
        report_progress(self.ctx, 90, "Centroid complete")

        return {}


class SimplifyOpPayload(BasePayload):
    tolerance: float


class SimplifyOp(Operation[SimplifyOpPayload, dict]):
    """Apply ST_Simplify to every feature geometry."""

    name = "simplify_op"

    def execute(self, *args, **kwargs) -> dict:
        job = ProcessingJob.objects.get(pk=self.payload.job_id)
        staging = create_staging_dataset(job.user)

        report_progress(self.ctx, 10, "Simplifying geometries...")

        from django.db import connection

        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO feature (id, dataset_id, geometry, properties, created_at, updated_at)
                SELECT
                    gen_random_uuid(),
                    %s,
                    ST_Simplify(geometry, %s),
                    properties,
                    NOW(),
                    NOW()
                FROM feature
                WHERE dataset_id = %s
                  AND ST_Simplify(geometry, %s) IS NOT NULL
                """,
                [
                    str(staging.id),
                    self.payload.tolerance,
                    self.payload.input_dataset_id,
                    self.payload.tolerance,
                ],
            )

        self.ctx["pending_feature_dataset_id"] = str(staging.id)
        report_progress(self.ctx, 90, "Simplify complete")

        return {}


class ConvexHullOpPayload(BasePayload):
    per_feature: bool = False


class ConvexHullOp(Operation[ConvexHullOpPayload, dict]):
    """Compute a convex hull, either per feature or as a single hull over all features."""

    name = "convex_hull_op"

    def execute(self, *args, **kwargs) -> dict:
        job = ProcessingJob.objects.get(pk=self.payload.job_id)
        staging = create_staging_dataset(job.user)

        report_progress(self.ctx, 10, "Computing convex hull...")

        if (
            Feature.objects.filter(dataset_id=self.payload.input_dataset_id).count()
            == 0
        ):
            self.ctx["pending_feature_dataset_id"] = str(staging.id)
            return {"feature_count": 0}

        from django.db import connection

        if self.payload.per_feature:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO feature (id, dataset_id, geometry, properties, created_at, updated_at)
                    SELECT
                        gen_random_uuid(),
                        %s,
                        ST_ConvexHull(geometry),
                        properties,
                        NOW(),
                        NOW()
                    FROM feature
                    WHERE dataset_id = %s
                      AND geometry IS NOT NULL
                    """,
                    [str(staging.id), self.payload.input_dataset_id],
                )
        else:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO feature (id, dataset_id, geometry, properties, created_at, updated_at)
                    SELECT
                        gen_random_uuid(),
                        %s,
                        ST_ConvexHull(ST_Collect(geometry)),
                        '{}'::jsonb,
                        NOW(),
                        NOW()
                    FROM feature
                    WHERE dataset_id = %s
                    HAVING ST_ConvexHull(ST_Collect(geometry)) IS NOT NULL
                    """,
                    [str(staging.id), self.payload.input_dataset_id],
                )

        self.ctx["pending_feature_dataset_id"] = str(staging.id)
        report_progress(self.ctx, 90, "Convex hull complete")

        return {}
