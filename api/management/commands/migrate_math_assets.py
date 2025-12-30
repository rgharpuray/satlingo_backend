"""
Management command to migrate math section assets from old S3 paths to new paths
"""
from django.core.management.base import BaseCommand
from api.models import MathAsset
from django.conf import settings
from urllib.parse import quote, unquote
import boto3
from botocore.exceptions import ClientError


class Command(BaseCommand):
    help = 'Migrate math section assets from math-sections/ to lessons/ path in S3'

    def handle(self, *args, **options):
        # Get S3 configuration
        aws_access_key_id = getattr(settings, 'AWS_ACCESS_KEY_ID', None)
        aws_secret_access_key = getattr(settings, 'AWS_SECRET_ACCESS_KEY', None)
        aws_storage_bucket_name = getattr(settings, 'AWS_STORAGE_BUCKET_NAME', None)
        aws_s3_region_name = getattr(settings, 'AWS_S3_REGION_NAME', 'us-east-1')

        if not all([aws_access_key_id, aws_secret_access_key, aws_storage_bucket_name]):
            self.stdout.write(self.style.ERROR('S3 not configured. Set AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, and AWS_STORAGE_BUCKET_NAME in settings.'))
            return

        # Initialize S3 client
        s3_client = boto3.client(
            's3',
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=aws_s3_region_name
        )

        # Find all math assets
        assets = MathAsset.objects.all()
        self.stdout.write(f'Found {assets.count()} math assets to check')

        migrated = 0
        skipped = 0
        errors = 0

        for asset in assets:
            if not asset.s3_url:
                skipped += 1
                continue

            old_url = asset.s3_url
            old_key = None
            new_key = None

            # Extract S3 key from URL
            if 'math-sections/' in old_url:
                # Old format: https://keuvi.s3.amazonaws.com/math-sections/{section_id}/{asset_id}.png
                # Extract the key part
                if '.s3.amazonaws.com/' in old_url:
                    old_key = old_url.split('.s3.amazonaws.com/')[1]
                elif '.s3.' in old_url and '.amazonaws.com/' in old_url:
                    old_key = old_url.split('.amazonaws.com/')[1]
                
                if old_key and old_key.startswith('math-sections/'):
                    # Build new key: lessons/{section_id}/{asset_id}.ext
                    parts = old_key.split('/')
                    if len(parts) >= 3:
                        section_id = parts[1]  # math-practice-questions-#6
                        filename = '/'.join(parts[2:])  # diagram-3.png
                        new_key = f"lessons/{section_id}/{filename}"
                        
                        # URL encode the new key for the URL
                        encoded_key = quote(new_key, safe='/')
                        
                        # Construct new URL
                        if aws_s3_region_name == 'us-east-1':
                            new_url = f"https://{aws_storage_bucket_name}.s3.amazonaws.com/{encoded_key}"
                        else:
                            new_url = f"https://{aws_storage_bucket_name}.s3.{aws_s3_region_name}.amazonaws.com/{encoded_key}"
                        
                        try:
                            # Check if file exists at old location
                            try:
                                s3_client.head_object(Bucket=aws_storage_bucket_name, Key=old_key)
                                file_exists = True
                            except ClientError as e:
                                if e.response['Error']['Code'] == '404':
                                    file_exists = False
                                    self.stdout.write(self.style.WARNING(f'  File not found at old location: {old_key}'))
                                else:
                                    raise
                            
                            if file_exists:
                                # Copy file from old location to new location
                                copy_source = {'Bucket': aws_storage_bucket_name, 'Key': old_key}
                                s3_client.copy_object(
                                    CopySource=copy_source,
                                    Bucket=aws_storage_bucket_name,
                                    Key=new_key
                                )
                                self.stdout.write(f'  ✓ Copied: {old_key} -> {new_key}')
                                
                                # Update database
                                asset.s3_url = new_url
                                asset.save()
                                migrated += 1
                                self.stdout.write(self.style.SUCCESS(f'  ✓ Updated URL: {new_url}'))
                            else:
                                # File doesn't exist, just update URL (file might need to be re-uploaded)
                                asset.s3_url = new_url
                                asset.save()
                                migrated += 1
                                self.stdout.write(self.style.WARNING(f'  ⚠ Updated URL but file not found: {new_url}'))
                                
                        except Exception as e:
                            errors += 1
                            self.stdout.write(self.style.ERROR(f'  ✗ Error migrating {asset.asset_id}: {str(e)}'))
                    else:
                        skipped += 1
                        self.stdout.write(self.style.WARNING(f'  ⚠ Skipped {asset.asset_id}: Invalid URL format'))
                else:
                    skipped += 1
            elif 'lessons/' in old_url and 'math-sections/' not in old_url:
                # Already in new format
                skipped += 1
            else:
                skipped += 1

        self.stdout.write(self.style.SUCCESS(f'\n✓ Migration complete:'))
        self.stdout.write(f'  Migrated: {migrated}')
        self.stdout.write(f'  Skipped: {skipped}')
        self.stdout.write(f'  Errors: {errors}')

