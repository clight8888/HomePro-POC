# 🔧 EC2 Private Instance Access & Troubleshooting Guide

## 🎯 **Accessing Private EC2 Instances**

Since your EC2 instances are in **private subnets**, traditional SSH won't work. Use **AWS Systems Manager Session Manager** for secure access.

---

## 🚀 **Method 1: AWS Systems Manager Session Manager (Recommended)**

### **Step 1: Find Your EC2 Instance ID**
```powershell
# Get Elastic Beanstalk environment instances
aws elasticbeanstalk describe-environment-resources --environment-name YOUR_EB_ENVIRONMENT_NAME --region us-east-1 --query "EnvironmentResources.Instances[*].Id" --output table
```

### **Step 2: Start Session Manager Session**
```powershell
# Connect to instance via Session Manager
aws ssm start-session --target i-YOUR-INSTANCE-ID --region us-east-1
```

### **Step 3: Check Application Status**
Once connected, run these commands:

```bash
# Check if your Flask app is running
sudo ps aux | grep python

# Check application logs
sudo tail -f /var/log/eb-engine.log
sudo tail -f /var/log/eb-hooks.log

# Check web server logs
sudo tail -f /var/log/httpd/access_log
sudo tail -f /var/log/httpd/error_log

# Check if port 80 is listening
sudo netstat -tlnp | grep :80

# Check system status
sudo systemctl status httpd
sudo systemctl status eb-engine
```

---

## 🔍 **Method 2: EB CLI Commands (Alternative)**

### **Check Environment Status:**
```powershell
# Get overall environment health
eb status

# Get detailed health information
eb health --refresh

# View recent logs
eb logs

# Get real-time logs
eb logs --all
```

### **Application-Specific Logs:**
```powershell
# View application logs specifically
eb logs --log-group /aws/elasticbeanstalk/YOUR_ENV_NAME/var/log/eb-engine.log

# View web server logs
eb logs --log-group /aws/elasticbeanstalk/YOUR_ENV_NAME/var/log/httpd/error_log
```

---

## 🛠️ **Method 3: CloudWatch Logs (No Instance Access Needed)**

### **View Logs in AWS Console:**
1. Go to **CloudWatch** → **Log Groups**
2. Find your EB environment log group: `/aws/elasticbeanstalk/YOUR_ENV_NAME/`
3. Check these log streams:
   - `var/log/eb-engine.log` - Deployment logs
   - `var/log/httpd/error_log` - Web server errors
   - `var/log/httpd/access_log` - Web requests

### **CLI Access to CloudWatch Logs:**
```powershell
# List log groups
aws logs describe-log-groups --log-group-name-prefix "/aws/elasticbeanstalk" --region us-east-1

# Get recent log events
aws logs filter-log-events --log-group-name "/aws/elasticbeanstalk/YOUR_ENV_NAME/var/log/eb-engine.log" --start-time $(date -d "1 hour ago" +%s)000 --region us-east-1
```

---

## 🔧 **Common Troubleshooting Commands**

### **Once Connected to EC2 Instance:**

#### **Check Flask Application:**
```bash
# Check if Python processes are running
sudo ps aux | grep python
sudo ps aux | grep gunicorn

# Check application directory
cd /var/app/current
ls -la

# Check if requirements are installed
pip list

# Test application manually
python application.py
```

#### **Check Database Connectivity:**
```bash
# Test MySQL connection
mysql -h homepro-mysql-db.c0zi8ey8usr4.us-east-1.rds.amazonaws.com -u homeproadmin -p homeprodb

# Check environment variables
env | grep DB_
env | grep FLASK_
```

#### **Check Web Server Configuration:**
```bash
# Check Apache/httpd configuration
sudo cat /etc/httpd/conf/httpd.conf
sudo cat /etc/httpd/conf.d/wsgi.conf

# Check if mod_wsgi is loaded
sudo httpd -M | grep wsgi

# Restart web server if needed
sudo systemctl restart httpd
```

