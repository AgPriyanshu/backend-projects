# Use the official Python image as the base
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install system dependencies including GIS libraries
RUN apt-get update && apt-get install -y \
    build-essential \
    default-jre \
    libpq-dev \
    gdal-bin \
    libgdal-dev \
    libgeos-dev \
    libproj-dev \
    libspatialite-dev \
    spatialite-bin \
    && rm -rf /var/lib/apt/lists/*

# Set GDAL environment variables
ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal

# Install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

# Install GDAL Python package matching the system GDAL version
RUN GDAL_VERSION=$(gdal-config --version) && \
    pip install GDAL==$GDAL_VERSION

# Copy project files
COPY . .

# Ensure the entrypoint script is executable
RUN chmod +x ./docker-entrypoint.sh

# Expose port 8000
EXPOSE 8000

ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["uvicorn", "backend_projects.asgi:application", "--host", "0.0.0.0", "--port", "8000", "--log-config", "log_config.yaml"]
