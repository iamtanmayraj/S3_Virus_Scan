# S3 Virus Scan

**Create a Lambda using Terraform**
  - run the workflow **lambda_terraform**

**Deploy the Lambda**
  - run the workflow **deploy_lambda**

**Run the application locally**
```bash
  pip install -r requirements.txt
  python virus_check.py
```

Notes : Make sure you have the *make* utility (for MAKEFILE) installed on your system. If you're on a Unix-like system (Linux or macOS), it is likely pre-installed. On Windows, you may need to use a tool like Cygwin or MinGW to have the make command available.  

Command to install cygwin using chocolatey
```bash
choco install cygwin
```
