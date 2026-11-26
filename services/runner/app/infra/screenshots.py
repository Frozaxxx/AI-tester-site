import asyncio

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from app.config import Settings


class S3Screenshots:
    def __init__(self, settings: Settings) -> None:
        self._bucket = settings.s3_bucket
        self._create_bucket = settings.s3_create_bucket
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url or None,
            aws_access_key_id=settings.s3_access_key or None,
            aws_secret_access_key=settings.s3_secret_key or None,
            region_name=settings.s3_region,
            config=Config(
                s3={"addressing_style": "path"},
                connect_timeout=2,
                read_timeout=3,
                retries={"total_max_attempts": 1},
            ),
        )

    async def save(self, run_id: str, step_index: int, image: bytes) -> None:
        await asyncio.to_thread(self._save, f"runs/{run_id}/{step_index}.jpg", image)

    def _save(self, key: str, image: bytes) -> None:
        try:
            self._client.put_object(
                Bucket=self._bucket, Key=key, Body=image, ContentType="image/jpeg"
            )
        except ClientError as error:
            if not self._create_bucket or error.response["Error"]["Code"] != "NoSuchBucket":
                raise
            try:
                self._client.create_bucket(Bucket=self._bucket)
            except ClientError as create_error:
                if create_error.response["Error"]["Code"] != "BucketAlreadyOwnedByYou":
                    raise
            self._client.put_object(
                Bucket=self._bucket, Key=key, Body=image, ContentType="image/jpeg"
            )
