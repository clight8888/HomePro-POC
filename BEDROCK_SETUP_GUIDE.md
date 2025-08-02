# 🤖 AWS Bedrock Setup Guide

This guide will help you set up AWS Bedrock for AI-powered project analysis in your HomePro application.

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [AWS Bedrock Console Setup](#aws-bedrock-console-setup)
3. [Model Access Configuration](#model-access-configuration)
4. [Environment Configuration](#environment-configuration)
5. [Testing Your Setup](#testing-your-setup)
6. [Troubleshooting](#troubleshooting)
7. [Cost Optimization](#cost-optimization)

## 🔧 Prerequisites

- AWS Account with appropriate permissions
- AWS CLI configured with credentials
- Python environment with boto3 installed
- HomePro application running

## 🚀 AWS Bedrock Console Setup

### Step 1: Access AWS Bedrock Console

1. **Login to AWS Console**
   - Go to [AWS Console](https://console.aws.amazon.com/)
   - Sign in with your AWS account

2. **Navigate to Bedrock**
   - Search for "Bedrock" in the AWS services search bar
   - Click on "Amazon Bedrock"
   - Or go directly to: https://console.aws.amazon.com/bedrock/

### Step 2: Check Region Availability

Bedrock is available in specific regions. Recommended regions:
- **US East (N. Virginia)** - `us-east-1`
- **US West (Oregon)** - `us-west-2`
- **Europe (Frankfurt)** - `eu-central-1`

Make sure you're in a supported region (check top-right corner of console).

## 🎯 Model Access Configuration

### Step 3: Request Model Access

1. **Go to Model Access**
   - In the Bedrock console, click "Model access" in the left sidebar
   - You'll see a list of available foundation models

2. **Request Access to Required Models**
   
   The HomePro application uses these models (in order of preference):
   
   #### Primary Models (Highest Performance):
   - ✅ **Anthropic Claude 3.5 Sonnet v2** (`anthropic.claude-3-5-sonnet-20241022-v2:0`) - **NEWEST & BEST**
   - ✅ **Anthropic Claude 3.5 Sonnet** (`anthropic.claude-3-5-sonnet-20240620-v1:0`) - **RECOMMENDED**
   
   #### Secondary Models (High Performance):
   - ✅ **Anthropic Claude 3 Sonnet** (`anthropic.claude-3-sonnet-20240229-v1:0`)
   - ✅ **Anthropic Claude 3 Haiku** (`anthropic.claude-3-haiku-20240307-v1:0`) - **FAST & COST-EFFECTIVE**
   
   #### Fallback Models:
   - ✅ **Anthropic Claude v2.1** (`anthropic.claude-v2:1`)
   - ✅ **Anthropic Claude v2** (`anthropic.claude-v2`)
   - ✅ **Amazon Titan Text Express** (`amazon.titan-text-express-v1`) - **BACKUP OPTION**

3. **Enable Model Access**
   - Click "Manage model access" button
   - Select the models you want to enable (prioritize Claude 3.5 Sonnet models)
   - Click "Request model access"
   - **Note**: Some models may require approval and can take up to 24 hours
   
   > 🚀 **Future Ready**: The application is configured to automatically support Claude 4 when it becomes available on Bedrock. Simply add the new model ID to the configuration when released.

### Step 4: Verify Model Access

After requesting access:
1. Wait for approval (usually instant for Claude models)
2. Refresh the "Model access" page
3. Verify that your requested models show "Access granted" status

## ⚙️ Environment Configuration

### Step 5: Configure AWS Credentials

Ensure your AWS credentials are properly configured:

#### Option A: AWS CLI Configuration
```bash
aws configure
```
Enter:
- AWS Access Key ID
- AWS Secret Access Key
- Default region (e.g., `us-east-1`)
- Default output format: `json`

#### Option B: Environment Variables
```bash
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_DEFAULT_REGION=us-east-1
```

#### Option C: IAM Role (for EC2/ECS deployment)
Attach an IAM role with Bedrock permissions to your instance.

### Step 6: Configure Application Environment

Update your `.env` file:

```env
# AWS Configuration
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_key_here

# Bedrock Configuration
BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0
BEDROCK_REGION=us-east-1

# Optional: Bedrock Settings
BEDROCK_MAX_TOKENS=4000
BEDROCK_TEMPERATURE=0.1
```

### Step 7: Required IAM Permissions

Your AWS user/role needs these permissions:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeModel",
                "bedrock:ListFoundationModels",
                "bedrock:GetFoundationModel"
            ],
            "Resource": "*"
        }
    ]
}
```

## 🧪 Testing Your Setup

### Step 8: Test Bedrock Connection

1. **Run the Test Script**
   ```bash
   python test_audio_processor.py
   ```

2. **Expected Output**
   ```
   ✓ AWS credentials configured
   ✓ Bedrock client: True
   
   Testing text analysis with Bedrock...
   ✅ Bedrock extraction successful - Project: Kitchen Renovation
   ```

3. **Test via Web Interface**
   - Go to your HomePro application
   - Navigate to "Submit Project"
   - Upload an audio file or enter text
   - Verify AI analysis works

### Step 9: Check Application Logs

Monitor your application logs for Bedrock-related messages:

```bash
# Look for these log messages:
🚀 AWS Bedrock Audio Processor initialized successfully
🔍 Available Bedrock models (X):
🤖 Using AWS Bedrock for project detail extraction
✅ Bedrock extraction successful
```

## 🔧 Troubleshooting

### Common Issues and Solutions

#### Issue 1: "Model not accessible" Error
```
❌ Model anthropic.claude-3-5-sonnet-20241022-v2:0 is not accessible
```

**Solution:**
1. Check model access in Bedrock console
2. Ensure model is approved and "Access granted"
3. Verify you're in the correct AWS region
4. Wait up to 24 hours for approval

#### Issue 2: "Access Denied" Error
```
❌ An error occurred (AccessDeniedException) when calling the InvokeModel operation
```

**Solution:**
1. Check IAM permissions
2. Verify AWS credentials are correct
3. Ensure Bedrock service permissions are attached

#### Issue 3: "Region Not Supported" Error
```
❌ Bedrock is not available in this region
```

**Solution:**
1. Switch to a supported region (us-east-1, us-west-2, eu-central-1)
2. Update AWS_REGION in your environment
3. Request model access in the new region

#### Issue 4: "No Models Available" Error
```
🚫 All Bedrock models are not enabled in your AWS account!
```

**Solution:**
1. Go to Bedrock console → Model access
2. Request access to Claude 3.5 Sonnet models (highest priority)
3. Also enable Claude 3 Haiku for cost-effective fallback
4. Wait for approval (usually instant for Claude models)
5. Restart your application

#### Issue 5: High Latency or Timeouts
```
❌ Request timed out
```

**Solution:**
1. Check your internet connection
2. Verify AWS region is geographically close
3. Consider using Claude Haiku for faster responses
4. Implement retry logic (already included in the app)

### Debug Mode

Enable debug logging by setting:
```env
LOG_LEVEL=DEBUG
```

This will show detailed Bedrock API calls and responses.

## 💰 Cost Optimization

### Understanding Bedrock Pricing

Bedrock charges per token (input + output):

| Model | Input (per 1K tokens) | Output (per 1K tokens) | Performance |
|-------|----------------------|------------------------|-------------|
| **Claude 3.5 Sonnet v2** | $0.003 | $0.015 | **Highest** |
| **Claude 3.5 Sonnet** | $0.003 | $0.015 | **Highest** |
| Claude 3 Sonnet | $0.003 | $0.015 | High |
| Claude 3 Haiku | $0.00025 | $0.00125 | Fast |
| Claude v2.1 | $0.008 | $0.024 | Legacy |
| Amazon Titan Express | $0.0008 | $0.0016 | Backup |

### Cost-Saving Tips

1. **Use Haiku for Simple Tasks**
   - 10x cheaper than Sonnet
   - Good for basic project analysis

2. **Optimize Prompts**
   - Keep prompts concise
   - Request specific output format
   - Avoid unnecessary context

3. **Implement Caching**
   - Cache similar transcript analyses
   - Store results to avoid re-processing

4. **Monitor Usage**
   - Check AWS Billing dashboard
   - Set up billing alerts
   - Track token usage in logs

### Estimated Costs

For typical usage:
- **Small project** (100 words): ~$0.01
- **Medium project** (500 words): ~$0.05
- **Large project** (1000 words): ~$0.10

## 🔮 Future Model Updates

### Preparing for Claude 4

When Claude 4 becomes available on AWS Bedrock, you can easily add it to your configuration:

1. **Check for New Models**
   - Monitor AWS Bedrock announcements
   - Check the Bedrock console for new model releases
   - Look for Claude 4 model IDs (format: `anthropic.claude-4-*`)

2. **Add Claude 4 to Configuration**
   
   Edit `audio_processor.py` and add the new model at the top of the `models_to_try` list:
   
   ```python
   {
       "id": "anthropic.claude-4-opus-YYYYMMDD-v1:0",  # Replace with actual ID
       "name": "Claude 4 Opus",
       "type": "anthropic", 
       "priority": "ultimate"
   },
   ```

3. **Request Model Access**
   - Go to Bedrock console → Model access
   - Request access to the new Claude 4 model
   - Wait for approval

4. **Test and Deploy**
   - Test with `python test_audio_processor.py`
   - Deploy the updated configuration
   - Monitor performance and costs

### Automatic Model Detection

The application is designed to:
- ✅ Try models in priority order
- ✅ Automatically fall back if newer models fail
- ✅ Log which model was successfully used
- ✅ Provide detailed error messages for troubleshooting

## 📊 Monitoring and Maintenance

### Health Checks

The application automatically:
- Tests Bedrock connectivity on startup
- Falls back to simpler analysis if Bedrock fails
- Logs all Bedrock interactions
- Retries failed requests

### Regular Maintenance

1. **Monthly**: Review Bedrock costs in AWS billing
2. **Quarterly**: Check for new model releases
3. **As needed**: Update model access for new features

## 🆘 Getting Help

### Resources

- [AWS Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [Anthropic Claude Documentation](https://docs.anthropic.com/)
- [AWS Support](https://aws.amazon.com/support/)

### Application-Specific Help

If you're still having issues:

1. **Check Application Logs**
   ```bash
   tail -f app.log
   ```

2. **Run Diagnostic Script**
   ```bash
   python test_audio_processor.py
   ```

3. **Verify Environment**
   ```bash
   python -c "import boto3; print(boto3.Session().region_name)"
   ```

### Contact Information

For HomePro-specific Bedrock issues, check:
- Application logs in `/logs/` directory
- Error messages in browser console
- AWS CloudWatch logs (if deployed on AWS)

---

## ✅ Quick Setup Checklist

- [ ] AWS account with Bedrock access
- [ ] Correct AWS region selected
- [ ] Claude model access requested and approved
- [ ] AWS credentials configured
- [ ] Environment variables set
- [ ] IAM permissions configured
- [ ] Test script runs successfully
- [ ] Application shows Bedrock initialization
- [ ] AI analysis works in web interface

**🎉 Congratulations! Your Bedrock setup is complete!**

---

*Last updated: January 2025*
*Version: 1.0*