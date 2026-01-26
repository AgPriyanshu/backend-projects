import os
from enum import Enum


class EnvVariable(Enum):
    ENV = os.environ["ENV"]
    DEBUG = os.environ["DEBUG"]
    DB_NAME = os.environ["DB_NAME"]
    DB_USER = os.environ["DB_USER"]
    DB_PASSWORD = os.environ["DB_PASSWORD"]
    DB_HOST = os.environ["DB_HOST"]
    DB_PORT = os.environ["DB_PORT"]

    INFRA_PROVIDER = os.environ.get("INFRA_PROVIDER", "k8s")

    # MinIO Object Storage Configuration
    MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT", "minio:9000")
    MINIO_ACCESS_KEY = os.environ.get("MINIO_ACCESS_KEY", "minioadmin")
    MINIO_SECRET_KEY = os.environ.get("MINIO_SECRET_KEY", "minioadmin123")
