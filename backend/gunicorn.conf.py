import multiprocessing

# Bind ke 0.0.0.0 port 8000 (Wajib 0.0.0.0 agar bisa diakses antar container Docker)
bind = "0.0.0.0:8000"

# Rumus aman untuk load Pandas besar di RAM 8GB
workers = 3
worker_class = "uvicorn.workers.UvicornWorker"

# Mencegah Timeout saat proses upload Excel besar
timeout = 300
keepalive = 5

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"

# Proxy configuration (wajib agar Rate Limiter bisa baca IP asli klien, bukan IP Nginx)
forwarded_allow_ips = "*"
