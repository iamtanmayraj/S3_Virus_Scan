import os
import subprocess
import tempfile
import shutil
import logging
import re
import boto3
from typing import Dict, List, Optional, Tuple
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Constants
MAX_FILE_SIZE_MB = 100  # Maximum file size to scan in MB
CLAMSCAN_TIMEOUT = 300  # Timeout for clamscan in seconds


def sanitize_s3_key(key: str) -> str:
    """
    Sanitize S3 key to prevent path traversal and injection attacks.
    
    Args:
        key: S3 object key
        
    Returns:
        Sanitized key safe for file system operations
    """
    # Remove path traversal sequences
    key = re.sub(r'\.\./', '', key)
    key = re.sub(r'\.\.\\', '', key)
    # Remove leading slashes
    key = key.lstrip('/')
    # Replace dangerous characters that could cause issues in file paths
    key = re.sub(r'[<>:"|?*]', '_', key)
    # Limit key length to prevent path length issues
    if len(key) > 255:
        # Keep extension if present
        ext = os.path.splitext(key)[1]
        key = key[:255-len(ext)] + ext
    return key


def scan_file(file_path: str) -> Tuple[bool, Optional[str]]:
    """
    Scan a file for viruses using ClamAV.
    
    Args:
        file_path: Path to the file to scan
        
    Returns:
        Tuple of (is_infected: bool, error_message: Optional[str])
    """
    try:
        # Run the clamscan command with timeout
        result = subprocess.run(
            ['clamscan', '--no-summary', '--infected', file_path],
            capture_output=True,
            text=True,
            timeout=CLAMSCAN_TIMEOUT
        )
        
        # ClamAV returns exit code 1 if virus is found, 0 if clean
        # Also check stderr for virus detection messages
        if result.returncode == 1:
            logger.warning(f"Virus detected in {file_path}: {result.stderr}")
            return True, None
        elif result.returncode == 0:
            return False, None
        else:
            error_msg = f"ClamAV scan failed with return code {result.returncode}: {result.stderr}"
            logger.error(error_msg)
            return False, error_msg
            
    except subprocess.TimeoutExpired:
        error_msg = f"ClamAV scan timed out for {file_path}"
        logger.error(error_msg)
        return False, error_msg
    except FileNotFoundError:
        error_msg = "ClamAV (clamscan) not found. Please ensure ClamAV is installed."
        logger.error(error_msg)
        return False, error_msg
    except Exception as e:
        error_msg = f"Error scanning file {file_path}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return False, error_msg


def get_file_size_mb(s3_client: boto3.client, bucket: str, key: str) -> float:
    """
    Get the size of an S3 object in MB.
    
    Args:
        s3_client: Boto3 S3 client
        bucket: S3 bucket name
        key: S3 object key
        
    Returns:
        File size in MB
    """
    try:
        response = s3_client.head_object(Bucket=bucket, Key=key)
        size_bytes = response.get('ContentLength', 0)
        return size_bytes / (1024 * 1024)  # Convert to MB
    except ClientError as e:
        logger.error(f"Error getting file size for {key}: {str(e)}")
        return 0.0


def scan_s3_object(s3_client: boto3.client, bucket: str, key: str) -> Dict:
    """
    Download and scan a single S3 object for viruses.
    
    Args:
        s3_client: Boto3 S3 client
        bucket: S3 bucket name
        key: S3 object key
        
    Returns:
        Dictionary with scan results
    """
    temp_dir = None
    temp_file_path = None
    
    try:
        # Check file size before downloading
        file_size_mb = get_file_size_mb(s3_client, bucket, key)
        if file_size_mb > MAX_FILE_SIZE_MB:
            logger.warning(f"Skipping {key}: file size ({file_size_mb:.2f} MB) exceeds maximum ({MAX_FILE_SIZE_MB} MB)")
            return {
                'key': key,
                'status': 'skipped',
                'reason': f'File size exceeds {MAX_FILE_SIZE_MB} MB limit',
                'size_mb': file_size_mb
            }
        
        # Create temporary directory
        temp_dir = tempfile.mkdtemp()
        
        # Sanitize S3 key to prevent path traversal attacks
        safe_key = sanitize_s3_key(key)
        
        # Preserve file extension for better ClamAV detection
        file_extension = os.path.splitext(safe_key)[1] or '.tmp'
        temp_file_path = os.path.join(temp_dir, f'downloaded_file{file_extension}')
        
        # Additional security: Ensure file path is within temp directory
        # This prevents any potential path traversal even after sanitization
        temp_file_path = os.path.normpath(temp_file_path)
        if not os.path.abspath(temp_file_path).startswith(os.path.abspath(temp_dir)):
            raise ValueError(f"Invalid file path detected: {temp_file_path}")
        
        # Download file from S3
        logger.info(f"Downloading {key} from bucket {bucket}")
        s3_client.download_file(bucket, key, temp_file_path)
        
        # Additional security check: Validate file path before scanning
        if not os.path.exists(temp_file_path):
            raise FileNotFoundError(f"Downloaded file not found: {temp_file_path}")
        
        # Ensure file path is within temp directory (defense in depth)
        if not os.path.abspath(temp_file_path).startswith(os.path.abspath(temp_dir)):
            raise ValueError(f"Security violation: File path outside temp directory: {temp_file_path}")
        
        # Scan the file
        logger.info(f"Scanning {key} for viruses")
        is_infected, error = scan_file(temp_file_path)
        
        if error:
            return {
                'key': key,
                'status': 'error',
                'error': error,
                'size_mb': file_size_mb
            }
        elif is_infected:
            logger.warning(f"VIRUS DETECTED: {key} in bucket {bucket}")
            return {
                'key': key,
                'status': 'infected',
                'size_mb': file_size_mb
            }
        else:
            logger.info(f"File {key} is clean")
            return {
                'key': key,
                'status': 'clean',
                'size_mb': file_size_mb
            }
            
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_msg = f"Error accessing S3 object {key}: {error_code} - {str(e)}"
        logger.error(error_msg)
        return {
            'key': key,
            'status': 'error',
            'error': error_msg
        }
    except Exception as e:
        error_msg = f"Unexpected error processing {key}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            'key': key,
            'status': 'error',
            'error': error_msg
        }
    finally:
        # Clean up temporary directory and files
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
                logger.debug(f"Cleaned up temporary directory: {temp_dir}")
            except Exception as e:
                logger.warning(f"Failed to clean up temporary directory {temp_dir}: {str(e)}")


