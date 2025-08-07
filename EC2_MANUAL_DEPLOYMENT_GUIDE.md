# HomePro EC2 Manual Deployment Guide

## 📦 Deployment Package
**File:** `homepro-ec2-audio-fix-20250805-231858.zip` (2.96 MB)
**Created:** August 5, 2025
**Includes:** Latest UI improvements and bug fixes

## 🚀 Step-by-Step EC2 Deployment

### Prerequisites
- AWS EC2 instance (t2.micro or larger)
- Ubuntu 20.04+ or Amazon Linux 2
- SSH access to your EC2 instance
- Security group allowing HTTP (port 80) and custom port (8000)

### Step 1: Launch EC2 Instance
1. **Go to AWS Console** → EC2 → Launch Instance
2. **Choose AMI:** Ubuntu Server 20.04 LTS (Free tier eligible)
3. **Instance Type:** t2.micro (Free tier eligible)
4. **Key Pair:** Create or select existing key pair
5. **Security Group:** Create new with these rules:
   - SSH (22) - Your IP
   - HTTP (80) - Anywhere (0.0.0.0/0)
   - Custom TCP (8000) - Anywhere (0.0.0.0/0)
6. **Storage:** 8 GB gp2 (Free tier)
7. **Launch Instance**

### Step 2: Connect to EC2 Instance
```bash
# Replace with your key file and instance IP
ssh -i "your-key.pem" ubuntu@your-ec2-public-ip
```

### Step 3: Update System and Install Dependencies
```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install Python and pip
sudo apt install python3 python3-pip python3-venv -y

# Install additional dependencies
sudo apt install unzip nginx -y

# Install MySQL client (if using RDS)
sudo apt install mysql-client -y
```

### Step 4: Upload and Extract Deployment Package
```bash
# Option 1: Upload via SCP (from your local machine)
scp -i "your-key.pem" homepro-ec2-audio-fix-20250805-231858.zip ubuntu@your-ec2-ip:~/

# Option 2: Download from a cloud storage (if uploaded there)
# wget https://your-storage-url/homepro-ec2-audio-fix-20250805-231858.zip

# Extract the package
unzip homepro-ec2-audio-fix-20250805-231858.zip
cd homepro-ec2-audio-fix-20250805-231858/
```

### Step 5: Set Up Python Environment
```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

### Step 6: Configure Environment Variables
```bash
# Copy environment template
cp .env.template .env

# Edit environment file
nano .env
```

**Configure these variables in .env:**
```bash
# Database Configuration (if using RDS)
DB_HOST=your-rds-endpoint.region.rds.amazonaws.com
DB_USER=your-db-username
DB_PASSWORD=your-db-password
DB_NAME=homepro_db

# For SQLite (simpler option)
# DATABASE_URL=sqlite:///homepro.db

# AWS Configuration (leave empty if using EC2 IAM role)
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_DEFAULT_REGION=us-east-1
AWS_S3_BUCKET=your-s3-bucket-name

# Flask Configuration
SECRET_KEY=your-super-secret-key-here-change-this
FLASK_ENV=production
```

### Step 7: Initialize Database
```bash
# Run database migration
python migrate_database.py
```

### Step 8: Test Application
```bash
# Start application in test mode
python app.py
```

**Test in browser:** `http://your-ec2-public-ip:8000`

### Step 9: Set Up Production Server (Gunicorn + Nginx)

#### Install and Configure Gunicorn
```bash
# Install Gunicorn
pip install gunicorn

# Test Gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 application:application
```

#### Configure Nginx
```bash
# Create Nginx configuration
sudo nano /etc/nginx/sites-available/homepro
```

**Add this configuration:**
```nginx
server {
    listen 80;
    server_name your-domain.com your-ec2-public-ip;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static {
        alias /home/ubuntu/homepro-ec2-audio-fix-20250805-231858/static;
        expires 30d;
    }

    location /uploads {
        alias /home/ubuntu/homepro-ec2-audio-fix-20250805-231858/uploads;
    }
}
```

```bash
# Enable the site
sudo ln -s /etc/nginx/sites-available/homepro /etc/nginx/sites-enabled/

# Remove default site
sudo rm /etc/nginx/sites-enabled/default

# Test Nginx configuration
sudo nginx -t

# Restart Nginx
sudo systemctl restart nginx
sudo systemctl enable nginx
```

### Step 10: Create Systemd Service (Auto-start)
```bash
# Create service file
sudo nano /etc/systemd/system/homepro.service
```

**Add this configuration:**
```ini
[Unit]
Description=HomePro Flask Application
After=network.target

[Service]
User=ubuntu
Group=ubuntu
WorkingDirectory=/home/ubuntu/homepro-ec2-audio-fix-20250805-231858
Environment=PATH=/home/ubuntu/homepro-ec2-audio-fix-20250805-231858/venv/bin
ExecStart=/home/ubuntu/homepro-ec2-audio-fix-20250805-231858/venv/bin/gunicorn -w 4 -b 127.0.0.1:8000 application:application
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start the service
sudo systemctl daemon-reload
sudo systemctl enable homepro
sudo systemctl start homepro

# Check status
sudo systemctl status homepro
```

## 🔧 Post-Deployment Configuration

### Set Up SSL (Optional but Recommended)
```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx -y

# Get SSL certificate (replace with your domain)
sudo certbot --nginx -d your-domain.com
```

### Set Up Database (RDS MySQL)
1. **Create RDS Instance** in AWS Console
2. **Configure Security Group** to allow EC2 access
3. **Update .env** with RDS credentials
4. **Run migration:** `python migrate_database.py`

### Configure S3 for File Uploads
1. **Create S3 Bucket** in AWS Console
2. **Set up IAM role** for EC2 with S3 access
3. **Update .env** with bucket name

## 🔍 Troubleshooting

### Check Application Logs
```bash
# View application logs
sudo journalctl -u homepro -f

# View Nginx logs
sudo tail -f /var/log/nginx/error.log
sudo tail -f /var/log/nginx/access.log
```

### Common Issues
1. **Port 8000 not accessible:** Check security group rules
2. **Database connection failed:** Verify RDS security group and credentials
3. **Static files not loading:** Check Nginx static file configuration
4. **Application won't start:** Check Python dependencies and .env file

### Restart Services
```bash
# Restart application
sudo systemctl restart homepro

# Restart Nginx
sudo systemctl restart nginx

# Check all services
sudo systemctl status homepro nginx
```

## 🎉 Deployment Complete!

Your HomePro application should now be accessible at:
- **HTTP:** `http://your-ec2-public-ip`
- **HTTPS:** `https://your-domain.com` (if SSL configured)

## 📋 Next Steps
1. Set up monitoring and alerts
2. Configure automated backups
3. Set up CI/CD pipeline
4. Monitor application performance
5. Scale as needed

---
**Generated:** August 5, 2025
**Package:** homepro-ec2-audio-fix-20250805-231858.zip