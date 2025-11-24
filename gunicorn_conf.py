import multiprocessing
import os

# Gunicorn Configuration File

# Bind to all interfaces on port 8000
bind = "0.0.0.0:8000"

# Worker Options
# Standard formula: 2 * CPUs + 1
workers = 64  # One per core is often a good starting point for async workers on large machines.
worker_class = "uvicorn.workers.UvicornWorker"

# Timeout
# Increase timeout for long queries if necessary
timeout = 120
keepalive = 5

# Logging
loglevel = "info"
accesslog = "-"  # stdout
errorlog = "-"   # stderr

# Process Naming
proc_name = "fiocruz_genomics_api"

# Daemon
daemon = False
