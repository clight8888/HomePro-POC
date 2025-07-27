# HomePro AWS Deployment Checklist

## Pre-Deployment Setup

### 1. AWS Account Setup
- [ ] AWS account created and configured
- [ ] AWS CLI installed and configured (`aws configure`)
- [ ] Elastic Beanstalk CLI installed (`pip install awsebcli`)

### 2. Environment Variables
- [ ] `SECRET_KEY` - Strong production secret key
- [ ] `AWS_REGION` - AWS region (e.g., us-east-1)
- [ ] `AWS_S3_BUCKET` - Default S3 bucket name
- [ ] `DATABASE_URL` - Production database URL (optional)
- [ ] `FLASK_ENV` - Set to 'production'

### 3. S3 Buckets
- [ ] Create `new-audio-files` bucket for audio uploads
- [ ] Create default uploads bucket (e.g., `homepro-uploads`)
- [ ] Configure bucket permissions and lifecycle policies

### 4. IAM Permissions
- [ ] Create IAM role for Elastic Beanstalk
- [ ] Attach S3 access policies
- [ ] Attach Transcribe and Comprehend policies
- [ ] Configure instance profile

## Deployment Steps

### 1. Initialize Application
```bash
eb init --platform python-3.9 --region us-east-1 HomePro
```

### 2. Deploy Infrastructure
```bash
aws cloudformation deploy \
    --template-file cloudformation-template.json \
    --stack-name homepro-infrastructure \
    --capabilities CAPABILITY_IAM \
    --region us-east-1
```

### 3. Create Environment
```bash
eb create homepro-prod \
    --instance-type t3.small \
    --min-instances 1 \
    --max-instances 3
```

### 4. Set Environment Variables
```bash
eb setenv SECRET_KEY="your-production-secret-key"
eb setenv AWS_REGION="us-east-1"
eb setenv AWS_S3_BUCKET="homepro-uploads"
eb setenv FLASK_ENV="production"
```

### 5. Deploy Application
```bash
eb deploy homepro-prod
```

## Post-Deployment

### 1. Verification
- [ ] Application loads successfully
- [ ] Audio upload functionality works
- [ ] S3 integration working
- [ ] Database operations functional
- [ ] User registration/login working

### 2. Security
- [ ] HTTPS configured (SSL certificate)
- [ ] Security groups properly configured
- [ ] Database access restricted
- [ ] S3 bucket policies reviewed

### 3. Monitoring
- [ ] CloudWatch alarms configured
- [ ] Log monitoring set up
- [ ] Performance monitoring enabled
- [ ] Cost monitoring configured

### 4. Backup & Recovery
- [ ] Database backup strategy
- [ ] S3 versioning enabled
- [ ] Disaster recovery plan documented

## Production Optimization

### 1. Performance
- [ ] Auto-scaling configured
- [ ] Load balancer health checks
- [ ] CDN for static assets (CloudFront)
- [ ] Database connection pooling

### 2. Cost Management
- [ ] Instance right-sizing
- [ ] S3 lifecycle policies
- [ ] Reserved instances (if applicable)
- [ ] Cost alerts configured

### 3. Maintenance
- [ ] Automated deployments set up
- [ ] Staging environment created
- [ ] Update procedures documented
- [ ] Rollback procedures tested

## Troubleshooting Commands

```bash
# Check application status
eb status

# View logs
eb logs

# SSH into instance
eb ssh

# Restart application
eb restart

# Check environment health
eb health

# Open application in browser
eb open
```

## Emergency Contacts & Resources

- AWS Support: [Support Case URL]
- Application Repository: [GitHub URL]
- Documentation: [Wiki/Docs URL]
- Team Contacts: [Contact Information]