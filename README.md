# S3 Virus Scan

An AWS Lambda function that automatically scans files in an S3 bucket for viruses using ClamAV. This project uses Terraform for infrastructure as code and GitHub Actions for CI/CD deployment.

## Overview

This project provides an automated virus scanning solution for S3 buckets. The Lambda function:
- Connects to an S3 bucket (via environment variable or S3 event triggers)
- Downloads files from the bucket
- Scans them using ClamAV's `clamscan` utility
- Reports infected files with detailed logging
- Supports both event-driven (S3 uploads) and manual (full bucket scan) modes

## Architecture

- **AWS Lambda**: Serverless function that performs virus scanning
- **Terraform**: Infrastructure as Code for provisioning AWS resources
- **ClamAV**: Open-source antivirus engine for virus detection
- **GitHub Actions**: CI/CD pipelines for automated deployment and code quality checks
- **CloudWatch Logs**: Centralized logging and monitoring

## Features

- ✅ **Event-driven scanning**: Automatically triggered by S3 uploads
- ✅ **Manual full scan**: Scan entire buckets on demand
- ✅ **File size limits**: Configurable maximum file size (default: 100MB)
- ✅ **Comprehensive logging**: Structured logging with different log levels
- ✅ **Error handling**: Robust error handling with detailed error messages
- ✅ **Resource management**: Automatic cleanup of temporary files
- ✅ **S3 pagination**: Handles buckets with more than 1000 objects
- ✅ **Lambda timeout awareness**: Stops before Lambda timeout
- ✅ **Type hints**: Full type annotations for better code maintainability
- ✅ **CI/CD pipelines**: Automated testing, validation, and deployment

## Prerequisites

Before using this project, ensure you have:

- **AWS Account** with appropriate permissions
- **Terraform** installed (v1.0+)
- **Python 3.8+** installed (3.11 recommended)
- **Make utility** installed (pre-installed on Unix-like systems)
- **ClamAV** installed (for local testing)
- **AWS CLI** configured (for manual deployments)
- **GitHub Secrets** configured:
  - `AWS_ACCESS_KEY_ID`
  - `AWS_SECRET_ACCESS_KEY`

### Installing ClamAV

**macOS:**
```bash
brew install clamav
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get update
sudo apt-get install clamav clamav-daemon
```

**Windows:**
```bash
choco install cygwin
# Then install ClamAV through Cygwin
```

## Project Structure

```
S3_Virus_Scan/
├── .github/
│   └── workflows/
│       ├── lambda_terraform.yaml    # Terraform deployment workflow
│       ├── deploy_lambda.yaml       # Lambda code update workflow
│       ├── code-quality.yaml        # Code quality checks (linting, formatting)
│       └── ci.yaml                  # Continuous Integration workflow
├── python/
│   └── virus_check.py               # Lambda function code
├── main.tf                          # Terraform infrastructure configuration
├── terraform.tfvars.example         # Example Terraform variables
├── MAKEFILE                         # Make targets for local development
├── requirements.txt                 # Python dependencies
├── .gitignore                       # Git ignore patterns
└── README.md                        # This file
```

## Setup Instructions

### 1. Local Development

Install Python dependencies:
```bash
make install
# or manually:
pip install -r requirements.txt
```

View all available make commands:
```bash
make help
```

### 2. Configure Terraform Variables

Copy the example variables file and update with your values:
```bash
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars`:
```hcl
aws_region         = "us-east-1"
s3_bucket_name     = "your-s3-bucket-name"
lambda_function_name = "s3-virus-scanner"
lambda_timeout     = 900
lambda_memory_size = 1024
lambda_runtime     = "python3.11"
```

