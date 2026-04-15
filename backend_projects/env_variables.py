import os
from enum import Enum


class EnvVariable(Enum):
    ENV = os.environ.get("ENV", "production")
    DEBUG = os.environ["DEBUG"]
    DB_NAME = os.environ["DB_NAME"]
    DB_USER = os.environ["DB_USER"]
    DB_PASSWORD = os.environ["DB_PASSWORD"]
    DB_HOST = os.environ["DB_HOST"]
    DB_PORT = os.environ["DB_PORT"]

    INFRA_PROVIDER = os.environ.get("INFRA_PROVIDER", "k8s")

    REDIS_HOST = os.environ.get("REDIS_HOST", "redis")
    REDIS_PORT = os.environ.get("REDIS_PORT", "6379")

    S3_ENDPOINT_URL = os.environ.get("S3_ENDPOINT_URL", "http://localhost:8333")
    S3_ACCESS_KEY = os.environ.get("S3_ACCESS_KEY", "minioadmin")
    S3_SECRET_KEY = os.environ.get("S3_SECRET_KEY", "minioadmin")
    S3_REGION_NAME = os.environ.get("S3_REGION_NAME", "ap-south-1")
    S3_BUCKET_NAME = os.environ.get("S3_BUCKET_NAME", "woa")
