import boto3
from botocore.config import Config
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


def get_r2_endpoint() -> str:
    """
    Resolve the R2 S3-compatible endpoint.
    If R2_ENDPOINT_URL contains placeholder '<account_id>', derive it from R2_ACCOUNT_ID.
    """
    url = settings.R2_ENDPOINT_URL.strip() if settings.R2_ENDPOINT_URL else ""
    if url and "<account_id>" not in url:
        return url
    if settings.R2_ACCOUNT_ID and settings.R2_ACCOUNT_ID != "your-cloudflare-account-id":
        return f"https://{settings.R2_ACCOUNT_ID.strip()}.r2.cloudflarestorage.com"
    return url


def get_r2_client():
    """Create and return a boto3 S3 client configured for Cloudflare R2."""
    endpoint_url = get_r2_endpoint()
    if not endpoint_url or "<account_id>" in endpoint_url:
        raise ValueError(
            "R2 endpoint is not properly configured. Please set R2_ENDPOINT_URL or R2_ACCOUNT_ID in backend/.env"
        )
    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=settings.R2_ACCESS_KEY_ID,
        aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
        region_name="auto",
        config=Config(
            signature_version="s3v4",
            retries={"max_attempts": 3, "mode": "standard"}
        ),
    )


class StorageService:
    @property
    def bucket_name(self) -> str:
        return settings.R2_BUCKET_NAME

    def get_client(self):
        """Returns the configured S3 / R2 client."""
        return get_r2_client()

    def get_r2_client(self):
        """Alias for get_client() to support get_r2_client naming."""
        return self.get_client()

    def upload_file(self, file_obj, destination_key: str, content_type: str = "application/octet-stream") -> dict:
        """
        Uploads a file-like object to Cloudflare R2.
        Returns the object key, bucket name, and file URL.
        """
        client = self.get_client()
        client.upload_fileobj(
            Fileobj=file_obj,
            Bucket=self.bucket_name,
            Key=destination_key,
            ExtraArgs={"ContentType": content_type}
        )

        endpoint = get_r2_endpoint().rstrip("/")
        file_url = f"{endpoint}/{self.bucket_name}/{destination_key}"

        return {
            "key": destination_key,
            "url": file_url,
            "bucket": self.bucket_name,
        }

    def download_file(self, key: str, destination_path: str) -> None:
        """Downloads an object from R2 to a local destination path."""
        client = self.get_client()
        client.download_file(Bucket=self.bucket_name, Key=key, Filename=destination_path)

    def generate_presigned_url(self, file_key: str, expiration_seconds: int = 3600) -> str:
        """Generates a presigned URL to download/stream the file."""
        client = self.get_client()
        return client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket_name, "Key": file_key},
            ExpiresIn=expiration_seconds,
        )


storage_service = StorageService()
