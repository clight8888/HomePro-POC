# 🔧 VPC Configuration Fix for Elastic Beanstalk

## ❌ **Current Error**
```
AWSEBInstanceLaunchWaitCondition failure
EC2 instances failed to communicate with AWS Elastic Beanstalk
VPC configuration problems
```

## 🎯 **Root Cause**
You have a custom VPC with 2 Availability Zones, but our EB configuration has empty VPC/subnet values, causing communication failures.

## 📋 **Step 1: Find Your VPC and Subnet IDs**

### **Method 1: AWS Console**
1. **Go to VPC Console**: https://console.aws.amazon.com/vpc/
2. **Find Your VPC**:
   - Click **"Your VPCs"**
   - Look for your custom VPC (not the default one)
   - Copy the **VPC ID** (format: `vpc-xxxxxxxxx`)

3. **Find Your Subnets**:
   - Click **"Subnets"**
   - Filter by your VPC ID
   - You should see subnets in 2 different AZs
   - Copy the **Subnet IDs** (format: `subnet-xxxxxxxxx`)

### **Method 2: AWS CLI**
```bash
# Find your VPC
aws ec2 describe-vpcs --query 'Vpcs[?IsDefault==`false`].[VpcId,Tags[?Key==`Name`].Value|[0]]' --output table

# Find subnets in your VPC (replace VPC-ID)
aws ec2 describe-subnets --filters "Name=vpc-id,Values=VPC-ID" --query 'Subnets[*].[SubnetId,AvailabilityZone,MapPublicIpOnLaunch]' --output table
```

## 📝 **Step 2: Update Configuration**

You'll need to provide these values:
- **VPC ID**: `vpc-xxxxxxxxx`
- **Public Subnets** (for load balancer): `subnet-xxxxxxxxx,subnet-yyyyyyyyy`
- **Instance Subnets**: Same as public subnets OR private subnets if you have them

## 🔧 **Step 3: Configuration Template**

Once you have the IDs, update `.ebextensions/01_environment.config`:

```yaml
option_settings:
  # VPC Configuration - REPLACE WITH YOUR ACTUAL IDs
  aws:ec2:vpc:
    VPCId: vpc-YOUR-VPC-ID-HERE
    Subnets: subnet-YOUR-SUBNET-1,subnet-YOUR-SUBNET-2
    ELBSubnets: subnet-YOUR-SUBNET-1,subnet-YOUR-SUBNET-2
    ELBScheme: internet-facing
    AssociatePublicIpAddress: true
```

## 🎯 **Common VPC Configurations**

### **Public Subnets Only** (Recommended for simple setup):
```yaml
aws:ec2:vpc:
  VPCId: vpc-087a68c03b9c50c84
  Subnets: subnet-0fe6b36bcb0ffc462,subnet-032fe3068297ac5b2
  ELBSubnets: subnet-0fe6b36bcb0ffc462,subnet-032fe3068297ac5b2
  ELBScheme: internet-facing
  AssociatePublicIpAddress: true
```

### **Public/Private Setup** (More secure):
```yaml
aws:ec2:vpc:
  VPCId: vpc-087a68c03b9c50c84
  Subnets: subnet-026c6117b178a9c45,subnet-0839e902f656e8bd1  # Private subnets
  ELBSubnets: subnet-0fe6b36bcb0ffc462,subnet-032fe3068297ac5b2  # Public subnets
  ELBScheme: internet-facing
  AssociatePublicIpAddress: false
```

## ⚠️ **Important Notes**

1. **Must have 2 AZs**: Both subnets must be in different Availability Zones <mcreference link="https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/using-features.managing.vpc.html" index="1">1</mcreference>
2. **Public subnets for ELB**: Load balancer needs public subnets to receive internet traffic <mcreference link="https://docs.aws.amazon.com/elasticloadbalancing/latest/classic/elb-manage-subnets.html" index="4">4</mcreference>
3. **Same AZ requirement**: Instances and load balancer must be in same AZs <mcreference link="https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/vpc-rds.html" index="3">3</mcreference>

## 🚀 **Next Steps**

1. **Get your VPC/subnet IDs** using methods above
2. **Update the configuration** with actual IDs
3. **Create new deployment package**
4. **Deploy with corrected VPC settings**

This will fix the `AWSEBInstanceLaunchWaitCondition` error! <mcreference link="https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/using-features.managing.vpc.html" index="1">1</mcreference>