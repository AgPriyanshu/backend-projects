# Use Alpine-based Python image
FROM python:3.12-alpine

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    CPLUS_INCLUDE_PATH=/usr/include/gdal \
    C_INCLUDE_PATH=/usr/include/gdal \
    # Helps some apps find the SpatiaLite .so when loading the extension
    SPATIALITE_LIBRARY_PATH=/usr/lib/libspatialite.so

WORKDIR /app

# System deps (no spatialite-tools on Alpine 3.22; use libspatialite + sqlite)
RUN apk update && apk add --no-cache \
    bash \
    build-base \
    openjdk17 \
    postgresql-dev \
    gdal \
    gdal-dev \
    geos-dev \
    proj-dev \
    sqlite \
    sqlite-dev \
    libspatialite \
    libspatialite-dev \
    curl \
    libstdc++ \
  && rm -rf /var/cache/apk/*

# Java for language_tool_python
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk

# Python deps
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# GDAL Python binding must match system GDAL
RUN GDAL_VERSION="$(gdal-config --version)" && pip install "GDAL==${GDAL_VERSION}"

# App files
COPY . .
RUN chmod +x ./docker-entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["uvicorn", "backend_projects.asgi:application", "--host", "0.0.0.0", "--port", "8000", "--log-config", "log_config.yaml"]
