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

            # Get shapefile info before creating layer
            shapefile_info = self._get_shapefile_metadata(shapefile_path)

            # Create layer with metadata
            layer = Layer.objects.create(
                name=layer_name, 
                description=description,
                file_name=zip_file.name,
                file_size=zip_file.size,
                geometry_type=shapefile_info['geometry_type'],
                srid=shapefile_info['srid']
            )

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
            for feature_data in shapefile_layer:
                try:
                    with transaction.atomic():
                        self._create_feature_from_shapefile_feature(feature_data, layer)
                        stats["features_created"] += 1
                except Exception as e:
                    error_msg = f"Error processing feature: {str(e)}"
                    stats["errors"].append(error_msg)
                    if len(stats["errors"]) > 20:  # Limit error reporting
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
            try:
                # Convert to GEOSGeometry
                geos_geom = GEOSGeometry(geom.wkt)
                
                # Force geometry to 2D if it has Z dimension
                if geos_geom.hasz:
                    # Create a simple 2D version by removing Z coordinates
                    import re
                    wkt = geom.wkt
                    
                    # Remove Z from geometry type declarations
                    wkt_2d = re.sub(r'\b(\w+)\s+Z\b', r'\1', wkt)
                    
                    # Remove third coordinate (Z) from coordinate triplets
                    # Matches patterns like "x y z" and converts to "x y"
                    wkt_2d = re.sub(r'(-?\d+\.?\d*)\s+(-?\d+\.?\d*)\s+(-?\d+\.?\d*)', r'\1 \2', wkt_2d)
                    
                    # Create new 2D geometry
                    geos_geom = GEOSGeometry(wkt_2d, srid=4326)
                
                # Ensure the geometry has the correct SRID
                if not geos_geom.srid:
                    geos_geom.srid = 4326
                    
            except Exception as e:
                raise ValueError(f"Cannot process geometry: {str(e)}")
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

                # Get field information
                field_info = self._analyze_fields(shapefile_layer)
                
                # Convert field info to frontend format
                attributes = {}
                for field_name, info in field_info.items():
                    attributes[field_name] = {
                        "data_type": info["type"],
                        "sample_values": info["sample_values"]
                    }

                # Extract SRID
                srid = 4326  # Default to WGS84
                if shapefile_layer.srs:
                    try:
                        srs = shapefile_layer.srs
                        if hasattr(srs, 'auth_code'):
                            auth_name, auth_code = srs.auth_code
                            if auth_name == 'EPSG':
                                srid = int(auth_code)
                    except:
                        pass  # Keep default

                # Get first few features as examples
                first_features = []
                feature_count = 0
                for feature_data in shapefile_layer:
                    if feature_count >= 3:  # Limit to first 3 features
                        break
                    
                    # Extract feature properties
                    properties = {}
                    for field_name in shapefile_layer.fields:
                        value = feature_data.get(field_name)
                        if value is not None:
                            properties[field_name] = value
                    
                    first_features.append({
                        "properties": properties,
                        "geometry_type": str(feature_data.geom.geom_type) if feature_data.geom else "Unknown"
                    })
                    feature_count += 1

                info = {
                    "layer_name": shapefile_layer.name,
                    "feature_count": len(shapefile_layer),
                    "geometry_type": str(shapefile_layer.geom_type).replace('OGRGeomType.', ''),
                    "srid": srid,
                    "attributes": attributes,
                    "first_features": first_features,
                }

                return info

            except Exception as e:
                raise ValueError(f"Error analyzing shapefile: {str(e)}")

    def _get_shapefile_metadata(self, shapefile_path: str) -> Dict[str, Any]:
        """Extract metadata from shapefile for Layer model"""
        try:
            # Open shapefile with GDAL
            ds = DataSource(shapefile_path)
            if len(ds) == 0:
                raise ValueError("Shapefile contains no layers")

            shapefile_layer = ds[0]
            
            # Extract SRID from spatial reference system
            srid = 4326  # Default to WGS84
            if shapefile_layer.srs:
                try:
                    # Try to get EPSG code from SRS
                    srs = shapefile_layer.srs
                    if hasattr(srs, 'auth_code'):
                        auth_name, auth_code = srs.auth_code
                        if auth_name == 'EPSG':
                            srid = int(auth_code)
                except:
                    pass  # Keep default

            return {
                'geometry_type': str(shapefile_layer.geom_type).replace('OGRGeomType.', ''),
                'srid': srid,
                'feature_count': len(shapefile_layer),
                'layer_name': shapefile_layer.name,
            }
        except Exception as e:
            # Return defaults if metadata extraction fails
            return {
                'geometry_type': 'Unknown',
                'srid': 4326,
                'feature_count': 0,
                'layer_name': 'Unknown',
            }


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
