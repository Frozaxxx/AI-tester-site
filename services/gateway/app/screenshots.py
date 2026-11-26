import asyncio
from contextlib import closing
from functools import lru_cache

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from app.config import settings

MAX_SCREENSHOT_BYTES = 2_000_000


class S3Screenshots:
    def __init__(self) -> None:
        self._bucket = settings.s3_bucket
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

    async def list_steps(self, run_id: str) -> set[int]:
        return await asyncio.to_thread(self._list_steps, run_id)

    def _list_steps(self, run_id: str) -> set[int]:
        prefix = f"runs/{run_id}/"
        try:
            objects = self._client.list_objects_v2(Bucket=self._bucket, Prefix=prefix)
        except ClientError as error:
            if error.response["Error"]["Code"] != "NoSuchBucket":
                raise
            return set()
        names = (item["Key"].removeprefix(prefix) for item in objects.get("Contents", []))
        return {
            int(name[:-4])
            for name in names
            if name.endswith(".jpg")
            and name[:-4].isascii()
            and name[:-4].isdigit()
            and len(name) <= 9
        }

    async def get(self, run_id: str, index: int) -> bytes | None:
        return await asyncio.to_thread(self._get, run_id, index)

    def _get(self, run_id: str, index: int) -> bytes | None:
        try:
            obj = self._client.get_object(Bucket=self._bucket, Key=f"runs/{run_id}/{index}.jpg")
        except ClientError as error:
            if error.response["Error"]["Code"] not in {"NoSuchBucket", "NoSuchKey", "404"}:
                raise
            return None
        with closing(obj["Body"]) as body:
            if obj["ContentLength"] <= MAX_SCREENSHOT_BYTES:
                return body.read()
        return None


@lru_cache(maxsize=1)
def screenshot_store() -> S3Screenshots | None:
    return S3Screenshots() if settings.s3_bucket else None
