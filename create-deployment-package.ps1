# HomePro EC2 Deployment Package Creator
# Creates a clean deployment zip file for EC2 instances

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$packageName = "homepro-ec2-audio-fix-$timestamp.zip"
$tempDir = "temp-deployment"

Write-Host "Creating HomePro EC2 deployment package..." -ForegroundColor Green

# Clean up any existing temp directory
if (Test-Path $tempDir) {
    Remove-Item $tempDir -Recurse -Force
}

# Create temporary directory
New-Item -ItemType Directory -Path $tempDir | Out-Null

# Copy essential application files
Write-Host "checkmark Copying core application files..." -ForegroundColor Green
Copy-Item "app.py" -Destination $tempDir
Copy-Item "application.py" -Destination $tempDir
Copy-Item "auth.py" -Destination $tempDir
Copy-Item "config.py" -Destination $tempDir
Copy-Item "requirements.txt" -Destination $tempDir
Copy-Item "migrate_database.py" -Destination $tempDir

# Copy directories
Write-Host "checkmark Copying templates directory..." -ForegroundColor Green
Copy-Item "templates" -Destination $tempDir -Recurse

Write-Host "checkmark Copying static directory..." -ForegroundColor Green
Copy-Item "static" -Destination $tempDir -Recurse

Write-Host "checkmark Copying .ebextensions directory..." -ForegroundColor Green
Copy-Item ".ebextensions" -Destination $tempDir -Recurse

# Create uploads directory
Write-Host "checkmark Creating uploads directory..." -ForegroundColor Green
New-Item -ItemType Directory -Path "$tempDir\uploads" | Out-Null

# Create production .env template
Write-Host "checkmark Creating production .env template..." -ForegroundColor Green
$envContent = @"
# Production Environment Variables for EC2
# Copy this file to .env and update with your actual values

# Database Configuration
DB_HOST=your-rds-endpoint.region.rds.amazonaws.com
DB_USER=your-db-username
DB_PASSWORD=your-db-password
DB_NAME=homepro_db

# AWS Configuration (leave empty for EC2 IAM role)
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_DEFAULT_REGION=us-east-1
AWS_S3_BUCKET=homepro0723

# Flask Configuration
SECRET_KEY=your-super-secret-key-here
FLASK_ENV=production
"@

$envContent | Out-File -FilePath "$tempDir\.env.template" -Encoding UTF8

# Create deployment README
Write-Host "checkmark Creating DEPLOYMENT_README.md..." -ForegroundColor Green
$readmeContent = @"
# HomePro EC2 Deployment Package

## Package Contents
- **Core Application**: app.py, application.py, auth.py, config.py
- **Dependencies**: requirements.txt
- **Web Assets**: templates/, static/
- **AWS Configuration**: .ebextensions/
- **Database Setup**: migrate_database.py
- **Environment Template**: .env.template

## Recent Fixes Included
- **Audio Upload Fix**: Improved error handling for AWS Transcribe failures
- **AWS Availability Check**: Better detection of AWS service availability
- **Session Conflict Resolution**: Fixed session variable conflicts
- **Enhanced Error Handling**: Comprehensive error handling for AWS services
- **Graceful Degradation**: Fallback to mock data when AWS services fail

## Quick Deployment Steps
1. Upload this package to your EC2 instance
2. Extract: `unzip $packageName`
3. Copy environment: `cp .env.template .env`
4. Edit .env with your actual database and AWS settings
5. Install dependencies: `pip install -r requirements.txt`
6. Initialize database: `python migrate_database.py`
7. Start application: `python app.py`

## Environment Variables Required
- DB_HOST, DB_USER, DB_PASSWORD, DB_NAME
- SECRET_KEY (generate a secure random key)
- AWS credentials (optional if using EC2 IAM role)

## Security Notes
- Never commit .env files to version control
- Use strong, unique SECRET_KEY
- Ensure EC2 security groups allow only necessary traffic
- Use RDS with proper security group configuration

Generated: $(Get-Date)
"@

$readmeContent | Out-File -FilePath "$tempDir\DEPLOYMENT_README.md" -Encoding UTF8

# Create the zip file
Write-Host "Creating deployment package: $packageName" -ForegroundColor Yellow
Compress-Archive -Path "$tempDir\*" -DestinationPath $packageName -Force

# Clean up temp directory
Remove-Item $tempDir -Recurse -Force

Write-Host "checkmark Deployment package created successfully: $packageName" -ForegroundColor Green
Write-Host "Package is ready for EC2 deployment!" -ForegroundColor Cyan

# Show package info
$packageInfo = Get-Item $packageName
Write-Host "Package size: $([math]::Round($packageInfo.Length / 1MB, 2)) MB" -ForegroundColor Gray