#### **Check Network Connectivity:**
```bash
# Test outbound connectivity
curl -I https://www.google.com
nslookup homepro-mysql-db.c0zi8ey8usr4.us-east-1.rds.amazonaws.com

# Check local services
curl -I http://localhost
curl -I http://localhost:80
```

---

## 📊 **Health Check Diagnostics**

### **Application Health Indicators:**

#### **✅ Healthy Application:**
```bash
# These should return success:
curl -I http://localhost/          # Should return 200 OK
sudo systemctl status httpd       # Should be "active (running)"
ps aux | grep python              # Should show Python processes
```

#### **❌ Common Issues:**

1. **Database Connection Issues:**
```bash
# Check database connectivity
telnet homepro-mysql-db.c0zi8ey8usr4.us-east-1.rds.amazonaws.com 3306
```

2. **Missing Dependencies:**
```bash
# Check if all packages installed
pip list | grep -i flask
pip list | grep -i mysql
```

3. **Permission Issues:**
```bash
# Check file permissions
ls -la /var/app/current/
sudo chown -R webapp:webapp /var/app/current/
```

4. **Port Conflicts:**
```bash
# Check what's using port 80
sudo lsof -i :80
sudo netstat -tlnp | grep :80
```

---

## 🚨 **Emergency Troubleshooting**

### **If Application Won't Start:**

1. **Check EB Engine Logs:**
```bash
sudo tail -f /var/log/eb-engine.log
```

2. **Manual Application Start:**
```bash
cd /var/app/current
sudo -u webapp python application.py
```

3. **Check WSGI Configuration:**
```bash
sudo cat /var/app/current/application.py
sudo cat /etc/httpd/conf.d/wsgi.conf
```

### **If Database Connection Fails:**

1. **Verify Environment Variables:**
```bash
env | grep DB_
```

2. **Test Direct Connection:**
```bash
mysql -h $DB_HOST -u $DB_USERNAME -p$DB_PASSWORD $DB_NAME
```

3. **Check Security Groups:**
- Ensure EC2 security group allows outbound to RDS port 3306
- Ensure RDS security group allows inbound from EC2 security group

---

## 📋 **Quick Diagnostic Checklist**

### **Run These Commands in Order:**

```bash
# 1. Check overall system health
sudo systemctl status httpd
sudo systemctl status eb-engine

# 2. Check application processes
ps aux | grep python
ps aux | grep httpd

# 3. Check network connectivity
curl -I http://localhost
telnet $DB_HOST 3306

# 4. Check logs for errors
sudo tail -20 /var/log/eb-engine.log
sudo tail -20 /var/log/httpd/error_log

# 5. Check environment variables
env | grep -E "(DB_|FLASK_|SECRET_)"
```

---

## 🔐 **Session Manager Prerequisites**

### **Ensure SSM Agent is Running:**
```bash
# Check SSM agent status
sudo systemctl status amazon-ssm-agent

# Start if not running
sudo systemctl start amazon-ssm-agent
sudo systemctl enable amazon-ssm-agent
```

### **Required IAM Permissions:**
Your EC2 instances need the `AmazonSSMManagedInstanceCore` policy attached to their IAM role.

---

## 📞 **Quick Commands Reference**

```powershell
# Find EB environment name
eb list

# Get instance IDs
aws elasticbeanstalk describe-environment-resources --environment-name YOUR_ENV_NAME --region us-east-1

# Connect to instance
aws ssm start-session --target i-INSTANCE-ID --region us-east-1

# View logs without connecting
eb logs --all

# Check environment health
eb health --refresh
```

---

## 🎯 **Next Steps Based on Status**

### **If "Info" Status is Normal:**
- Application is likely starting up
- Check logs for any errors during initialization
- Verify database connectivity

### **If Issues Found:**
1. **Fix configuration** in `.ebextensions/`
2. **Redeploy** with corrected package
3. **Monitor** deployment logs

### **If All Looks Good:**
- Test application via load balancer URL
- Verify all features work correctly
- Monitor performance metrics

**Remember**: Since you're using private subnets, all troubleshooting must be done via Session Manager or CloudWatch Logs! 🔒