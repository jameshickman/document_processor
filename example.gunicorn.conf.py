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
    "DEBUG=false",
    # Storage configuration
    "STORAGE_BACKEND=local",  # Options: "local" or "s3"
    "DOCUMENT_STORAGE=/var/lib/documents",  # For local storage only
    # S3/MinIO configuration (only needed if STORAGE_BACKEND=s3)
    # "S3_ENDPOINT=https://s3.amazonaws.com",  # Or MinIO URL like http://minio:9000
    # "S3_BUCKET=documents",
    # "S3_ACCESS_KEY=access_key",
    # "S3_SECRET_KEY=secret_key",
    # "S3_REGION=us-east-1",  # Optional
    # "S3_PREFIX=",  # Optional base prefix within bucket
]