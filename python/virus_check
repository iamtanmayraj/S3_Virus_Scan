import pyclamav

def scan_file(file_path):
    try:
        virus_found, virus_name = pyclamav.scanfile(file_path)
        if virus_found:
            print(f"The file '{file_path}' contains a virus: {virus_name}")
        else:
            print(f"The file '{file_path}' is clean.")
    except Exception as e:
        print(f"An error occurred: {e}")

# Replace 'your_file_path' with the path to the file you want to scan
file_path = 'your_file_path'
scan_file(file_path)
