# HomePro EC2 Deployment Guide 2025

## 📦 Latest Deployment Package
**File:** `homepro-ec2-audio-fix-20250806-222342.zip` (2.97 MB)  
**Created:** January 6, 2025  
**Includes:** Contact page, updated UI, and all latest features

## 🚀 Complete EC2 Deployment Process

### Prerequisites
- AWS Account with EC2 access
- Basic knowledge of SSH and Linux commands
- Domain name (optional, for SSL)

---

## Step 1: Launch EC2 Instance

### 1.1 Create EC2 Instance
1. **Go to AWS Console** → EC2 → Launch Instance
2. **Name:** `HomePro-Production`
3. **AMI:** Ubuntu Server 22.04 LTS (Free tier eligible)
4. **Instance Type:** t2.micro (Free tier) or t3.small (recommended for production)
5. **Key Pair:** Create new or select existing
6. **Network Settings:**
   - Create new security group or use existing
   - Allow SSH (22) from your IP
   - Allow HTTP (80) from anywhere (0.0.0.0/0)
   - Allow HTTPS (443) from anywhere (0.0.0.0/0)
   - Allow Custom TCP (8000) from anywhere (for testing)

### 1.2 Security Group Rules
```
Type        Protocol    Port Range    Source
SSH         TCP         22           Your IP/32
HTTP        TCP         80           0.0.0.0/0
HTTPS       TCP         443          0.0.0.0/0
Custom TCP  TCP         8000         0.0.0.0/0
```

---

## Step 2: Connect to Your Instance

```bash
# Replace with your key file and instance public IP
ssh -i "your-key.pem" ubuntu@your-ec2-public-ip

# Make key file secure (if needed)
chmod 400 your-key.pem
```

---

## Step 3: System Setup

### 3.1 Update System
```bash
sudo apt update && sudo apt upgrade -y
```

### 3.2 Install Dependencies
```bash
# Install Python and essential tools
sudo apt install python3 python3-pip python3-venv unzip nginx mysql-client -y

# Install Node.js (for any future frontend builds)
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs
```

---

## Step 4: Upload and Setup Application

### 4.1 Upload Deployment Package
```bash
# Option 1: Upload from your local machine
scp -i "your-key.pem" homepro-ec2-audio-fix-20250806-222342.zip ubuntu@your-ec2-ip:~/

# Option 2: Download from cloud storage (if you uploaded it there)
# wget https://your-storage-url/homepro-ec2-audio-fix-20250806-222342.zip
```

### 4.2 Extract and Setup
```bash
# Extract the package
unzip homepro-ec2-audio-fix-20250806-222342.zip
cd homepro-ec2-audio-fix-20250806-222342/

# Create Python virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
pip install gunicorn  # For production server
```

---

## Step 5: Database Configuration

### Option A: SQLite (Simpler, for testing)
```bash
# Copy environment template
cp .env.template .env

# Edit environment file
nano .env
```

**Configure .env for SQLite:**
```bash
# Database Configuration (SQLite)
DATABASE_URL=sqlite:///homepro.db

# AWS Configuration (optional)
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_DEFAULT_REGION=us-east-1
AWS_S3_BUCKET=

# Flask Configuration
SECRET_KEY=your-super-secret-key-change-this-to-something-random
FLASK_ENV=production
```

### Option B: RDS MySQL (Production recommended)
1. **Create RDS Instance** in AWS Console:
   - Engine: MySQL 8.0
   - Instance: db.t3.micro (Free tier)
   - Storage: 20 GB
   - **Important:** Set security group to allow access from EC2

2. **Configure .env for RDS:**
```bash
# Database Configuration (RDS MySQL)
DB_HOST=your-rds-endpoint.region.rds.amazonaws.com
DB_USER=admin
DB_PASSWORD=your-secure-password
DB_NAME=homepro_db

# AWS Configuration
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_DEFAULT_REGION=us-east-1
AWS_S3_BUCKET=your-bucket-name

# Flask Configuration
SECRET_KEY=your-super-secret-key-change-this
FLASK_ENV=production
```

### 5.1 Initialize Database
```bash
# Run database migration
python migrate_database.py
```

---

## Step 6: Test Application

```bash
# Test the application
python app.py
```

**Open browser:** `http://your-ec2-public-ip:8000`

If everything works, press `Ctrl+C` to stop and continue to production setup.

---

## Step 7: Production Setup with Nginx + Gunicorn

### 7.1 Test Gunicorn
```bash
# Test Gunicorn (should work without errors)
gunicorn -w 4 -b 0.0.0.0:8000 application:application
```

### 7.2 Configure Nginx
```bash
# Create Nginx configuration
sudo nano /etc/nginx/sites-available/homepro
```

