#!/bin/bash

# HomePro AWS Deployment Script with RDS MySQL Free Tier
# This script automates the deployment process

set -e

echo "🚀 Starting HomePro AWS Deployment with RDS MySQL..."

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI is not installed. Please install it first:"
    echo "pip install awscli"
    exit 1
fi

# Check if EB CLI is installed
if ! command -v eb &> /dev/null; then
    echo "❌ Elastic Beanstalk CLI is not installed. Please install it first:"
    echo "pip install awsebcli"
    exit 1
fi

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    echo "❌ AWS credentials not configured. Please run:"
    echo "aws configure"
    exit 1
fi

echo "✅ Prerequisites check passed"

# Prompt for database password
echo "🔐 Please enter a secure password for the MySQL database (8-41 characters):"
read -s DB_PASSWORD
echo

if [ ${#DB_PASSWORD} -lt 8 ]; then
    echo "❌ Password must be at least 8 characters long"
    exit 1
fi

# Deploy CloudFormation stack for infrastructure including RDS
echo "📦 Deploying infrastructure with RDS MySQL..."
aws cloudformation deploy \
    --template-file cloudformation-rds-template.json \
    --stack-name homepro-infrastructure \
    --capabilities CAPABILITY_IAM \
    --region us-east-1 \
    --parameter-overrides DBPassword=$DB_PASSWORD

echo "✅ Infrastructure with RDS MySQL deployed successfully"

# Get database endpoint from CloudFormation outputs
DB_ENDPOINT=$(aws cloudformation describe-stacks \
    --stack-name homepro-infrastructure \
    --region us-east-1 \
    --query 'Stacks[0].Outputs[?OutputKey==`DatabaseEndpoint`].OutputValue' \
    --output text)

echo "📊 Database endpoint: $DB_ENDPOINT"

# Initialize Elastic Beanstalk (if not already done)
if [ ! -d ".elasticbeanstalk" ]; then
    echo "🔧 Initializing Elastic Beanstalk application..."
    eb init --platform python-3.9 --region us-east-1 HomePro
fi

# Create environment if it doesn't exist
if ! eb list | grep -q "homepro-prod"; then
    echo "🌍 Creating production environment (AWS Free Tier with RDS MySQL)..."
    eb create homepro-prod \
        --instance-type t2.micro \
        --min-instances 1 \
        --max-instances 1 \
        --envvars SECRET_KEY=your-production-secret-key,AWS_REGION=us-east-1,AWS_S3_BUCKET=homepro-uploads,DB_HOST=$DB_ENDPOINT,DB_USERNAME=homeproadmin,DB_PASSWORD=$DB_PASSWORD,DB_NAME=homeprodb,FLASK_ENV=production
else
    echo "🔄 Deploying to existing environment..."
    eb setenv DB_HOST=$DB_ENDPOINT DB_USERNAME=homeproadmin DB_PASSWORD=$DB_PASSWORD DB_NAME=homeprodb FLASK_ENV=production
    eb deploy homepro-prod
fi

echo "✅ Application deployed successfully with RDS MySQL!"

# Get application URL
APP_URL=$(eb status homepro-prod | grep "CNAME" | awk '{print $2}')
echo "🌐 Application URL: http://$APP_URL"
echo "🗄️  Database: MySQL RDS (Free Tier) at $DB_ENDPOINT"

echo "🎉 Deployment completed successfully!"
echo ""
echo "Next steps:"
echo "1. Test the application at: http://$APP_URL"
echo "2. Verify database connectivity"
echo "3. Configure SSL certificate in AWS Certificate Manager"
echo "4. Set up monitoring and alerts"
echo "5. Review security settings"