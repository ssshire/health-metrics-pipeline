from dotenv import load_dotenv
import os
import boto3
import requests
from datetime import date
from botocore.exceptions import ClientError

load_dotenv()

endpoint = os.getenv("MINIO_ENDPOINT")
bucket = os.getenv("MINIO_BUCKET")
access_key = os.getenv("MINIO_ROOT_USER")
secret_key = os.getenv("MINIO_ROOT_PASSWORD")

CDC_URL = "https://data.cdc.gov/api/views/swc5-untb/rows.csv?accessType=DOWNLOAD"


def _s3_client():
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
    )


def _ensure_bucket(client):
    try:
        client.head_bucket(Bucket=bucket)
    except ClientError:
        client.create_bucket(Bucket=bucket)


def run():
    print("Downloading CDC PLACES data...")
    response = requests.get(CDC_URL, timeout=120)
    response.raise_for_status()

    key = f"raw/places_county_{date.today()}.csv"

    client = _s3_client()
    _ensure_bucket(client)

    client.put_object(Bucket=bucket, Key=key, Body=response.content)
    print(f"Uploaded {len(response.content)} bytes to s3://{bucket}/{key}")


if __name__ == "__main__":
    run()