def list_all_s3_objects(s3_client: boto3.client, bucket: str, prefix: str = '') -> List[str]:
    """
    List all objects in an S3 bucket with pagination support.
    
    Args:
        s3_client: Boto3 S3 client
        bucket: S3 bucket name
        prefix: Optional prefix to filter objects
        
    Returns:
        List of object keys
    """
    object_keys = []
    paginator = s3_client.get_paginator('list_objects_v2')
    
    try:
        page_iterator = paginator.paginate(Bucket=bucket, Prefix=prefix)
        for page in page_iterator:
            if 'Contents' in page:
                object_keys.extend([obj['Key'] for obj in page['Contents']])
    except ClientError as e:
        logger.error(f"Error listing objects in bucket {bucket}: {str(e)}")
        raise
    
    return object_keys


def lambda_handler(event: Dict, context) -> Dict:
    """
    AWS Lambda handler function for virus scanning.
    
    Supports two invocation modes:
    1. S3 Event: Triggered by S3 upload events (event-driven)
    2. Manual: Scans all objects in a bucket (full scan)
    
    Args:
        event: Lambda event object (can be S3 event or manual trigger)
        context: Lambda context object
        
    Returns:
        Dictionary with scan results summary
    """
    scan_results = {
        'total_scanned': 0,
        'clean': 0,
        'infected': 0,
        'errors': 0,
        'skipped': 0,
        'details': []
    }
    
    # Initialize S3 client
    s3_client = boto3.client('s3')
    
    # Get bucket name from environment variable or event
    bucket_name = os.environ.get('S3_BUCKET_NAME')
    
    # Handle S3 event trigger
    if 'Records' in event:
        logger.info("Processing S3 event trigger")
        for record in event['Records']:
            if record.get('eventSource') == 'aws:s3':
                bucket_name = record['s3']['bucket']['name']
                key = record['s3']['object']['key']
                
                result = scan_s3_object(s3_client, bucket_name, key)
                scan_results['details'].append(result)
                scan_results['total_scanned'] += 1
                
                if result['status'] == 'infected':
                    scan_results['infected'] += 1
                elif result['status'] == 'clean':
                    scan_results['clean'] += 1
                elif result['status'] == 'error':
                    scan_results['errors'] += 1
                elif result['status'] == 'skipped':
                    scan_results['skipped'] += 1
    
    # Handle manual trigger (scan all objects)
    elif bucket_name:
        logger.info(f"Starting full scan of bucket: {bucket_name}")
        
        try:
            # Get all object keys
            object_keys = list_all_s3_objects(s3_client, bucket_name)
            logger.info(f"Found {len(object_keys)} objects to scan")
            
            # Scan each object
            for key in object_keys:
                # Check if we're approaching Lambda timeout
                if context and context.get_remaining_time_in_millis() < 30000:  # 30 seconds buffer
                    logger.warning("Approaching Lambda timeout, stopping scan")
                    break
                
                result = scan_s3_object(s3_client, bucket_name, key)
                scan_results['details'].append(result)
                scan_results['total_scanned'] += 1
                
                if result['status'] == 'infected':
                    scan_results['infected'] += 1
                elif result['status'] == 'clean':
                    scan_results['clean'] += 1
                elif result['status'] == 'error':
                    scan_results['errors'] += 1
                elif result['status'] == 'skipped':
                    scan_results['skipped'] += 1
                    
        except Exception as e:
            error_msg = f"Error during full bucket scan: {str(e)}"
            logger.error(error_msg, exc_info=True)
            scan_results['error'] = error_msg
            return scan_results
    
    else:
        error_msg = "S3_BUCKET_NAME environment variable not set and no S3 event provided"
        logger.error(error_msg)
        scan_results['error'] = error_msg
        return scan_results
    
    logger.info(f"Scan complete: {scan_results['total_scanned']} scanned, "
                f"{scan_results['infected']} infected, {scan_results['clean']} clean, "
                f"{scan_results['errors']} errors, {scan_results['skipped']} skipped")
    
    return scan_results
