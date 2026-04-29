# 🚀 AWS EC2 Deployment Guide - SecureChat Backend

This guide covers the full setup and deployment of the FastAPI backend on an Amazon EC2 instance.

## 1. Recommended EC2 Specifications

| Component | Minimum (Testing) | Recommended (Production) |
| :--- | :--- | :--- |
| **Instance Type** | `t3.small` | `t3.medium` |
| **vCPU** | 2 | 2 |
| **Memory (RAM)** | 2 GB | 4 GB |
| **Storage** | 20 GB (gp3) | 50 GB (gp3) |
| **OS** | Ubuntu 24.04 LTS | Ubuntu 24.04 LTS |

> [!TIP]
> Use a `t3.medium` for production to handle simultaneous WebSocket connections and media processing without lag.

---

## 2. Security Group Configuration (Inbound Rules)

Ensure your EC2 Security Group allows the following ports:

| Port | Protocol | Source | Purpose |
| :--- | :--- | :--- | :--- |
| 22 | TCP | Your IP | SSH Access |
| 80 | TCP | 0.0.0.0/0 | HTTP (Nginx) |
| 443 | TCP | 0.0.0.0/0 | HTTPS (SSL) |
| 8000 | TCP | 0.0.0.0/0 | FastAPI (If not using Nginx) |

---

## 3. Server Preparation

Connect to your instance:
```bash
ssh -i "your-key.pem" ubuntu@your-ec2-ip
```

Update and install dependencies:
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-pip python3-venv nginx redis-server postgresql postgresql-contrib
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
   Create a `.env` file:
   ```bash
   nano .env
   ```
   *Paste your production config (DATABASE_URL, REDIS_URL, AWS keys, Firebase path, etc.)*

4. **Run Database Migrations:**
   ```bash
   alembic upgrade head
   ```

---

## 5. Process Management (systemd)

To keep the app running in the background and restart automatically:

Create a service file:
```bash
sudo nano /etc/systemd/system/chat_app.service
```

Paste the following:
```ini
[Unit]
Description=Gunicorn instance to serve Chat App
After=network.target

[Service]
User=ubuntu
Group=www-data
WorkingDirectory=/home/ubuntu/chat_app/chat_app_backend
Environment="PATH=/home/ubuntu/chat_app/chat_app_backend/.venv/bin"
ExecStart=/home/ubuntu/chat_app/chat_app_backend/.venv/bin/gunicorn \
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

## 6. Reverse Proxy (Nginx)

Create an Nginx configuration:
```bash
sudo nano /etc/nginx/sites-available/chat_app
```

Paste:
```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

Link and restart Nginx:
```bash
sudo ln -s /etc/nginx/sites-available/chat_app /etc/nginx/sites-enabled
sudo nginx -t
sudo systemctl restart nginx
```

---

## 7. SSL Setup (HTTPS)

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
```

---

## 8. Final Checklist
- [ ] Redis is running (`sudo systemctl status redis`)
- [ ] PostgreSQL is running and user/db created.
- [ ] `FIREBASE_SERVICE_ACCOUNT_PATH` points to the correct location on the server.
- [ ] AWS S3 keys are set in `.env`.
- [ ] Nginx is forwarding WebSocket (`Upgrade` header).
