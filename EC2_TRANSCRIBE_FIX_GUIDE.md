# AWS Transcribe Permission Fix for EC2

## Problem
The EC2 instance is getting an `AccessDeniedException` when trying to use AWS Transcribe:
```
User: arn:aws:sts::332802448311:assumed-role/HomeProEC2Role/i-005619d1b23215847 is not authorized to perform: transcribe:StartTranscriptionJob
```

## Root Cause
The EC2 IAM role `HomeProEC2Role` doesn't have permission to use AWS Transcribe services.

## Solution Options

### Option 1: Add Transcribe Permissions to EC2 Role (Recommended)
1. Go to AWS IAM Console
2. Find the role `HomeProEC2Role`
3. Add the following policy:

```json
{
    "Version": "2012-10-17",
    "Statement": [
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

### Option 2: Use the Latest Code (Immediate Fix)
The latest deployment package includes improved error handling that will:
1. Detect the AWS permission failure
2. Automatically fall back to mock data
3. Still allow the audio upload to work
4. Show a message that audio processing had issues

## Deployment Steps for Immediate Fix

1. **Upload the new package**: `homepro-ec2-audio-fix-20250728-224121.zip`

2. **Stop the current application**:
   ```bash
   # Find the process
   ps aux | grep python
   # Kill the process (replace XXXX with actual PID)
   kill XXXX
   ```

3. **Extract the new package**:
   ```bash
   cd /home/ssm-user/homepro072803/app
   unzip -o homepro-ec2-audio-fix-20250728-224121.zip
   ```

4. **Restart the application**:
   ```bash
   python app.py
   ```

## What the Fix Does

The improved code will:
- ✅ Upload the audio file to S3 successfully
- ❌ Fail at AWS Transcribe (due to permissions)
- ✅ Catch the error and use fallback mock data
- ✅ Continue with project creation
- ✅ Show the review page with editable project details
- ✅ Allow the user to edit and submit the project

## Testing the Fix

1. Upload an audio file
2. You should see a message: "Audio processing encountered an issue. Please review and edit the project details below."
3. The review page should show with default project data
4. You can edit the details and submit successfully

## Long-term Solution

For production use, add the Transcribe permissions to the EC2 role so the audio transcription works properly.

## Verification Commands

Check if the new code is deployed:
```bash
grep -n "DEBUG.*process_ai_submission" app.py
```

You should see debug logging statements in the new version.