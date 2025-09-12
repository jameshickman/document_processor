# Gunicorn configuration for FastAPI
import os

# Server socket
bind = "0.0.0.0:8000"
backlog = 2048

# Worker processes
workers = 4
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 100
preload_app = True

# Timeout
timeout = 30
keepalive = 2

# Security
user = "www-data"
group = "www-data"
umask = 0

# Logging
accesslog = "/home/ubuntu/log/docserver-access.log"
errorlog = "/home/ubuntu/log/docserver-error.log"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# Process naming
proc_name = "classifier_extractor"

# Server mechanics
daemon = False
pidfile = "/var/run/gunicorn/classifier_extractor.pid"
tmp_upload_dir = None

# SSL (if needed)
# keyfile = "/path/to/keyfile"
# certfile = "/path/to/certfile"

# Environment variables
raw_env = [
    "POSTGRES_USER=user",
    "POSTGRES_PASSWORD=password", 
    "POSTGRES_HOST=localhost",
    "POSTGRES_PORT=5432",
    "POSTGRES_DB=database",
    "ALLOWED_ORIGINS=*",
    "DEBUG=false"
]