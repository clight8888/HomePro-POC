# HomePro AWS Deployment Guide

## Prerequisites

1. **AWS CLI Installation**
   ```bash
   # Install AWS CLI
   pip install awscli
   
   # Configure AWS credentials
   aws configure
   ```

2. **Elastic Beanstalk CLI Installation**
   ```bash
   pip install awsebcli
   ```

## Deployment Steps

### 1. Initialize Elastic Beanstalk Application

```bash
# Navigate to your project directory
cd /path/to/HomePro

# Initialize EB application
eb init

# Follow the prompts:
# - Select region (e.g., us-east-1)
# - Create new application: HomePro
# - Select Python platform
# - Choose Python 3.9+ version
# - Setup SSH: Yes (recommended)
```

### 2. Create Environment and Deploy

```bash
# Create and deploy to production environment
eb create homepro-prod

# Or create staging environment first
eb create homepro-staging
```

### 3. Set Environment Variables

```bash
# Set production environment variables
eb setenv SECRET_KEY="your-super-secret-production-key-here"
eb setenv AWS_REGION="us-east-1"
eb setenv DATABASE_URL="your-rds-database-url"  # Optional: Use RDS instead of SQLite
```

### 4. Create S3 Buckets

```bash
# Create the audio files bucket
aws s3 mb s3://new-audio-files --region us-east-1

# Create default bucket for other files (optional)
aws s3 mb s3://homepro-uploads --region us-east-1

# Set bucket policy for the application
eb setenv AWS_S3_BUCKET="homepro-uploads"
```

### 5. Set Up IAM Permissions

Create an IAM role for your Elastic Beanstalk application with the following permissions:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:PutObject",
                "s3:DeleteObject"
            ],
            "Resource": [
                "arn:aws:s3:::new-audio-files/*",
                "arn:aws:s3:::homepro-uploads/*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "transcribe:StartTranscriptionJob",
                "transcribe:GetTranscriptionJob",
                "transcribe:ListTranscriptionJobs"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "comprehend:DetectEntities",
                "comprehend:DetectKeyPhrases",
                "comprehend:DetectSentiment"
            ],
            "Resource": "*"
        }
    ]
}
```

### 6. Deploy Updates

```bash
# Deploy code changes
eb deploy

# Check application status
eb status

# View logs
eb logs

# Open application in browser
eb open
```

## Database Setup (Optional: RDS)

For production, consider using Amazon RDS instead of SQLite:

```bash
# Create RDS PostgreSQL instance
aws rds create-db-instance \
    --db-instance-identifier homepro-db \
    --db-instance-class db.t3.micro \
    --engine postgres \
    --master-username homeproadmin \
    --master-user-password YourSecurePassword123 \
    --allocated-storage 20 \
    --vpc-security-group-ids sg-xxxxxxxxx

# Update environment variable
eb setenv DATABASE_URL="postgresql://homeproadmin:YourSecurePassword123@homepro-db.xxxxxxxxx.us-east-1.rds.amazonaws.com:5432/postgres"
```

## SSL Certificate (Optional)

```bash
# Request SSL certificate through AWS Certificate Manager
aws acm request-certificate \
    --domain-name yourdomain.com \
    --domain-name www.yourdomain.com \
    --validation-method DNS

# Configure load balancer to use HTTPS
eb config
```

## Monitoring and Scaling

```bash
# Configure auto-scaling
eb config

# Set up CloudWatch alarms
aws cloudwatch put-metric-alarm \
    --alarm-name "HomePro-HighCPU" \
    --alarm-description "Alarm when CPU exceeds 70%" \
    --metric-name CPUUtilization \
    --namespace AWS/EC2 \
    --statistic Average \
    --period 300 \
    --threshold 70 \
    --comparison-operator GreaterThanThreshold
```

## Troubleshooting

1. **Check logs**: `eb logs`
2. **SSH into instance**: `eb ssh`
3. **Check environment health**: `eb health`
4. **Restart application**: `eb restart`

## Cost Optimization

- Use t3.micro instances for development/staging
- Set up auto-scaling to handle traffic spikes
- Use S3 lifecycle policies for old audio files
- Monitor costs with AWS Cost Explorer

## Security Best Practices

1. Use environment variables for all secrets
2. Enable VPC for database security
3. Use IAM roles with minimal permissions
4. Enable CloudTrail for audit logging
5. Regular security updates via EB platform updates