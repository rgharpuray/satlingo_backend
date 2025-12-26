#!/usr/bin/env python3
"""
Test script to verify S3 upload functionality
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'satlingo.settings')
django.setup()

from django.conf import settings
import boto3
from botocore.exceptions import ClientError
from boto3.exceptions import S3UploadFailedError
import tempfile

def test_s3_upload():
    """Test uploading a file to S3"""
    print("=" * 60)
    print("S3 Upload Test")
    print("=" * 60)
    
    # Check configuration
    aws_access_key_id = getattr(settings, 'AWS_ACCESS_KEY_ID', None)
    aws_secret_access_key = getattr(settings, 'AWS_SECRET_ACCESS_KEY', None)
    aws_storage_bucket_name = getattr(settings, 'AWS_STORAGE_BUCKET_NAME', None)
    aws_s3_region_name = getattr(settings, 'AWS_S3_REGION_NAME', 'us-east-1')
    
    print(f"\n📋 Configuration:")
    print(f"  AWS_ACCESS_KEY_ID: {'SET' if aws_access_key_id else 'NOT SET'}")
    print(f"  AWS_SECRET_ACCESS_KEY: {'SET' if aws_secret_access_key else 'NOT SET'}")
    print(f"  AWS_STORAGE_BUCKET_NAME: {aws_storage_bucket_name}")
    print(f"  AWS_S3_REGION_NAME: {aws_s3_region_name}")
    
    if not all([aws_access_key_id, aws_secret_access_key, aws_storage_bucket_name]):
        print("\n❌ ERROR: S3 configuration incomplete!")
        return False
    
    # Create a test file
    print(f"\n📝 Creating test file...")
    test_content = b"This is a test image file for S3 upload verification."
    with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp_file:
        tmp_file.write(test_content)
        test_file_path = tmp_file.name
    
    print(f"  Test file: {test_file_path}")
    
    # Initialize S3 client
    print(f"\n🔌 Connecting to S3...")
    try:
        s3_client = boto3.client(
            's3',
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=aws_s3_region_name
        )
        print("  ✅ S3 client initialized")
    except Exception as e:
        print(f"  ❌ Failed to initialize S3 client: {str(e)}")
        os.unlink(test_file_path)
        return False
    
    # Test upload
    s3_key = "test/upload-test.png"
    print(f"\n📤 Uploading test file to s3://{aws_storage_bucket_name}/{s3_key}...")
    
    # Try with ACL first
    try:
        s3_client.upload_file(
            test_file_path,
            aws_storage_bucket_name,
            s3_key,
            ExtraArgs={'ACL': 'public-read'}
        )
        print("  ✅ Upload successful (with ACL)")
    except (ClientError, S3UploadFailedError) as acl_error:
        # Extract error code from the exception
        if isinstance(acl_error, ClientError):
            error_code = acl_error.response.get('Error', {}).get('Code', '')
            error_message = acl_error.response.get('Error', {}).get('Message', '')
        else:
            # S3UploadFailedError wraps the original error
            error_code = 'AccessControlListNotSupported' if 'ACL' in str(acl_error) else 'Unknown'
            error_message = str(acl_error)
        
        print(f"  ⚠️  ACL upload failed ({error_code}): {error_message}")
        
        if 'AccessControlListNotSupported' in error_code or 'ACL' in error_message:
            # Try without ACL
            print(f"  🔄 Retrying without ACL...")
            try:
                s3_client.upload_file(
                    test_file_path,
                    aws_storage_bucket_name,
                    s3_key
                )
                print(f"  ✅ Upload successful (without ACL - bucket ACLs disabled)")
            except (ClientError, S3UploadFailedError) as upload_error:
                if isinstance(upload_error, ClientError):
                    error_code = upload_error.response.get('Error', {}).get('Code', '')
                    error_message = upload_error.response.get('Error', {}).get('Message', '')
                else:
                    error_code = 'Unknown'
                    error_message = str(upload_error)
                print(f"\n❌ UPLOAD FAILED!")
                print(f"  Error Code: {error_code}")
                print(f"  Error Message: {error_message}")
                os.unlink(test_file_path)
                return False
        else:
            # Different error, fail
            print(f"\n❌ UPLOAD FAILED!")
            print(f"  Error Code: {error_code}")
            print(f"  Error Message: {error_message}")
            os.unlink(test_file_path)
            return False
    
    try:
        
        # Construct URL
        if aws_s3_region_name == 'us-east-1':
            s3_url = f"https://{aws_storage_bucket_name}.s3.amazonaws.com/{s3_key}"
        else:
            s3_url = f"https://{aws_storage_bucket_name}.s3.{aws_s3_region_name}.amazonaws.com/{s3_key}"
        
        print(f"\n✅ SUCCESS!")
        print(f"  File uploaded to: {s3_url}")
        print(f"\n🧹 Cleaning up test file...")
        os.unlink(test_file_path)
        
        # Try to verify the file exists
        print(f"\n🔍 Verifying file exists in bucket...")
        try:
            s3_client.head_object(Bucket=aws_storage_bucket_name, Key=s3_key)
            print(f"  ✅ File verified in bucket")
        except ClientError as e:
            print(f"  ⚠️  Warning: Could not verify file (this might be normal): {str(e)}")
        
        return True
        
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', '')
        error_message = e.response.get('Error', {}).get('Message', str(e))
        print(f"\n❌ UPLOAD FAILED!")
        print(f"  Error Code: {error_code}")
        print(f"  Error Message: {error_message}")
        os.unlink(test_file_path)
        return False
    except Exception as e:
        print(f"\n❌ UPLOAD FAILED!")
        print(f"  Error: {str(e)}")
        os.unlink(test_file_path)
        return False

if __name__ == '__main__':
    success = test_s3_upload()
    sys.exit(0 if success else 1)

