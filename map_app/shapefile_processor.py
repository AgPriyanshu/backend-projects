import os
import tempfile
import zipfile
from typing import Dict, Any, List, Tuple
from django.contrib.gis.gdal import DataSource
from django.contrib.gis.geos import GEOSGeometry
from django.db import transaction
from .models import Layer, Feature
from .utils import AttributeManager


class ShapefileProcessor:
    """Process shapefile uploads and convert to database format"""

    def __init__(self):
        self.required_extensions = {".shp", ".shx", ".dbf"}
        self.optional_extensions = {".prj", ".cpg", ".qix", ".sbn", ".sbx"}

    def process_shapefile_zip(
        self, zip_file, layer_name: str, description: str = ""
    ) -> Tuple[Layer, Dict[str, Any]]:
        """
        Process a zip file containing shapefile components
        Returns: (Layer object, processing stats)
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            # Extract zip file
            extracted_files = self._extract_zip(zip_file, temp_dir)

            # Validate shapefile components
            shapefile_path = self._validate_shapefile_components(
                extracted_files, temp_dir
            )

            # Create layer
            layer = Layer.objects.create(name=layer_name, description=description)

            # Process shapefile and create features
            stats = self._process_shapefile(shapefile_path, layer)

            return layer, stats

    def _extract_zip(self, zip_file, temp_dir: str) -> List[str]:
        """Extract zip file and return list of extracted filenames"""
        extracted_files = []

        with zipfile.ZipFile(zip_file, "r") as zip_ref:
            # Check for malicious paths
            for member in zip_ref.namelist():
                if os.path.isabs(member) or ".." in member:
                    raise ValueError(f"Unsafe path in zip file: {member}")

            zip_ref.extractall(temp_dir)
            extracted_files = zip_ref.namelist()

        return extracted_files

    def _validate_shapefile_components(
        self, extracted_files: List[str], temp_dir: str
    ) -> str:
        """Validate that required shapefile components are present"""
        # Get file extensions
        file_extensions = {os.path.splitext(f)[1].lower() for f in extracted_files}

        # Check for required components
        missing_required = self.required_extensions - file_extensions
        if missing_required:
            raise ValueError(
                f"Missing required shapefile components: {missing_required}"
            )

        # Find the .shp file (main shapefile)
        shp_files = [f for f in extracted_files if f.endswith(".shp")]
        if len(shp_files) != 1:
            raise ValueError("Zip file must contain exactly one .shp file")

        shapefile_path = os.path.join(temp_dir, shp_files[0])

        if not os.path.exists(shapefile_path):
            raise ValueError("Shapefile not found after extraction")

        return shapefile_path

    def _process_shapefile(self, shapefile_path: str, layer: Layer) -> Dict[str, Any]:
        """Process the shapefile and create features with attributes"""
        stats = {
            "features_created": 0,
            "attributes_created": 0,
            "errors": [],
            "field_info": {},
        }

        try:
            # Open shapefile with GDAL
            ds = DataSource(shapefile_path)

            if len(ds) == 0:
                raise ValueError("Shapefile contains no layers")

            # Get the first (and typically only) layer in the shapefile
            shapefile_layer = ds[0]

            # Get field information
            field_info = self._analyze_fields(shapefile_layer)
            stats["field_info"] = field_info

            # Process features
            with transaction.atomic():
                for feature_data in shapefile_layer:
                    try:
                        self._create_feature_from_shapefile_feature(feature_data, layer)
                        stats["features_created"] += 1
                    except Exception as e:
                        error_msg = f"Error processing feature: {str(e)}"
                        stats["errors"].append(error_msg)
                        if len(stats["errors"]) > 10:  # Limit error reporting
                            stats["errors"].append("... (more errors truncated)")
                            break

        except Exception as e:
            raise ValueError(f"Error processing shapefile: {str(e)}")

        return stats

    def _analyze_fields(self, shapefile_layer) -> Dict[str, Dict[str, Any]]:
        """Analyze field types and characteristics"""
        field_info = {}

        for field in shapefile_layer.fields:
            field_info[field] = {
                "type": str(
                    shapefile_layer.field_types[shapefile_layer.fields.index(field)]
                ),
                "sample_values": [],
            }

        # Sample first few features to get example values
        sample_count = 0
        for feature in shapefile_layer:
            if sample_count >= 5:  # Sample first 5 features
                break

            for field_name in field_info.keys():
                value = feature.get(field_name)
                if (
                    value is not None
                    and value not in field_info[field_name]["sample_values"]
                ):
                    field_info[field_name]["sample_values"].append(value)

            sample_count += 1

        return field_info

    def _create_feature_from_shapefile_feature(self, shapefile_feature, layer: Layer):
        """Create a Feature and its attributes from a shapefile feature"""
        # Get geometry
        geom = shapefile_feature.geom
        if geom:
            # Convert to GEOSGeometry
            geos_geom = GEOSGeometry(geom.wkt)
        else:
            raise ValueError("Feature has no geometry")

        # Create Feature
        feature = Feature.objects.create(layer=layer, geometry=geos_geom)

        # Extract attributes
        attributes = {}
        for field_name in shapefile_feature.fields:
            value = shapefile_feature.get(field_name)
            if value is not None:
                # Convert to string for our attribute system
                attributes[field_name.lower()] = str(value)

        # Create attributes using our AttributeManager
        if attributes:
            AttributeManager.create_feature_attributes(feature, attributes)

    def get_shapefile_info(self, zip_file) -> Dict[str, Any]:
        """Get information about a shapefile without importing it"""
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                # Extract and validate
                extracted_files = self._extract_zip(zip_file, temp_dir)
                shapefile_path = self._validate_shapefile_components(
                    extracted_files, temp_dir
                )

                # Open and analyze
                ds = DataSource(shapefile_path)
                if len(ds) == 0:
                    raise ValueError("Shapefile contains no layers")

                shapefile_layer = ds[0]

                info = {
                    "layer_name": shapefile_layer.name,
                    "feature_count": len(shapefile_layer),
                    "geometry_type": str(shapefile_layer.geom_type),
                    "srs": str(shapefile_layer.srs) if shapefile_layer.srs else None,
                    "extent": (
                        list(shapefile_layer.extent)
                        if hasattr(shapefile_layer, "extent")
                        else None
                    ),
                    "fields": self._analyze_fields(shapefile_layer),
                }

                return info

            except Exception as e:
                raise ValueError(f"Error analyzing shapefile: {str(e)}")


def process_shapefile_upload(
    zip_file, layer_name: str, description: str = ""
) -> Tuple[Layer, Dict[str, Any]]:
    """Convenience function to process a shapefile upload"""
    processor = ShapefileProcessor()
    return processor.process_shapefile_zip(zip_file, layer_name, description)


def get_shapefile_preview(zip_file) -> Dict[str, Any]:
    """Convenience function to get shapefile information without importing"""
    processor = ShapefileProcessor()
    return processor.get_shapefile_info(zip_file)
