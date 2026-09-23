"""Container healthcheck: GET the configured health path on the local port."""
import os
import sys
import urllib.request

port = int(os.environ.get("UVICORN_PORT", "8000"))
path = os.environ.get("HEALTH_PATH", "/health")
raw_timeout = os.environ.get("HEALTH_TIMEOUT", "3")
timeout = float(raw_timeout.rstrip("s秒"))
url = f"http://127.0.0.1:{port}{path}"

try:
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        sys.exit(0 if 200 <= resp.status < 400 else 1)
except Exception:
    sys.exit(1)