**Add this configuration:**
```nginx
server {
    listen 80;
    server_name your-domain.com your-ec2-public-ip;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;

    # Main application
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
    }

    # Static files
    location /static {
        alias /home/ubuntu/homepro-ec2-audio-fix-20250806-222342/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Upload files
    location /uploads {
        alias /home/ubuntu/homepro-ec2-audio-fix-20250806-222342/uploads;
        expires 7d;
    }

    # Increase upload size limit
    client_max_body_size 50M;
}
```

### 7.3 Enable Nginx Site
```bash
# Enable the site
sudo ln -s /etc/nginx/sites-available/homepro /etc/nginx/sites-enabled/

# Remove default site
sudo rm -f /etc/nginx/sites-enabled/default

# Test Nginx configuration
sudo nginx -t

# Start and enable Nginx
sudo systemctl restart nginx
sudo systemctl enable nginx
```

---

## Step 8: Create System Service

### 8.1 Create Systemd Service
```bash
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
WorkingDirectory=/home/ubuntu/homepro-ec2-audio-fix-20250806-222342
Environment=PATH=/home/ubuntu/homepro-ec2-audio-fix-20250806-222342/venv/bin
ExecStart=/home/ubuntu/homepro-ec2-audio-fix-20250806-222342/venv/bin/gunicorn -w 4 -b 127.0.0.1:8000 application:application
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

### 8.2 Start the Service
```bash
# Reload systemd and start service
sudo systemctl daemon-reload
sudo systemctl enable homepro
sudo systemctl start homepro

# Check status
sudo systemctl status homepro
```

---

## Step 9: SSL Setup (Recommended)

### 9.1 Install Certbot
```bash
sudo apt install certbot python3-certbot-nginx -y
```

### 9.2 Get SSL Certificate
```bash
# Replace with your actual domain
sudo certbot --nginx -d your-domain.com

# Test auto-renewal
sudo certbot renew --dry-run
```

---

## Step 10: Final Configuration

### 10.1 Set Up Firewall (Optional)
```bash
# Enable UFW firewall
sudo ufw enable
sudo ufw allow ssh
sudo ufw allow 'Nginx Full'
sudo ufw status
```

### 10.2 Create Admin User
```bash
# Activate virtual environment
source venv/bin/activate

# Run admin setup script
python setup_admin.py
```

---

## 🔧 Post-Deployment Tasks

### Monitoring and Logs
```bash
# View application logs
sudo journalctl -u homepro -f

# View Nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log

# Check service status
sudo systemctl status homepro nginx
```

### Backup Setup
```bash
# Create backup script
nano ~/backup.sh
```

**Backup script content:**
```bash
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/home/ubuntu/backups"
APP_DIR="/home/ubuntu/homepro-ec2-audio-fix-20250806-222342"

mkdir -p $BACKUP_DIR

# Backup database (if using SQLite)
cp $APP_DIR/homepro.db $BACKUP_DIR/homepro_$DATE.db

# Backup uploads
tar -czf $BACKUP_DIR/uploads_$DATE.tar.gz $APP_DIR/uploads/

# Keep only last 7 days of backups
find $BACKUP_DIR -name "*.db" -mtime +7 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete
```

```bash
# Make executable and add to crontab
chmod +x ~/backup.sh
crontab -e
# Add: 0 2 * * * /home/ubuntu/backup.sh
```

---

## 🎉 Deployment Complete!

Your HomePro application is now live at:
- **HTTP:** `http://your-ec2-public-ip`
- **HTTPS:** `https://your-domain.com` (if SSL configured)

### Features Available:
- ✅ User registration and authentication
- ✅ Project submission with audio transcription
- ✅ Contractor bidding system
- ✅ Real-time messaging
- ✅ Contact page with form submissions
- ✅ Admin dashboard
- ✅ File uploads and management

---

## 🔍 Troubleshooting

### Common Issues:

**1. Application won't start:**
```bash
# Check logs
sudo journalctl -u homepro -n 50

# Check Python environment
source venv/bin/activate
python -c "import flask; print('Flask OK')"
```

**2. Database connection issues:**
```bash
# Test database connection
python -c "from app import init_database; init_database()"
```

**3. Nginx issues:**
```bash
# Test Nginx config
sudo nginx -t

# Restart services
sudo systemctl restart nginx homepro
```

**4. SSL certificate issues:**
```bash
# Renew certificate
sudo certbot renew
```

### Performance Optimization:
- Use t3.small or larger for production
- Set up CloudWatch monitoring
- Configure log rotation
- Use RDS for database
- Set up S3 for file storage

---

## 📋 Maintenance Commands

```bash
# Restart application
sudo systemctl restart homepro

# Update application (after uploading new package)
sudo systemctl stop homepro
# Extract new package, update files
sudo systemctl start homepro

# View real-time logs
sudo journalctl -u homepro -f

# Check disk space
df -h

# Check memory usage
free -h
```

---

**Generated:** January 6, 2025  
**Package:** homepro-ec2-audio-fix-20250806-222342.zip  
**Version:** 2025.1.0