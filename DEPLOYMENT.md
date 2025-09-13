# Deployment Guide

This guide provides instructions for deploying the Classifier and Extractor API to a production server using Gunicorn with uvicorn workers.

## Prerequisites

- Ubuntu/Debian server with Python 3.8+
- PostgreSQL database
- Nginx (for reverse proxy)
- Virtual environment with project dependencies installed

## Gunicorn Deployment

Gunicorn with uvicorn workers is the recommended approach for FastAPI applications.

### 1. Install Dependencies

```bash
pip install gunicorn uvicorn[standard]
```

### 2. Configuration

Use the provided `example.gunicorn.conf.py` configuration file. Update the paths and settings as needed:

```python
# example.gunicorn.conf.py
bind = "0.0.0.0:8000"
workers = 4
worker_class = "uvicorn.workers.UvicornWorker"
```

### 3. Create Systemd Service

Create `/etc/systemd/system/classifier-extractor.service`:

```ini
[Unit]
Description=Classifier Extractor API
After=network.target

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/home/ubuntu/docserver
Environment=PATH=/home/ubuntu/docserver/venv/bin
ExecStart=/home/ubuntu/docserver/venv/bin/gunicorn -c example.gunicorn.conf.py api.main:app
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true
Restart=always
RestartSec=10

# Environment variables
Environment=POSTGRES_USER=your_db_user
Environment=POSTGRES_PASSWORD=your_db_password
Environment=POSTGRES_HOST=localhost
Environment=POSTGRES_PORT=5432
Environment=POSTGRES_DB=your_database
Environment=ALLOWED_ORIGINS=https://yourdomain.com
Environment=DEBUG=false
Environment=OPENAI_BASE_URL=https://api.openai.com/v1
Environment=OPENAI_API_KEY=sk-your-openai-key-here
Environment=OPENAI_MODEL_NAME=gpt-4
Environment=OPENAI_TEMPERATURE=0.05
Environment=OPENAI_MAX_TOKENS=2048
Environment=OPENAI_TIMEOUT=360
Environment=DOCUMENT_STORAGE=/var/lib/classifier-extractor/documents
Environment=JWT_SECRET=your-super-secure-jwt-secret-key-here

[Install]
WantedBy=multi-user.target
```

### 4. Start the Service

```bash
sudo systemctl daemon-reload
sudo systemctl enable classifier-extractor
sudo systemctl start classifier-extractor
sudo systemctl status classifier-extractor
```

## Nginx Configuration

Create an Nginx configuration file `/etc/nginx/sites-available/classifier-extractor`:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # Static files
    location /static {
        alias /home/ubuntu/docserver/api/public;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # API endpoints
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }

    # File upload size limit
    client_max_body_size 50M;
}
```

Enable the site:

```bash
sudo ln -s /etc/nginx/sites-available/classifier-extractor /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## SSL Configuration with Let's Encrypt

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
sudo systemctl enable certbot.timer
```

## Database Setup

1. Install PostgreSQL:
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
```

2. Create database and user:
```bash
sudo -u postgres createdb your_database
sudo -u postgres createuser --interactive your_db_user
sudo -u postgres psql -c "ALTER USER your_db_user PASSWORD 'your_password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE your_database TO your_db_user;"
```

## Log Management

### Create Log Directories

```bash
# Create user log directory for application logs
mkdir -p /home/ubuntu/log
chown ubuntu:ubuntu /home/ubuntu/log
```

### Log Rotation

Create `/etc/logrotate.d/classifier-extractor`:

```
/home/ubuntu/log/docserver*.log {
    daily
    missingok
    rotate 52
    compress
    delaycompress
    notifempty
    create 644 ubuntu ubuntu
    postrotate
        systemctl reload classifier-extractor
    endscript
}
```

## Environment Variables

The application uses the following environment variables. Create a `.env` file or set them in your deployment configuration:

### Database Configuration
```bash
export POSTGRES_USER=your_db_user          # PostgreSQL username (default: "user")
export POSTGRES_PASSWORD=your_db_password  # PostgreSQL password (default: "password")
export POSTGRES_HOST=localhost              # PostgreSQL host (default: "localhost")
export POSTGRES_PORT=5432                  # PostgreSQL port (default: 5432)
export POSTGRES_DB=your_database           # PostgreSQL database name (default: "database")
```

