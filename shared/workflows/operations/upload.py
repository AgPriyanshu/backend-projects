from pathlib import Path

from shared.infrastructure import InfraManager
from shared.utils import URIType, parse_uri

from ..base.base_operation import Operation
from ..schemas import StrictPayload


class UploadPayload(StrictPayload):
    upload_url: str
    upload_from_path: str | None = None
    metadata: dict[str, str] | None = None


class Upload(Operation[UploadPayload, object]):
    name = "upload"

    def execute(self, *args, **kwargs):
        upload_url = self.payload.upload_url
        upload_from_path = self.payload.upload_from_path
        metadata = getattr(self.payload, "metadata", None)
        parse_results = parse_uri(upload_url)

        if not upload_from_path:
            raise ValueError("upload_from_path is required.")

        uri_type = parse_results.get("type")
        components = parse_results.get("components")

        src = Path(upload_from_path).expanduser()
        if not src.exists():
            raise FileNotFoundError(f"Local file not found: {src}")

        if uri_type == URIType.S3:
            if not components:
                raise ValueError(f"Invalid S3 URL: {upload_url}")
            bucket = components.get("bucket")
            key = components.get("key")
            if not bucket or not key:
                raise ValueError(f"Invalid S3 URL: {upload_url}")
            with open(src, "rb") as fh:
                return InfraManager.object_storage.upload_object(
                    file=fh,
                    key=key,
                    bucket=bucket,
                    metadata=metadata,
                )

        if uri_type == URIType.LOCAL:
            dst = Path(upload_url).expanduser()
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(src.read_bytes())
            return str(dst)

        if uri_type == URIType.AZURE:
            raise ValueError(
                "Azure URI scheme is not supported for uploads. "
                "Use an S3-compatible URI or a local path."
            )

        if uri_type in (URIType.HTTP, URIType.HTTPS):
            raise ValueError(
                "HTTP/HTTPS uploads are not supported. "
                "Use an S3-compatible URI or a local path."
            )

        raise ValueError(f"Unsupported or unknown upload URL type: {upload_url}")
