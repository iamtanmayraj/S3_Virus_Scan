import os
import subprocess
import tempfile
import boto3

def scan_file(file_path):
    try:
        # Run the clamscan command
        result = subprocess.run(['clamscan', file_path], capture_output=True)

        # Check the output for virus detection
        output = result.stdout.decode('utf-8')
        if "Infected files: 1" in output:
            return True
        else:
            return False
    except Exception as e:
        print(f"An error occurred: {e}")
        return False

def lambda_handler(event, context):
    try:
        # Specify your S3 bucket name
        bucket_name = 'your-s3-bucket-name'

        # Create an S3 client
        s3 = boto3.client('s3')

        # List objects in the specified bucket
        objects = s3.list_objects(Bucket=bucket_name)

        # Iterate through each object and scan for viruses
        for obj in objects.get('Contents', []):
            key = obj['Key']

            # Download the file from S3 to a temporary directory
            temp_dir = tempfile.mkdtemp()
            temp_file_path = os.path.join(temp_dir, 'downloaded_file')

            s3.download_file(bucket_name, key, temp_file_path)

            # Scan the file for viruses
            is_infected = scan_file(temp_file_path)

            if is_infected:
                print(f"The file '{key}' in the S3 bucket '{bucket_name}' contains a virus.")
            else:
                print(f"The file '{key}' in the S3 bucket '{bucket_name}' is clean.")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        # Clean up: remove the temporary directory
        if os.path.exists(temp_dir):
            os.rmdir(temp_dir)
