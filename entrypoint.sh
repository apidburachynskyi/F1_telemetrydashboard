#!/bin/sh
set -e

CACHE_DIR="${FF1_CACHE_DIR:-/app/cache}"
mkdir -p "$CACHE_DIR"

if [ -n "$AWS_ACCESS_KEY_ID" ] && [ -n "$S3_BUCKET" ]; then
    echo "Downloading FastF1 cache from S3..."
    python - <<EOF
import boto3, os
s3 = boto3.client(
    "s3",
    endpoint_url=os.environ["AWS_S3_ENDPOINT"],
    aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
    aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
    aws_session_token=os.environ.get("AWS_SESSION_TOKEN"),
    region_name=os.environ.get("AWS_DEFAULT_REGION", "us-east-1"),
)
bucket = os.environ["S3_BUCKET"]
cache_dir = os.environ.get("FF1_CACHE_DIR", "/app/cache")
paginator = s3.get_paginator("list_objects_v2")
for page in paginator.paginate(Bucket=bucket):
    for obj in page.get("Contents", []):
        key = obj["Key"]
        dest = f"{cache_dir}/{key}"
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        s3.download_file(bucket, key, dest)
        print(f"  Downloaded {key}")
print("Cache ready.")
EOF
else
    echo "No S3 config found, starting without cache."
fi

exec gunicorn app:server \
    --workers 1 \
    --timeout 180 \
    --bind "0.0.0.0:${PORT:-8050}"
