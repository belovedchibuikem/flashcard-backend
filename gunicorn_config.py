"""
Gunicorn configuration for production deployment
"""
import multiprocessing
import os

# Server socket
bind = f"0.0.0.0:{os.getenv('API_PORT', '8000')}"
backlog = 2048

# Worker processes
workers = int(os.getenv('WEB_CONCURRENCY', multiprocessing.cpu_count() * 2 + 1))
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
timeout = 120
keepalive = 5

# Logging
accesslog = "-"  # Log to stdout
errorlog = "-"  # Log to stderr
loglevel = os.getenv('LOG_LEVEL', 'info')
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = "flashcard-api"

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# SSL (if needed)
# keyfile = None
# certfile = None

# Performance
preload_app = True
max_requests = 1000
max_requests_jitter = 50

def on_starting(server):
    """Called just before the master process is initialized."""
    server.log.info("Starting Flashcard API server...")

def on_reload(server):
    """Called to recycle workers during a reload via SIGHUP."""
    server.log.info("Reloading Flashcard API server...")

def when_ready(server):
    """Called just after the server is started."""
    server.log.info("Flashcard API server is ready. Spawning workers...")

def on_exit(server):
    """Called just before exiting Gunicorn."""
    server.log.info("Shutting down Flashcard API server...")
