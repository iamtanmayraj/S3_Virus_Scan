import os
import subprocess
import tempfile

def scan_file(file_path):
    try:
        # Create a temporary directory to store the scanned file
        temp_dir = tempfile.mkdtemp()
        temp_file_path = os.path.join(temp_dir, 'uploaded_file')

        # Copy the file to the temporary directory
        os.rename(file_path, temp_file_path)

        # Run the clamscan command
        result = subprocess.run(['clamscan', temp_file_path], capture_output=True)

        # Check the output for virus detection
        output = result.stdout.decode('utf-8')
        if "Infected files: 1" in output:
            print(f"The file '{file_path}' contains a virus.")
        else:
            print(f"The file '{file_path}' is clean.")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        # Clean up: remove the temporary directory
        if os.path.exists(temp_dir):
            os.rmdir(temp_dir)

def lambda_handler(event, context):
    try:
        # Assuming the file path is provided in the Lambda event
        file_path = event.get('file_path')
        if file_path:
            scan_file(file_path)
        else:
            print("File path not provided in the event.")
    except Exception as e:
        print(f"An error occurred: {e}")

# Example event:
# {
#   "file_path": "/tmp/uploaded_file.txt"
# }
