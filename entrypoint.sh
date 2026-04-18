#!/bin/sh
set -e

CACHE_DIR="${FF1_CACHE_DIR:-/app/cache}"
mkdir -p "$CACHE_DIR"

echo "Downloading FastF1 cache from S3..."
python - <<EOF
import urllib.request
import json
import os
from pathlib import Path

endpoint = "https://minio.lab.sspcloud.fr"
bucket = "mascret"
prefix = "f1-dashboard-cache"
cache_dir = Path(os.environ.get("FF1_CACHE_DIR", "/app/cache"))

# List objects via public MinIO API
url = f"{endpoint}/{bucket}?prefix={prefix}/&list-type=2"
with urllib.request.urlopen(url) as r:
    content = r.read().decode()

# Parse XML to get keys
import xml.etree.ElementTree as ET
root = ET.fromstring(content)
ns = {"s3": "http://s3.amazonaws.com/doc/2006-03-01/"}
keys = [k.text for k in root.findall(".//s3:Key", ns)]

print(f"Found {len(keys)} files to download.")
for i, key in enumerate(keys, 1):
    rel = key[len(prefix) + 1:]
    dest = cache_dir / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(f"{endpoint}/{bucket}/{key}", dest)
    print(f"[{i}/{len(keys)}] {rel}")

print("Cache ready.")
EOF

exec gunicorn app:server \
    --workers 1 \
    --timeout 180 \
    --bind "0.0.0.0:${PORT:-8050}"
