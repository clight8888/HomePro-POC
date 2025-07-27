# PowerShell Deployment Script for HomePro (Windows)
# This script works around EB CLI Windows compatibility issues

param(
    [Parameter(Mandatory=$true)]
    [string]$DBPassword
)

Write-Host "🚀 HomePro Windows Deployment Script" -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Green

# Check AWS CLI
Write-Host "🔍 Checking AWS CLI..." -ForegroundColor Yellow
if (!(Get-Command aws -ErrorAction SilentlyContinue)) {
    Write-Host "❌ AWS CLI not found!" -ForegroundColor Red
    Write-Host "📥 Install from: https://aws.amazon.com/cli/" -ForegroundColor Cyan
    exit 1
}
Write-Host "✅ AWS CLI found" -ForegroundColor Green

# Test AWS credentials
Write-Host "🔐 Checking AWS credentials..." -ForegroundColor Yellow
try {
    $identity = aws sts get-caller-identity --output json | ConvertFrom-Json
    Write-Host "✅ AWS credentials configured for user: $($identity.Arn)" -ForegroundColor Green
} catch {
    Write-Host "❌ AWS credentials not configured!" -ForegroundColor Red
    Write-Host "🔧 Run: aws configure" -ForegroundColor Cyan
    exit 1
}

# Set variables
$STACK_NAME = "homepro-infrastructure"
$REGION = "us-east-1"
$APP_NAME = "HomePro"

Write-Host "📦 Deploying CloudFormation infrastructure..." -ForegroundColor Yellow
Write-Host "Stack: $STACK_NAME" -ForegroundColor Cyan
Write-Host "Region: $REGION" -ForegroundColor Cyan

# Deploy CloudFormation stack
try {
    aws cloudformation deploy `
        --template-file cloudformation-rds-template.json `
        --stack-name $STACK_NAME `
        --capabilities CAPABILITY_IAM `
        --region $REGION `
        --parameter-overrides DBPassword=$DBPassword

    Write-Host "✅ Infrastructure deployed successfully!" -ForegroundColor Green
} catch {
    Write-Host "❌ Infrastructure deployment failed!" -ForegroundColor Red
    Write-Host "Error: $_" -ForegroundColor Red
    exit 1
}

# Get stack outputs
Write-Host "📋 Retrieving stack outputs..." -ForegroundColor Yellow
try {
    $outputs = aws cloudformation describe-stacks `
        --stack-name $STACK_NAME `
        --region $REGION `
        --query 'Stacks[0].Outputs' `
        --output json | ConvertFrom-Json

    $dbEndpoint = ($outputs | Where-Object { $_.OutputKey -eq "DatabaseEndpoint" }).OutputValue
    $s3Bucket = ($outputs | Where-Object { $_.OutputKey -eq "S3BucketName" }).OutputValue
    $iamRole = ($outputs | Where-Object { $_.OutputKey -eq "IAMRoleArn" }).OutputValue

    Write-Host "✅ Stack outputs retrieved:" -ForegroundColor Green
    Write-Host "  📊 Database Endpoint: $dbEndpoint" -ForegroundColor Cyan
    Write-Host "  🪣 S3 Bucket: $s3Bucket" -ForegroundColor Cyan
    Write-Host "  🔐 IAM Role: $iamRole" -ForegroundColor Cyan
} catch {
    Write-Host "⚠️  Could not retrieve all stack outputs" -ForegroundColor Yellow
}

# Create deployment package
Write-Host "📦 Creating deployment package..." -ForegroundColor Yellow
try {
    if (Test-Path "homepro-deployment.zip") {
        Remove-Item "homepro-deployment.zip" -Force
    }
    
    # Exclude unnecessary files
    $excludeFiles = @("venv", ".git", "__pycache__", "*.pyc", ".env", "homepro-deployment.zip")
    
    # Get all files except excluded ones
    $files = Get-ChildItem -Recurse | Where-Object { 
        $exclude = $false
        foreach ($pattern in $excludeFiles) {
            if ($_.FullName -like "*$pattern*") {
                $exclude = $true
                break
            }
        }
        !$exclude
    }
    
    Compress-Archive -Path $files -DestinationPath "homepro-deployment.zip" -Force
    Write-Host "✅ Deployment package created: homepro-deployment.zip" -ForegroundColor Green
} catch {
    Write-Host "❌ Failed to create deployment package!" -ForegroundColor Red
    Write-Host "Error: $_" -ForegroundColor Red
}

# Display next steps
Write-Host ""
Write-Host "🎉 Infrastructure Setup Complete!" -ForegroundColor Green
Write-Host "=================================" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Next Steps:" -ForegroundColor Yellow
Write-Host "1. Go to AWS Elastic Beanstalk Console:" -ForegroundColor White
Write-Host "   https://console.aws.amazon.com/elasticbeanstalk/" -ForegroundColor Cyan
Write-Host ""
Write-Host "2. Create New Application:" -ForegroundColor White
Write-Host "   - Application name: $APP_NAME" -ForegroundColor Cyan
Write-Host "   - Platform: Python 3.9" -ForegroundColor Cyan
Write-Host "   - Upload: homepro-deployment.zip" -ForegroundColor Cyan
Write-Host ""
Write-Host "3. Configure Environment Variables:" -ForegroundColor White
Write-Host "   SECRET_KEY = your-production-secret-key" -ForegroundColor Cyan
Write-Host "   AWS_REGION = $REGION" -ForegroundColor Cyan
Write-Host "   AWS_S3_BUCKET = $s3Bucket" -ForegroundColor Cyan
if ($dbEndpoint) {
    Write-Host "   DB_HOST = $dbEndpoint" -ForegroundColor Cyan
}
Write-Host "   DB_USERNAME = homeproadmin" -ForegroundColor Cyan
Write-Host "   DB_PASSWORD = [your-password]" -ForegroundColor Cyan
Write-Host "   DB_NAME = homeprodb" -ForegroundColor Cyan
Write-Host "   FLASK_ENV = production" -ForegroundColor Cyan
Write-Host ""
Write-Host "4. Deploy and test your application!" -ForegroundColor White
Write-Host ""
Write-Host "💡 Tip: Keep this terminal output for reference" -ForegroundColor Yellow