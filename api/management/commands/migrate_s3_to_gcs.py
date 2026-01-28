"""
One-off migration: copy all diagram images from S3 to GCS and update DB URLs.
Usage:
  python manage.py migrate_s3_to_gcs --dry-run   # report only
  python manage.py migrate_s3_to_gcs             # copy + update DB

Requires AWS_* and GS_BUCKET_NAME + GOOGLE_APPLICATION_CREDENTIALS_JSON when not --dry-run.
"""
import tempfile
import os
from django.core.management.base import BaseCommand
from django.db import transaction
from django.conf import settings

from api.models import LessonAsset, MathAsset
from api.storage_backend import s3_url_to_key, upload_to_gcs


def _is_s3_url(url):
    if not url or not isinstance(url, str):
        return False
    return "s3.amazonaws.com" in url or (".s3." in url and "amazonaws.com" in url)


def _s3_get_to_temp(s3_client, bucket, key, temp_dir):
    """Stream S3 object to a temp file; return (path, content_type)."""
    try:
        head = s3_client.head_object(Bucket=bucket, Key=key)
        ct = head.get("ContentType") or "image/png"
    except Exception:
        ct = "image/png"
    path = os.path.join(temp_dir, os.path.basename(key).replace("/", "_"))
    s3_client.download_file(bucket, key, path)
    return path, ct


class Command(BaseCommand):
    help = "Copy S3 diagram assets to GCS and update LessonAsset/MathAsset URLs"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Only report counts and sample updates; no S3 get, no GCS put, no DB write",
        )

    def handle(self, *args, **options):
        dry_run = options.get("dry_run", False)

        # Discover refs
        refs = []  # (model_name, pk, url)
        for a in LessonAsset.objects.exclude(s3_url=""):
            if a.s3_url and _is_s3_url(a.s3_url):
                refs.append(("LessonAsset", str(a.pk), a.s3_url))
        for a in MathAsset.objects.exclude(s3_url=""):
            if a.s3_url and _is_s3_url(a.s3_url):
                refs.append(("MathAsset", str(a.pk), a.s3_url))

        # Unique S3 keys and map url -> key
        url_to_key = {}
        keys_to_urls = {}  # key -> list of (model, pk, url)
        for model_name, pk, url in refs:
            key = s3_url_to_key(url)
            if not key:
                self.stdout.write(self.style.WARNING(f"Could not parse key from: {url[:80]}..."))
                continue
            url_to_key[url] = key
            keys_to_urls.setdefault(key, []).append((model_name, pk, url))

        unique_keys = list(keys_to_urls.keys())
        self.stdout.write(
            f"Unique S3 objects to migrate: {len(unique_keys)}"
        )
        self.stdout.write(
            f"DB reference cells to update: {len(refs)}"
        )
        if not unique_keys:
            self.stdout.write("Nothing to migrate.")
            return

        if dry_run:
            for i, key in enumerate(unique_keys[:5]):
                self.stdout.write(f"  Sample key: {key}")
            if len(unique_keys) > 5:
                self.stdout.write(f"  ... and {len(unique_keys) - 5} more")
            return

        # Require AWS and GCS
        try:
            import boto3
            from botocore.exceptions import ClientError
        except ImportError:
            self.stdout.write(self.style.ERROR("boto3 required for migration. pip install boto3"))
            return
        ak = getattr(settings, "AWS_ACCESS_KEY_ID", None)
        sk = getattr(settings, "AWS_SECRET_ACCESS_KEY", None)
        bucket_s3 = getattr(settings, "AWS_STORAGE_BUCKET_NAME", None)
        if not all([ak, sk, bucket_s3]):
            self.stdout.write(
                self.style.ERROR(
                    "AWS not configured. Set AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_STORAGE_BUCKET_NAME."
                )
            )
            return
        if not getattr(settings, "GS_BUCKET_NAME", None) or not getattr(
            settings, "GOOGLE_APPLICATION_CREDENTIALS_JSON", None
        ):
            self.stdout.write(
                self.style.ERROR(
                    "GCS not configured. Set GS_BUCKET_NAME and GOOGLE_APPLICATION_CREDENTIALS_JSON."
                )
            )
            return

        s3_client = boto3.client(
            "s3",
            aws_access_key_id=ak,
            aws_secret_access_key=sk,
            region_name=getattr(settings, "AWS_S3_REGION_NAME", "us-east-1"),
        )

        # key -> new GCS url
        key_to_gcs_url = {}
        with tempfile.TemporaryDirectory() as temp_dir:
            for key in unique_keys:
                try:
                    path, content_type = _s3_get_to_temp(s3_client, bucket_s3, key, temp_dir)
                    gcs_url = upload_to_gcs(path, key, content_type=content_type)
                    key_to_gcs_url[key] = gcs_url
                except ClientError as e:
                    code = e.response.get("Error", {}).get("Code", "")
                    if code in ("NoSuchKey", "404"):
                        self.stdout.write(self.style.WARNING(f"  NoSuchKey (skipped): {key}"))
                    else:
                        self.stdout.write(self.style.ERROR(f"  S3 error {key}: {e}"))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"  Error copying {key}: {e}"))

        updated = 0
        for model_name, pk, old_url in refs:
            key = url_to_key.get(old_url)
            if not key or key not in key_to_gcs_url:
                continue
            new_url = key_to_gcs_url[key]
            try:
                with transaction.atomic():
                    if model_name == "LessonAsset":
                        LessonAsset.objects.filter(pk=pk).update(s3_url=new_url)
                    else:
                        MathAsset.objects.filter(pk=pk).update(s3_url=new_url)
                updated += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  DB update failed {model_name} {pk}: {e}"))

        self.stdout.write(self.style.SUCCESS(f"Updated {updated} reference(s)."))
