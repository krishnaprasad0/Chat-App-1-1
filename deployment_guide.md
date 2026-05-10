# 🚀 AWS EC2 Deployment Guide - Amazon Linux 2023 (AL2023)

This guide covers the full setup and deployment of the FastAPI backend on an **Amazon Linux 2023** EC2 instance.

## 1. Recommended EC2 Specifications

| Component | Minimum (Testing) | Recommended (Production) |
| :--- | :--- | :--- |
| **Instance Type** | `t3.small` | `t3.medium` |
| **vCPU** | 2 | 2 |
| **Memory (RAM)** | 2 GB | 4 GB |
| **Storage** | 20 GB (gp3) | 50 GB (gp3) |
| **OS** | Amazon Linux 2023 | Amazon Linux 2023 |

---

## 2. Security Group Configuration (Inbound Rules)

Ensure your EC2 Security Group allows:
- **22 (SSH)**
- **80 (HTTP)**
- **443 (HTTPS)**
- **8000 (FastAPI)**

---

## 3. Server Preparation (AL2023 Commands)

Connect to your instance and run:

```bash
# Update system
sudo dnf update -y

# Install Python, Git, and Development Tools
sudo dnf install -y python3.11 python3-pip git-all

# Install Redis
sudo dnf install -y redis6
sudo systemctl start redis6
sudo systemctl enable redis6

# Install Nginx
sudo dnf install -y nginx
sudo systemctl start nginx
sudo systemctl enable nginx

# Install PostgreSQL (Client and Server)
sudo dnf install -y postgresql15-server postgresql15
sudo postgresql-setup --initdb
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

---

## 4. Application Setup

1. **Clone the Repository:**
   ```bash
   git clone <your-repo-url> chat_app
   cd chat_app/chat_app_backend
   ```

2. **Create Virtual Environment:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   pip install gunicorn uvicorn
   ```

3. **Configure Environment Variables:**
   ```bash
   nano .env
   ```
   *Paste your production config (DATABASE_URL, REDIS_URL, AWS keys, etc.)*

---

## 5. Process Management (systemd)

Create a service file:
```bash
sudo nano /etc/systemd/system/chat_app.service
```

Paste the following:
```ini
[Unit]
Description=Gunicorn instance to serve Chat App
After=network.target redis6.service postgresql.service

[Service]
User=ec2-user
Group=nginx
WorkingDirectory=/home/ec2-user/chat_app/chat_app_backend
Environment="PATH=/home/ec2-user/chat_app/chat_app_backend/.venv/bin"
ExecStart=/home/ec2-user/chat_app/chat_app_backend/.venv/bin/gunicorn \
    -w 4 \
    -k uvicorn.workers.UvicornWorker \
    app.main:app \
    --bind 0.0.0.0:8000

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl start chat_app
sudo systemctl enable chat_app
```

---

## 6. Nginx Reverse Proxy

Create an Nginx configuration:
```bash
sudo nano /etc/nginx/conf.d/chat_app.conf
```

Paste:
```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Restart Nginx:
```bash
sudo nginx -t
sudo systemctl restart nginx
```

---

## 7. SSL with Certbot

```bash
sudo dnf install -y python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
```