### Server Configuration
```bash
export HOST=0.0.0.0                        # Server host (default: "0.0.0.0")
export PORT=8000                           # Server port (default: "8000")
export DEBUG=false                         # Debug mode (default: "false")
export ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com  # CORS origins (default: "*")
```

### LLM Configuration (from api/util/llm_config.py)
```bash
export OPENAI_BASE_URL=http://localhost:11434/v1  # LLM API base URL (default: "http://localhost:11434/v1")
export OPENAI_API_KEY=your_openai_api_key         # LLM API key (default: "openai_api_key")
export OPENAI_MODEL_NAME=gpt-4                    # LLM model name (default: "gemma3n")
export OPENAI_TEMPERATURE=0.05                    # LLM temperature (default: 0.05)
export OPENAI_MAX_TOKENS=2048                     # LLM max tokens (default: 2048)
export OPENAI_TIMEOUT=360                         # LLM request timeout in seconds (default: 360)
```

### File Storage Configuration
```bash
export DOCUMENT_STORAGE=/path/to/document/storage  # Document storage path (optional)
```

### Authentication Configuration
```bash
export JWT_SECRET=your_jwt_secret_key              # JWT secret key for authentication (required)
```

### Complete Environment File Example

Create a `.env` file in your project root:

```bash
# Database
POSTGRES_USER=classifier_user
POSTGRES_PASSWORD=secure_password_here
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=classifier_db

# Server
HOST=0.0.0.0
PORT=8000
DEBUG=false
ALLOWED_ORIGINS=https://yourdomain.com,https://api.yourdomain.com

# LLM Configuration
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_API_KEY=sk-your-openai-key-here
OPENAI_MODEL_NAME=gpt-4
OPENAI_TEMPERATURE=0.05
OPENAI_MAX_TOKENS=2048
OPENAI_TIMEOUT=360

# File Storage
DOCUMENT_STORAGE=/var/lib/classifier-extractor/documents

# Authentication
JWT_SECRET=your-super-secure-jwt-secret-key-here
```

### Environment Variable Loading

The application loads environment variables in several locations:
- `api/main.py` - Database and server configuration
- `api/util/llm_config.py` - LLM/OpenAI configuration  
- `api/util/upload_document.py` - Document storage configuration
- `api/rbac.py` - JWT authentication configuration

## Monitoring and Health Checks

### Health Check Endpoint

The API should include a health check endpoint at `/health` or similar.

### Process Monitoring

```bash
# Check service status
sudo systemctl status classifier-extractor

# View logs
sudo journalctl -u classifier-extractor -f

# Check process
ps aux | grep gunicorn
```

### Resource Monitoring

```bash
# Install htop for process monitoring
sudo apt install htop

# Monitor system resources
htop
```

## Troubleshooting

### Common Issues

1. **Permission Errors**: Ensure correct ownership of files and directories
2. **Port Conflicts**: Check if port 8000 is available
3. **Database Connection**: Verify PostgreSQL is running and credentials are correct
4. **Static Files**: Ensure the public directory exists and has correct permissions

### Debug Commands

```bash
# Test Gunicorn directly
cd /home/ubuntu/docserver
source venv/bin/activate
gunicorn -c example.gunicorn.conf.py api.main:app

# View application logs
tail -f /home/ubuntu/log/docserver-error.log
tail -f /home/ubuntu/log/docserver-access.log

# Check port usage
sudo netstat -tlnp | grep :8000

# Check service logs
sudo journalctl -u classifier-extractor --since "1 hour ago"
```

## Security Considerations

1. **Firewall**: Configure UFW or iptables to allow only necessary ports
2. **User Permissions**: Run services with limited user privileges
3. **SSL/TLS**: Always use HTTPS in production
4. **Database Security**: Use strong passwords and restrict database access
5. **Environment Variables**: Store sensitive data in environment variables, not in code
6. **Updates**: Regularly update system packages and Python dependencies

## Performance Tuning

### Gunicorn Workers

Adjust worker count based on CPU cores:
```python
workers = (2 * cpu_cores) + 1
```

### Database Connections

Configure connection pooling in your application if needed.

### Nginx Caching

Add caching headers for static content and API responses where appropriate.

## Backup Strategy

1. **Database Backups**: Set up automated PostgreSQL backups
2. **Application Files**: Include uploaded files and configuration in backups
3. **Environment Configuration**: Document all environment variables and configurations

```bash
# Example database backup script
pg_dump -U your_db_user -h localhost your_database > backup_$(date +%Y%m%d_%H%M%S).sql
```