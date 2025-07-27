# AWS Free Tier Deployment Guide for HomePro

## 🆓 AWS Free Tier Configuration

Yes! You can absolutely use AWS Free Tier with Elastic Beanstalk. Here's what's included and how to configure it:

### AWS Free Tier Limits (12 months from account creation)

#### Elastic Beanstalk (Free Tier Eligible)
- **EC2 Instance**: t2.micro (1 vCPU, 1 GB RAM)
- **Usage**: 750 hours/month (enough for 1 instance running 24/7)
- **Cost**: FREE for the first 12 months

#### S3 Storage
- **Storage**: 5 GB of standard storage
- **Requests**: 20,000 GET requests, 2,000 PUT requests
- **Data Transfer**: 15 GB out per month

#### Other AWS Services (Free Tier)
- **AWS Transcribe**: 60 minutes/month
- **AWS Comprehend**: 50,000 units of text (5M characters)
- **CloudWatch**: Basic monitoring included

### Free Tier Deployment Commands

#### Option 1: Using the Updated Deploy Script
```bash
./deploy.sh
```
The script now automatically uses `t2.micro` instance type.

#### Option 2: Manual Commands (Free Tier)
```bash
# Initialize with free tier settings
eb init --platform python-3.9 --region us-east-1 HomePro

# Create environment with free tier instance
eb create homepro-prod \
    --instance-type t2.micro \
    --min-instances 1 \
    --max-instances 1 \
    --single-instance
```

### Free Tier Optimizations

#### 1. Single Instance Deployment
```bash
# Use single instance (no load balancer) to save costs
eb create homepro-prod \
    --instance-type t2.micro \
    --single-instance
```

#### 2. Environment Variables for Free Tier
```bash
eb setenv SECRET_KEY="your-secret-key"
eb setenv AWS_REGION="us-east-1"
eb setenv AWS_S3_BUCKET="homepro-uploads"
eb setenv FLASK_ENV="production"
eb setenv MAX_CONTENT_LENGTH="16777216"  # 16MB limit for free tier
```

### Cost Monitoring

#### Set Up Billing Alerts
1. Go to AWS Billing Dashboard
2. Set up billing alerts for $1, $5, $10
3. Monitor usage in AWS Cost Explorer

#### Free Tier Usage Tracking
- Check AWS Free Tier usage dashboard
- Monitor EC2, S3, and AI service usage
- Set up CloudWatch alarms

### Performance Considerations for t2.micro

#### Memory Optimization
- **RAM**: Only 1 GB available
- **Recommendation**: Limit concurrent users during testing
- **Database**: Use SQLite for development, consider RDS free tier for production

#### CPU Credits
- t2.micro uses burstable performance
- Monitor CPU credit balance in CloudWatch
- Optimize code for efficiency

### Free Tier Deployment Timeline

1. **Month 1-12**: Everything free (within limits)
2. **After 12 months**: 
   - t2.micro: ~$8.50/month
   - S3: ~$0.023/GB/month
   - AI services: Pay per use

### Alternative Free Options

#### 1. AWS Lightsail (Always Free Options)
```bash
# Consider Lightsail for simple deployments
# $3.50/month for 512 MB RAM, 1 vCPU
```

#### 2. Heroku Free Alternative
```bash
# If you prefer, Heroku has similar free tiers
# But AWS gives you more control and learning
```

### Monitoring Free Tier Usage

#### Check Current Usage
```bash
# AWS CLI command to check free tier usage
aws support describe-trusted-advisor-checks --language en
```

#### CloudWatch Free Tier Monitoring
- Basic monitoring included
- Custom metrics: First 10 metrics free
- Alarms: First 10 alarms free

### Best Practices for Free Tier

1. **Start Small**: Use t2.micro and scale later
2. **Monitor Usage**: Set up billing alerts
3. **Optimize Code**: Efficient code = lower resource usage
4. **Use Free Services**: Leverage free tier AI services
5. **Plan Ahead**: Know when free tier expires

### Free Tier Deployment Checklist

- [ ] AWS account less than 12 months old
- [ ] Using t2.micro instance type
- [ ] Single instance deployment
- [ ] Billing alerts configured
- [ ] Free tier usage monitoring enabled
- [ ] S3 usage under 5 GB
- [ ] AI service usage monitored

Your HomePro application is now configured to run entirely within AWS Free Tier limits!