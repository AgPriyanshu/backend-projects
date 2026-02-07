import io
from pathlib import Path

import requests

from shared.infrastructure import InfraManager
from shared.utils import URIType, parse_uri

from ..base.base_operation import Operation
from ..schemas import StrictPayload


class DownloadPayload(StrictPayload):
    download_url: str
    download_to_path: str | None = None


class Download(Operation[DownloadPayload, object]):
    name = "download"

    def execute(self, *args, **kwargs):
        download_url = self.payload.download_url
        download_to_path = self.payload.download_to_path
        parse_results = parse_uri(download_url)

        def _write_fileobj_to_path(fileobj, path):
            if path:
                p = Path(path)
                p.parent.mkdir(parents=True, exist_ok=True)
                # Fileobj may be BytesIO or similar.
                with open(p, "wb") as fh:
                    for chunk in iter(lambda: fileobj.read(8192), b""):
                        fh.write(chunk)
                return str(p)
            # If no path provided, return the file-like object.
            return fileobj

        uri_type = parse_results.get("type")
        components = parse_results.get("components")

        # S3-style (and S3-compatible) object storage.
        if uri_type == URIType.S3:
            if not components:
                raise ValueError(f"Invalid S3 URL: {download_url}")
            bucket = components.get("bucket")
            key = components.get("key")
            if not isinstance(bucket, str) or not isinstance(key, str):
                raise ValueError(f"Invalid S3 URL: {download_url}")
            fileobj = InfraManager.object_storage.download_object(
                key=key, bucket=bucket
            )
            return _write_fileobj_to_path(fileobj, download_to_path)

        # Local path - copy or return path.
        if uri_type == URIType.LOCAL:
            src = Path(download_url).expanduser()
            if not src.exists():
                raise FileNotFoundError(f"Local file not found: {src}")
            if download_to_path:
                dst = Path(download_to_path)
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_bytes(src.read_bytes())
                return str(dst)
            return str(src)

        # HTTP/HTTPS.
        if uri_type in (URIType.HTTP, URIType.HTTPS) or (
            uri_type == URIType.AZURE and download_url.startswith("https://")
        ):
            response = requests.get(download_url, stream=True, timeout=30)
            response.raise_for_status()
            if download_to_path:
                dst = Path(download_to_path)
                dst.parent.mkdir(parents=True, exist_ok=True)
                with open(dst, "wb") as fh:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            fh.write(chunk)
                return str(dst)
            data = io.BytesIO()
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    data.write(chunk)
            data.seek(0)
            return data

        if uri_type == URIType.AZURE:
            raise ValueError(
                "Azure URI scheme is not supported for downloads. "
                "Use a full https://<account>.blob.core.windows.net/... URL."
            )

        # Unknown type - raise.
        raise ValueError(f"Unsupported or unknown download URL type: {download_url}")
