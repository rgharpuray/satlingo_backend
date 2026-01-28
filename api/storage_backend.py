"""
Storage abstraction for diagram/image assets. Supports AWS S3 and Google Cloud Storage (GCS).
Use USE_GCS to switch; new uploads go to GCS when True. Stored URLs are always returned as-is;
clients and API use the URL from the DB (S3 or GCS). Delete uses the backend that owns the URL.
"""
import os
import re
from urllib.parse import quote, unquote

from django.conf import settings

# ---------------------------------------------------------------------------
# GCS
# ---------------------------------------------------------------------------
def _gcs_credentials():
    """Return GCS credentials from GOOGLE_APPLICATION_CREDENTIALS_JSON or file."""
    import json
    creds_json = getattr(settings, 'GOOGLE_APPLICATION_CREDENTIALS_JSON', None)
    if creds_json and isinstance(creds_json, str) and creds_json.strip():
        return json.loads(creds_json)
    path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    if path and os.path.isfile(path):
        with open(path, 'r') as f:
            return json.load(f)
    return None


def _gcs_client():
    """Lazy GCS client using credentials from env/settings."""
    from google.oauth2 import service_account
    from google.cloud import storage as gcs_storage
    info = _gcs_credentials()
    if not info:
        return None
    creds = service_account.Credentials.from_service_account_info(info)
    return gcs_storage.Client(
        credentials=creds,
        project=info.get('project_id') or getattr(settings, 'GS_PROJECT_ID', None),
    )


def upload_to_gcs(local_path, key, content_type=None):
    """Upload file at local_path to GCS at key. Returns public URL."""
    client = _gcs_client()
    bucket_name = getattr(settings, 'GS_BUCKET_NAME', None)
    if not client or not bucket_name:
        raise RuntimeError("GCS not configured: set GS_BUCKET_NAME and GOOGLE_APPLICATION_CREDENTIALS_JSON")
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(key)
    if content_type:
        blob.upload_from_filename(local_path, content_type=content_type)
    else:
        blob.upload_from_filename(local_path)
    return f"https://storage.googleapis.com/{bucket_name}/{quote(key, safe='/')}"


def delete_from_gcs(key_or_url):
    """Delete object from GCS by key or by URL. No-op if key not found."""
    client = _gcs_client()
    bucket_name = getattr(settings, 'GS_BUCKET_NAME', None)
    if not client or not bucket_name:
        return
    key = key_or_url
    if key_or_url.startswith("https://storage.googleapis.com/"):
        prefix = f"https://storage.googleapis.com/{bucket_name}/"
        if key_or_url.startswith(prefix):
            key = unquote(key_or_url[len(prefix):].split("?")[0])
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(key)
    try:
        blob.delete()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# S3
# ---------------------------------------------------------------------------
def _s3_client():
    """Lazy S3 client."""
    try:
        import boto3
    except ImportError:
        return None
    ak = getattr(settings, 'AWS_ACCESS_KEY_ID', None)
    sk = getattr(settings, 'AWS_SECRET_ACCESS_KEY', None)
    if not ak or not sk:
        return None
    return boto3.client(
        's3',
        aws_access_key_id=ak,
        aws_secret_access_key=sk,
        region_name=getattr(settings, 'AWS_S3_REGION_NAME', 'us-east-1'),
    )


def upload_to_s3(local_path, key, content_type=None):
    """Upload file to S3 at key. Returns public URL."""
    client = _s3_client()
    bucket = getattr(settings, 'AWS_STORAGE_BUCKET_NAME', None)
    if not client or not bucket:
        raise RuntimeError("S3 not configured: set AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_STORAGE_BUCKET_NAME")
    region = getattr(settings, 'AWS_S3_REGION_NAME', 'us-east-1')
    extra = {}
    if content_type:
        extra['ContentType'] = content_type
    try:
        extra['ACL'] = 'public-read'
        client.upload_file(local_path, bucket, key, ExtraArgs=extra)
    except Exception:
        extra.pop('ACL', None)
        client.upload_file(local_path, bucket, key, ExtraArgs=extra or None)
    encoded = quote(key, safe='/')
    if region == 'us-east-1':
        return f"https://{bucket}.s3.amazonaws.com/{encoded}"
    return f"https://{bucket}.s3.{region}.amazonaws.com/{encoded}"


def delete_from_s3(key_or_url):
    """Delete object from S3 by key or URL. No-op if key not found."""
    client = _s3_client()
    bucket = getattr(settings, 'AWS_STORAGE_BUCKET_NAME', None)
    if not client or not bucket:
        return
    key = key_or_url
    if isinstance(key_or_url, str) and ("s3.amazonaws.com" in key_or_url or ".s3." in key_or_url):
        key = s3_url_to_key(key_or_url)
    if not key:
        return
    try:
        client.delete_object(Bucket=bucket, Key=key)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Abstraction
# ---------------------------------------------------------------------------
def use_gcs():
    """True if new uploads should go to GCS."""
    return getattr(settings, 'USE_GCS', False)


def upload_media(local_path, key, content_type=None):
    """
    Upload a file to the configured backend (GCS if USE_GCS else S3).
    key: object key/path (e.g. 'lessons/abc-123/diagram-1.png').
    Returns the URL to store in the DB.
    """
    if use_gcs():
        return upload_to_gcs(local_path, key, content_type=content_type)
    return upload_to_s3(local_path, key, content_type=content_type)


def delete_media(url_or_key):
    """
    Delete from the backend that owns the object.
    If url_or_key looks like a GCS URL, delete from GCS; else treat as S3 key or S3 URL and delete from S3.
    """
    if not url_or_key:
        return
    s = (url_or_key or "").strip()
    if s.startswith("https://storage.googleapis.com/"):
        delete_from_gcs(s)
        return
    if "s3.amazonaws.com" in s or ".s3." in s and "amazonaws.com" in s:
        delete_from_s3(s)
        return
    # Assume it's a key
    if use_gcs():
        delete_from_gcs(s)
    else:
        delete_from_s3(s)


# ---------------------------------------------------------------------------
# Migration helpers: S3 URL <-> key
# ---------------------------------------------------------------------------
def s3_url_to_key(url, bucket_name=None):
    """
    Extract S3 object key from common S3 URL forms. Returns None if not recognized.
    """
    if not url or not isinstance(url, str):
        return None
    url = url.split("?")[0].strip()
    # https://bucket.s3.amazonaws.com/key
    m = re.match(r"https://([^.]+)\.s3\.amazonaws\.com/(.+)", url)
    if m:
        return unquote(m.group(2))
    # https://s3.amazonaws.com/bucket/key
    m = re.match(r"https://s3\.amazonaws\.com/([^/]+)/(.+)", url)
    if m:
        return unquote(m.group(2))
    # https://bucket.s3.region.amazonaws.com/key
    m = re.match(r"https://[^.]+\.s3\.[^/]+\.amazonaws\.com/(.+)", url)
    if m:
        return unquote(m.group(1))
    return None


