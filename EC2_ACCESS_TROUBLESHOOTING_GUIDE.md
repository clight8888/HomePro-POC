# EC2 Instance Access Guide for HomePro Application

## Current Situation
- **Old Environment**: `HomePro072207-env` - Status: "Info" (VPC communication issues)
- **New Environment**: `HomePro-Fixed-env` - Status: "Launching" (Correct configuration)

## Problem with Old Environment
The old environment has ELB in private subnets, causing communication failures:
- ELB Subnets: `subnet-006acebce26f6435b,subnet-0edc5f96140ea34a5` (Private)
- EC2 Subnets: `subnet-0edc5f96140ea34a5,subnet-006acebce26f6435b` (Private)
- Result: No internet access for load balancer

## New Environment Configuration
The new environment has the correct setup:
- **ELB Subnets**: `subnet-09f21c1ff6a24e86e,subnet-08bf34578b894452f` (Public)
- **EC2 Subnets**: `subnet-0edc5f96140ea34a5,subnet-006acebce26f6435b` (Private)
- **Result**: Secure EC2 instances with internet-accessible load balancer

## How to Access EC2 Instances

### Method 1: AWS Systems Manager Session Manager (Recommended)

#### Step 1: Wait for Environment to be Ready
```bash
# Check environment status
aws elasticbeanstalk describe-environments --environment-names "HomePro-Fixed-env" --region us-east-1 --query "Environments[0].[EnvironmentName,Status,Health]" --output table
```

#### Step 2: Get Instance ID
```bash
# Get EC2 instance ID
aws elasticbeanstalk describe-environment-resources --environment-name "HomePro-Fixed-env" --region us-east-1 --query "EnvironmentResources.Instances[*].Id" --output table
```

#### Step 3: Connect via Session Manager
```bash
# Connect to instance (replace INSTANCE_ID with actual ID)
aws ssm start-session --target INSTANCE_ID --region us-east-1
```

### Method 2: CloudWatch Logs (No Instance Access Needed)

#### Check Application Logs
```bash
# List log groups
aws logs describe-log-groups --log-group-name-prefix "/aws/elasticbeanstalk/HomePro-Fixed-env" --region us-east-1

# Get recent logs (replace LOG_GROUP_NAME)
aws logs tail LOG_GROUP_NAME --region us-east-1 --follow
```

### Method 3: Elastic Beanstalk Events
```bash
# Check recent events
aws elasticbeanstalk describe-events --environment-name "HomePro-Fixed-env" --region us-east-1 --max-records 20 --query "Events[*].[EventDate,Severity,Message]" --output table
```

## Commands to Check Application Status

### Once Connected to EC2 Instance:

#### 1. Check Application Process
```bash
# Check if Python/Flask app is running
sudo ps aux | grep python
sudo ps aux | grep flask

# Check application logs
sudo tail -f /var/log/eb-engine.log
sudo tail -f /var/log/eb-hooks.log
```

#### 2. Check Web Server Status
```bash
# Check nginx status
sudo systemctl status nginx

# Check nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

#### 3. Check Application Health
```bash
# Test local application
curl http://localhost/
curl http://localhost/health

# Check if app is listening on correct port
sudo netstat -tlnp | grep :80
sudo netstat -tlnp | grep python
```

#### 4. Check Environment Variables
```bash
# Check if environment variables are set
sudo cat /opt/elasticbeanstalk/deployment/env
printenv | grep -E "(DB_|AWS_|FLASK_)"
```

#### 5. Check Database Connectivity
```bash
# Test database connection (if MySQL client is available)
mysql -h homepro-mysql-db.c0zi8ey8usr4.us-east-1.rds.amazonaws.com -u homeproadmin -p homeprodb

# Or test with Python
python3 -c "
import pymysql
try:
    conn = pymysql.connect(
        host='homepro-mysql-db.c0zi8ey8usr4.us-east-1.rds.amazonaws.com',
        user='homeproadmin',
        password='SecurePassword123!',
        database='homeprodb'
    )
    print('Database connection successful')
    conn.close()
except Exception as e:
    print(f'Database connection failed: {e}')
"
```

## Quick Status Check Commands

### Environment Status
```bash
# Check all environments
aws elasticbeanstalk describe-environments --region us-east-1 --query "Environments[*].[EnvironmentName,Status,Health]" --output table

# Check specific environment health
aws elasticbeanstalk describe-environment-health --environment-name "HomePro-Fixed-env" --attribute-names All --region us-east-1
```

### Application URL
```bash
# Get application URL
aws elasticbeanstalk describe-environments --environment-names "HomePro-Fixed-env" --region us-east-1 --query "Environments[0].CNAME"
```

## Troubleshooting Checklist

### If Environment Shows "Info" Status:
1. ✅ Check VPC configuration (subnets)
2. ✅ Verify ELB is in public subnets
3. ✅ Ensure EC2 instances can reach internet (via NAT Gateway)
4. ✅ Check security groups allow required traffic

### If Application Not Responding:
1. Check application logs in CloudWatch
2. Verify database connectivity
3. Check environment variables
4. Ensure all required packages are installed
5. Verify application is listening on correct port

## Next Steps

1. **Wait for new environment** to reach "Ready" status
2. **Test application URL** once environment is ready
3. **Access EC2 instance** using Session Manager if needed
4. **Terminate old environment** once new one is working
5. **Update DNS/domain** to point to new environment

## Expected Timeline
- Environment creation: 10-15 minutes
- Application deployment: 5-10 minutes
- Total time: 15-25 minutes

Monitor progress with:
```bash
watch -n 30 'aws elasticbeanstalk describe-environments --environment-names "HomePro-Fixed-env" --region us-east-1 --query "Environments[0].[EnvironmentName,Status,Health]" --output table'
```