**Important:** Never commit `terraform.tfvars` to version control (it's in `.gitignore`).

### 3. Configure Lambda Environment Variables

The Lambda function uses the `S3_BUCKET_NAME` environment variable. This is automatically set by Terraform from the `s3_bucket_name` variable. You can also set it manually in the AWS Console or via Terraform.

### 4. Test Locally

For local testing, you'll need to:
1. Set up AWS credentials (`aws configure` or environment variables)
2. Have ClamAV installed
3. Create a test event or modify the script

Example test:
```python
# Create a test event
test_event = {
    "Records": [{
        "eventSource": "aws:s3",
        "s3": {
            "bucket": {"name": "your-test-bucket"},
            "object": {"key": "test-file.txt"}
        }
    }]
}

# Or test full bucket scan
test_event = {}  # Empty event triggers full scan
```

## Deployment

### Option 1: Using GitHub Actions Workflows

#### Deploy Infrastructure (Terraform)

1. Go to the **Actions** tab in your GitHub repository
2. Select the **Terraform Deploy** workflow
3. Click **Run workflow**
4. Fill in the required inputs:
   - **Terraform action**: Choose `plan` (to preview) or `apply` (to deploy)
   - **AWS Region**: Your AWS region (e.g., `us-east-1`)
   - **S3 Bucket Name**: The bucket you want to scan
   - **Auto-approve**: Enable only if you're sure (for apply/destroy)
5. Click **Run workflow**

The workflow will:
- Validate Terraform configuration
- Format check
- Initialize Terraform
- Plan or apply changes
- Create/update Lambda function, IAM roles, and policies

#### Deploy Lambda Code

1. Go to the **Actions** tab
2. Select the **Deploy Lambda Function** workflow
3. Click **Run workflow**
4. Fill in the inputs:
   - **AWS Region**: Your AWS region
   - **Lambda Function Name**: Name of your function (default: `s3-virus-scanner`)
   - **Skip validation**: Leave unchecked for code validation
5. Click **Run workflow**

The workflow will:
- Validate Python code
- Verify Lambda function exists
- Package Lambda code
- Deploy to AWS Lambda
- Verify deployment success

#### Code Quality Checks

The **Code Quality Checks** workflow runs automatically on:
- Pull requests to main/master/develop branches
- Pushes to main/master/develop branches

It performs:
- Python syntax validation
- Code formatting checks (Black)
- Linting (Flake8)
- Type checking (mypy)
- Terraform validation
- YAML linting

#### Continuous Integration

The **CI** workflow runs on pull requests and includes:
- Multi-version Python testing (3.8, 3.9, 3.10, 3.11)
- Import verification
- Lambda handler validation
- Terraform plan (on PRs)

### Option 2: Manual Deployment

#### Using Terraform

```bash
# Initialize Terraform
terraform init

# Review the plan (with variables)
terraform plan -var-file="terraform.tfvars"

# Apply the configuration
terraform apply -var-file="terraform.tfvars"
```

Or use individual variables:
```bash
terraform apply \
  -var="aws_region=us-east-1" \
  -var="s3_bucket_name=your-bucket-name" \
  -var="lambda_function_name=s3-virus-scanner"
```

#### Update Lambda Code Manually

```bash
# Package Lambda code
make package-lambda
# or manually:
cd python
zip -r lambda-function.zip . -x "*.pyc" -x "__pycache__/*" -x "*.zip"
cd ..

# Update Lambda function
aws lambda update-function-code \
  --function-name s3-virus-scanner \
  --zip-file fileb://python/lambda-function.zip \
  --region us-east-1
```

## Lambda Function Behavior

### Event-Driven Mode (S3 Events)

When triggered by S3 upload events:
- Scans only the newly uploaded file
- Efficient and cost-effective
- Requires S3 Event Notification configuration

### Manual/Full Scan Mode

When invoked manually or with empty event:
- Scans all objects in the bucket
- Uses pagination for large buckets
- Stops before Lambda timeout
- Returns summary of scan results

### Configuration

The function supports the following environment variables:
- `S3_BUCKET_NAME`: S3 bucket to scan (required for manual mode)
- `LOG_LEVEL`: Logging level (default: INFO)

### Scan Results

The function returns a structured response:
```json
{
  "total_scanned": 10,
  "clean": 8,
  "infected": 1,
  "errors": 1,
  "skipped": 0,
  "details": [
    {
      "key": "file1.txt",
      "status": "clean",
      "size_mb": 0.5
    },
    {
      "key": "file2.exe",
      "status": "infected",
      "size_mb": 2.1
    }
  ]
}
```

## Configuration

### Terraform Variables

All configuration is done through Terraform variables. See `terraform.tfvars.example` for available options:

- `aws_region`: AWS region for resources
- `s3_bucket_name`: S3 bucket to scan
- `lambda_function_name`: Name of the Lambda function
- `lambda_timeout`: Function timeout in seconds (max 900)
- `lambda_memory_size`: Memory allocation in MB (default: 1024)
- `lambda_runtime`: Python runtime version (default: python3.11)

### Lambda Configuration

The Lambda function is configured with:
- **Handler**: `virus_check.lambda_handler`
- **Runtime**: Python 3.11 (configurable)
- **Timeout**: 15 minutes (configurable, max 15 minutes)
- **Memory**: 1 GB (configurable)
- **IAM Permissions**: 
  - CloudWatch Logs (create log groups, streams, put events)
  - S3 (GetObject, ListBucket, HeadObject) for specified bucket

## Important Notes

### ClamAV in Lambda

⚠️ **Important**: ClamAV needs to be included in the Lambda deployment package. The current setup assumes ClamAV is available. Options:

1. **Lambda Layer** (Recommended): Create a Lambda layer with ClamAV binaries
2. **Container Image**: Use a container image with ClamAV pre-installed
3. **Custom Runtime**: Build a custom runtime with ClamAV
4. **Community Layers**: Use community-maintained ClamAV Lambda layers

Example using a Lambda layer:
```bash
# Add to main.tf
resource "aws_lambda_layer_version" "clamav" {
  filename   = "clamav-layer.zip"
  layer_name = "clamav"
  # ... layer configuration
}

# Attach to Lambda function
resource "aws_lambda_function" "s3_virus_scanner" {
  # ... existing configuration
  layers = [aws_lambda_layer_version.clamav.arn]
}
```

### File Size Limits

- Default maximum file size: **100 MB**
- Configurable via `MAX_FILE_SIZE_MB` constant in code
- Files exceeding the limit are skipped with a warning

### Cost Considerations

- **Lambda execution**: Based on duration and memory
- **S3 data transfer**: Downloading files for scanning
- **CloudWatch Logs**: Log storage (30-day retention configured)
- **Recommendation**: Use S3 Event Notifications to scan only new uploads

### Security Best Practices

- ✅ IAM policies follow least privilege principle
- ✅ S3 access restricted to specified bucket only
- ✅ Environment variables for configuration
- ✅ No hardcoded credentials
- ✅ Proper error handling to avoid information leakage

## Troubleshooting

### Local Testing Issues

- **ClamAV not found**: 
  ```bash
  which clamscan  # Verify installation
  export PATH=$PATH:/path/to/clamav/bin  # Add to PATH if needed
  ```

- **S3 access denied**: 
  - Verify AWS credentials: `aws sts get-caller-identity`
  - Check IAM permissions for S3 access
  - Verify bucket name is correct

- **Import errors**: 
  ```bash
  pip install -r requirements.txt
  ```

- **Python version mismatch**: 
  - Ensure Python 3.8+ is installed
  - Use `python3` instead of `python` if needed

### Lambda Deployment Issues

- **Handler not found**: 
  - Verify handler is set to `virus_check.lambda_handler`
  - Check that `virus_check.py` is in the root of the zip package

- **Timeout errors**: 
  - Increase Lambda timeout in Terraform variables
  - Consider scanning smaller files or using event-driven mode
  - Check CloudWatch Logs for slow operations

- **Memory errors**: 
  - Increase Lambda memory allocation
  - Reduce `MAX_FILE_SIZE_MB` if scanning large files

- **ClamAV not available**: 
  - Ensure ClamAV is included in deployment package or Lambda layer
  - Check Lambda execution logs for ClamAV errors
  - Verify ClamAV binaries are compatible with Lambda runtime

- **Permission errors**: 
  - Verify IAM role has S3 permissions
  - Check bucket policy allows Lambda access
  - Verify CloudWatch Logs permissions

### Terraform Issues

- **State lock errors**: 
  ```bash
  terraform force-unlock <LOCK_ID>
  ```

- **Variable not set**: 
  - Use `terraform.tfvars` file
  - Or pass variables via command line: `-var="key=value"`

- **Provider version conflicts**: 
  ```bash
  terraform init -upgrade
  ```

## Monitoring

### CloudWatch Logs

View Lambda execution logs:
```bash
aws logs tail /aws/lambda/s3-virus-scanner --follow
```

### CloudWatch Metrics

Monitor Lambda function:
- Invocations
- Duration
- Errors
- Throttles
- Memory usage

### Log Analysis

The function logs include:
- `INFO`: Normal operations, scan results
- `WARNING`: Infected files detected, skipped files
- `ERROR`: Scan failures, S3 access errors

Search for infected files:
```bash
aws logs filter-log-events \
  --log-group-name /aws/lambda/s3-virus-scanner \
  --filter-pattern "VIRUS DETECTED"
```

## Future Improvements

- [x] Environment variable support
- [x] Event-driven scanning support
- [x] Comprehensive error handling
- [x] Structured logging
- [x] File size limits
- [x] S3 pagination support
- [x] CI/CD pipelines
- [x] Code quality checks
- [ ] S3 Event Notifications integration (Terraform)
- [ ] Quarantine mechanism for infected files
- [ ] SNS/Email notifications for infected files
- [ ] Support for scanning specific file types only
- [ ] Unit tests and integration tests
- [ ] Lambda layer for ClamAV (Terraform module)
- [ ] CloudWatch metrics and alarms
- [ ] Support for multiple S3 buckets
- [ ] Dead Letter Queue configuration
- [ ] VPC configuration for private S3 buckets

## Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Ensure code quality checks pass (`make lint`, `make format`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

### Development Guidelines

- Follow PEP 8 style guide for Python code
- Use type hints for function parameters and return values
- Add docstrings to functions and classes
- Update tests when adding new features
- Update README.md for significant changes
- Run `make help` to see available development commands

## License

[Specify your license here]

## Support

For issues, questions, or contributions:
- Open an issue on GitHub
- Check CloudWatch Logs for Lambda execution details
- Review Terraform plan output for infrastructure issues
