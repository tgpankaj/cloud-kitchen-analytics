"""
Gunicorn production configuration.
Used by: gunicorn -c gunicorn.conf.py app:app
"""
import multiprocessing
import os

# Bind
bind = f"0.0.0.0:{os.getenv('PORT', '5000')}"

# Workers
workers = int(os.getenv('WEB_CONCURRENCY', multiprocessing.cpu_count() * 2 + 1))
worker_class = 'sync'
threads = 2

# Timeouts
timeout = 120
graceful_timeout = 30
keepalive = 5

# Logging
accesslog = '-'
errorlog = '-'
loglevel = os.getenv('LOG_LEVEL', 'info')
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)sμs'

# Process naming
proc_name = 'cloudkitchen-api'

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# Reload (dev only)
reload = os.getenv('FLASK_ENV') == 'development'

# Preload app (saves memory when multiple workers)
preload_app = True

# Max requests (helps with memory leaks)
max_requests = 1000
max_requests_jitter = 100