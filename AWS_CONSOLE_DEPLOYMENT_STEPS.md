# 🚀 AWS Console Deployment - Step-by-Step Guide

## 📋 **Prerequisites Checklist**
- ✅ AWS Account with Free Tier access
- ✅ Infrastructure deployed (CloudFormation stack: `homepro-infrastructure`)
- ✅ Deployment package ready: `homepro-deployment.zip`
- ✅ Database credentials and resource names from deployment

## 🎯 **Step 1: Access AWS Elastic Beanstalk Console**

1. **Open your web browser** and go to:
   ```
   https://console.aws.amazon.com/elasticbeanstalk/
   ```

2. **Sign in to AWS Console** with your credentials

3. **Verify Region**: Ensure you're in **US East (N. Virginia) us-east-1** region
   - Look at the top-right corner of the console
   - If not in us-east-1, click the region dropdown and select it

## 🏗️ **Step 2: Create New Application**

1. **Click "Create Application"** (big orange button)

2. **Fill Application Information**:
   - **Application name**: `HomePro`
   - **Description**: `Home improvement project management platform`
   - **Platform**: Select **Python**
   - **Platform branch**: Choose **Python 3.9 running on 64bit Amazon Linux 2**
   - **Platform version**: Leave as **Recommended**

3. **Application Code Section**:
   - Select **"Upload your code"**
   - **Version label**: `v1.0` (or leave default)
   - **Source code origin**: Click **"Choose file"**
   - Navigate to your project folder and select `homepro-deployment.zip`

4. **Click "Create Application"** (this may take 5-10 minutes)

## ⚙️ **Step 3: Configure Environment Variables**

1. **Wait for Initial Deployment** to complete (status will show "Ok" in green)

2. **Go to Configuration**:
   - In the left sidebar, click **"Configuration"**
   - Or click the **"Configuration"** tab in the main area

3. **Edit Software Configuration**:
   - Find the **"Software"** section
   - Click **"Edit"** button

4. **Add Environment Properties**:
   Scroll down to **"Environment properties"** section and add these **one by one**:

   ```
   Name: SECRET_KEY
   Value: your-super-secret-production-key-change-this-123456789

   Name: AWS_REGION
   Value: us-east-1

   Name: AWS_S3_BUCKET
   Value: homepro-infrastructure-defaultuploadsbucket-wotbg57omt0l

   Name: DB_HOST
   Value: homepro-mysql-db.c0zi8ey8usr4.us-east-1.rds.amazonaws.com

   Name: DB_USERNAME
   Value: homeproadmin

   Name: DB_PASSWORD
   Value: SecurePassword123!

   Name: DB_NAME
   Value: homeprodb

   Name: FLASK_ENV
   Value: production

   Name: DB_PORT
   Value: 3306
   ```

5. **Click "Apply"** at the bottom (this will restart your environment)

## 🔧 **Step 4: Configure Instance Settings (Optional but Recommended)**

1. **Edit Instances Configuration**:
   - In Configuration page, find **"Instances"** section
   - Click **"Edit"**

2. **Instance Settings**:
   - **Instance type**: Ensure it's **t2.micro** (Free Tier eligible)
   - **Security groups**: Leave as default
   - **Instance profile**: Should auto-select the IAM role we created

3. **Click "Apply"**

## 🌐 **Step 5: Configure Load Balancer (Optional)**

1. **Edit Load Balancer Configuration**:
   - Find **"Load balancer"** section
   - Click **"Edit"**

2. **Load Balancer Settings**:
   - **Load balancer type**: **Application Load Balancer** (recommended)
   - **Listeners**: Keep default (Port 80, HTTP)
   - **Health check path**: Change to `/` (root path)

3. **Click "Apply"**

## 🔍 **Step 6: Monitor Deployment**

1. **Check Environment Health**:
   - Go back to main dashboard
   - Wait for **Health** status to show **"Ok"** (green)
   - This may take 5-15 minutes

2. **Monitor Events**:
   - Click **"Events"** in the left sidebar
   - Watch for any error messages
   - Look for "Successfully launched environment" message

## 🎉 **Step 7: Test Your Application**

1. **Get Application URL**:
   - On the main dashboard, you'll see your **Environment URL**
   - It will look like: `http://homepro-env.eba-xxxxxxxx.us-east-1.elasticbeanstalk.com`

2. **Click the URL** to open your application

3. **Test Key Features**:
   - ✅ Homepage loads
   - ✅ Registration works
   - ✅ Login functionality
   - ✅ File upload (uses S3)
   - ✅ Database connectivity

## 🛠️ **Step 8: Troubleshooting Common Issues**

### **If Application Shows "502 Bad Gateway"**:
1. Check **Logs** → **Request Logs** → **Last 100 Lines**
2. Look for Python/Flask errors
3. Verify environment variables are set correctly

### **If Database Connection Fails**:
1. Verify DB_HOST, DB_USERNAME, DB_PASSWORD in environment variables
2. Check RDS security group allows connections from Elastic Beanstalk

### **If File Upload Fails**:
1. Verify AWS_S3_BUCKET environment variable
2. Check IAM role has S3 permissions

## 📊 **Step 9: Monitor Costs and Usage**

1. **Go to AWS Billing Dashboard**:
   ```
   https://console.aws.amazon.com/billing/
   ```

2. **Check Free Tier Usage**:
   - Monitor EC2 hours (750/month limit)
   - Monitor RDS hours (750/month limit)
   - Monitor S3 storage (5GB limit)

## 🔄 **Step 10: Future Updates**

### **To Deploy Code Updates**:
1. Create new ZIP file with updated code
2. Go to **Application Versions**
3. Click **"Upload and Deploy"**
4. Select new ZIP file
5. Deploy to environment

### **To Update Environment Variables**:
1. Go to **Configuration** → **Software** → **Edit**
2. Modify environment properties
3. Click **Apply**

## 🎯 **Success Indicators**

Your deployment is successful when you see:
- ✅ Environment Health: **Ok** (Green)
- ✅ Application URL accessible
- ✅ Homepage loads without errors
- ✅ Database operations work
- ✅ File uploads work

## 📞 **Need Help?**

If you encounter issues:
1. Check **Events** tab for error messages
2. Download **Logs** for detailed error information
3. Verify all environment variables are correct
4. Ensure your AWS account has necessary permissions

**Your application should be live and accessible via the Elastic Beanstalk URL!** 🚀