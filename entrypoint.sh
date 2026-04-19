#!/bin/sh

CACHE_DIR="${FF1_CACHE_DIR:-/app/cache}"
mkdir -p "$CACHE_DIR"

# Download S3 cache in background so gunicorn starts immediately
python - <<EOF &
import urllib.request
import os
import xml.etree.ElementTree as ET
from pathlib import Path

endpoint = "https://minio.lab.sspcloud.fr"
bucket = "mascret"
prefix = "f1-dashboard-cache"
cache_dir = Path(os.environ.get("FF1_CACHE_DIR", "/app/cache"))

try:
    url = f"{endpoint}/{bucket}?prefix={prefix}/&list-type=2"
    with urllib.request.urlopen(url) as r:
        content = r.read().decode()
    root = ET.fromstring(content)
    ns = {"s3": "http://s3.amazonaws.com/doc/2006-03-01/"}
    keys = [k.text for k in root.findall(".//s3:Key", ns)]
    print(f"[S3] Downloading {len(keys)} files in background...")
    for key in keys:
        rel = key[len(prefix) + 1:]
        dest = cache_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(f"{endpoint}/{bucket}/{key}", dest)
    print("[S3] Cache ready.")
except Exception as e:
    print(f"[S3] Warning: cache download failed: {e}")
EOF

exec gunicorn app:server \
    --workers 4 \
    --timeout 300 \
    --bind "0.0.0.0:${PORT:-8050}" \
    --access-logfile - \
    --access-logformat '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s %(D)sµs'
