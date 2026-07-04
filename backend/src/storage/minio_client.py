from minio import Minio
from config import settings

_minio_client:Minio|None = None

def get_minio_client()->Minio:
    global _minio_client
    if _minio_client is None:
        _minio_client = Minio(
            endpoint=f"localhost:{settings.minio_port}",
            access_key=settings.minio_access_keys,
            secret_key=settings.minio_secret_keys,
            secure=False
        )
    return _minio_client

def init_minio_bucket()->None:
    client = get_minio_client()
    found = client.bucket_exists(settings.minio_bucket_name)
    if not found:
        client.make_bucket(settings.minio_bucket_name)