#!/usr/bin/env python3
"""
Gunicorn configuration for ABB Product Search Application.
Optimized for Render.com free tier memory and timeout constraints.
"""

import os

# Basic server configuration  
bind = f"0.0.0.0:{os.environ.get('PORT', '5000')}"
workers = 1  # Single worker for free tier (512MB memory limit)

# Worker configuration - optimized for free tier
worker_class = "sync"
worker_connections = 100  # Reduced for memory efficiency
max_requests = 500  # Restart worker more frequently to prevent memory buildup
max_requests_jitter = 50

# Timeout settings - balanced for free tier
timeout = 120  # 2 minutes - increased from default 30s but not excessive
keepalive = 2
graceful_timeout = 30

# Memory management - minimal for free tier
preload_app = False  # Don't preload to save memory on startup

# Process naming
proc_name = "abb_search_app"

# Logging
errorlog = "-"  # Log to stderr
loglevel = "info"
accesslog = "-"  # Access log to stderr
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Performance tuning
worker_rlimit_nofile = 65535  # Increase file descriptor limit
worker_rlimit_core = 0  # Don't create core dumps

def when_ready(server):
    """Called when the server is started."""
    server.log.info("ABB Product Search server is ready. Listening on %s", server.address)

def worker_int(worker):
    """Called when a worker receives the SIGINT or SIGTERM signal."""
    worker.log.info("Worker received SIGINT or SIGTERM")

def pre_fork(server, worker):
    """Called before a worker is forked."""
    server.log.info("Worker spawned (pid: %s)", worker.pid)

def post_fork(server, worker):
    """Called after a worker is forked."""
    server.log.info("Worker spawned (pid: %s)", worker.pid)
    
def max_requests_jitter_handler(worker):
    """Called when a worker reaches the max_requests limit."""
    worker.log.info("Worker %s recycling due to max_requests limit", worker.pid)

# Memory monitoring (optional, requires psutil)
try:
    import psutil
    
    def worker_abort(worker):
        """Called when a worker is aborted."""
        worker.log.info("Worker %s aborted", worker.pid)
        try:
            process = psutil.Process(worker.pid)
            memory_info = process.memory_info()
            worker.log.info("Worker %s memory usage: RSS=%s MB, VMS=%s MB", 
                           worker.pid, 
                           memory_info.rss // 1024 // 1024,
                           memory_info.vms // 1024 // 1024)
        except Exception:
            pass
            
except ImportError:
    pass