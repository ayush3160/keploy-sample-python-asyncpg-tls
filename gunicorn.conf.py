import multiprocessing
import os

bind = f"0.0.0.0:{os.environ.get('PORT', '8080')}"
worker_class = "uvicorn.workers.UvicornWorker"
workers = int(os.environ.get("WEB_CONCURRENCY", max(2, multiprocessing.cpu_count())))
accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("LOG_LEVEL", "info")
timeout = int(os.environ.get("TIMEOUT", "30"))
keepalive = int(os.environ.get("KEEPALIVE", "5"))
