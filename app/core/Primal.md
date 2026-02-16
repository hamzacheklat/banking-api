Voici un **middleware Prometheus complet et propre**, prêt pour production, compatible avec ton code Sanic actuel.

Il inclut :

* ✅ Requests total
* ✅ Latency (histogram optimisé p95/p99)
* ✅ In-progress requests
* ✅ Request size
* ✅ Response size
* ✅ 4xx / 5xx
* ✅ Exclusion endpoints (metrics, swagger, etc.)
* ✅ Gestion propre des erreurs

---

# 📁 `utils/metrics.py`

```python
from prometheus_client import Counter, Histogram, Gauge

# ==============================
# HTTP Metrics
# ==============================

REQUESTS = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["server", "worker", "method", "endpoint", "status"],
)

LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["server", "worker", "endpoint"],
    buckets=(
        0.01, 0.05, 0.1, 0.2, 0.3,
        0.5, 0.75, 1,
        1.5, 2, 3, 5, 10
    ),
)

IN_PROGRESS = Gauge(
    "http_requests_in_progress",
    "Number of HTTP requests in progress",
    ["server", "worker", "endpoint"],
)

REQUEST_SIZE = Histogram(
    "http_request_size_bytes",
    "HTTP request size",
    buckets=(100, 500, 1_000, 5_000, 10_000, 50_000, 100_000, 1_000_000),
)

RESPONSE_SIZE = Histogram(
    "http_response_size_bytes",
    "HTTP response size",
    buckets=(100, 500, 1_000, 5_000, 10_000, 50_000, 100_000, 1_000_000),
)

ERRORS_5XX = Counter(
    "http_requests_5xx_total",
    "Total HTTP 5xx errors",
    ["server", "endpoint"],
)

ERRORS_4XX = Counter(
    "http_requests_4xx_total",
    "Total HTTP 4xx errors",
    ["server", "endpoint"],
)
```

---

# 📁 `middleware_metrics.py` (middleware complet)

```python
import time
import socket
import os

from sanic import Request
from sanic.response import HTTPResponse

from utils.metrics import (
    REQUESTS,
    LATENCY,
    IN_PROGRESS,
    REQUEST_SIZE,
    RESPONSE_SIZE,
    ERRORS_4XX,
    ERRORS_5XX,
)

EXCLUDED_ENDPOINTS = {
    "metrics",
    "favicon.ico",
    "ready",
    "swagger",
    "swagger-config",
    "openapi",
    "docs",
    "static",
    "sanic-docs",
    "openapi.json",
}

# ============================================
# REQUEST MIDDLEWARE
# ============================================

async def prometheus_start_timer(request: Request):

    endpoint = request.path.split("/")[-1]

    if endpoint in EXCLUDED_ENDPOINTS:
        request.ctx.skip_metrics = True
        return

    request.ctx.skip_metrics = False
    request.ctx.start_time = time.time()
    request.ctx.endpoint = request.path
    request.ctx.method = request.method

    server_id = socket.gethostname()
    worker_id = str(os.getpid())

    request.ctx.server_id = server_id
    request.ctx.worker_id = worker_id

    # In-progress ++
    IN_PROGRESS.labels(server_id, worker_id, request.ctx.endpoint).inc()

    # Request size
    content_length = request.headers.get("content-length")
    if content_length:
        REQUEST_SIZE.observe(int(content_length))


# ============================================
# RESPONSE MIDDLEWARE
# ============================================

def prometheus_record_metrics(request: Request, response: HTTPResponse):

    if getattr(request.ctx, "skip_metrics", False):
        return response

    duration = time.time() - request.ctx.start_time
    status_code = response.status

    server_id = request.ctx.server_id
    worker_id = request.ctx.worker_id
    endpoint = request.ctx.endpoint
    method = request.ctx.method

    # In-progress --
    IN_PROGRESS.labels(server_id, worker_id, endpoint).dec()

    # Request counter
    REQUESTS.labels(
        server_id,
        worker_id,
        method,
        endpoint,
        status_code,
    ).inc()

    # Latency
    LATENCY.labels(
        server_id,
        worker_id,
        endpoint,
    ).observe(duration)

    # Response size
    if response.body:
        RESPONSE_SIZE.observe(len(response.body))

    # Errors
    if 500 <= status_code < 600:
        ERRORS_5XX.labels(server_id, endpoint).inc()
    elif 400 <= status_code < 500:
        ERRORS_4XX.labels(server_id, endpoint).inc()

    return response


# ============================================
# REGISTER FUNCTION
# ============================================

def register_prometheus_middlewares(app):
    app.register_middleware(prometheus_start_timer, "request")
    app.register_middleware(prometheus_record_metrics, "response")
```

---

# 🔥 Ce middleware te donne

Tu peux maintenant monitorer :

* RPS
* p50 / p95 / p99
* erreurs 4xx / 5xx
* requêtes en cours
* taille request / response
* CPU (via métriques auto python)
* memory
* GC
* nombre de workers

---

# 🚀 Bonus recommandé (important)

Ajoute aussi :

```python
from prometheus_client import generate_latest
from sanic.response import raw

@app.get("/metrics")
async def metrics(request):
    return raw(generate_latest(), content_type="text/plain; version=0.0.4")
```

---

Si tu veux, je peux maintenant te faire :

* 🔥 Version ultra-optimisée haute perf (éviter labels cardinality explosion)
* 📊 Dashboard Grafana SRE niveau entreprise
* 🚨 Alerting production-grade (multi-severity)
* 🐳 Stack docker-compose complète prête à déployer

Tu veux qu’on passe en mode production-grade ?
