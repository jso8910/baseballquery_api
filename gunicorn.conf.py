import multiprocessing

bind = "0.0.0.0:8000"
backlog = 2048
worker_class = "gevent"
worker_connections = 1000
timeout = 240
workers = multiprocessing.cpu_count() * 3