from uuid import UUID

from redis.asyncio import Redis

LEASE_KEY = "runs:leases"
LEASE_MS = 30_000
EXPIRED_BATCH_SIZE = 100

_TIME = """
local t = redis.call('TIME')
local now = tonumber(t[1]) * 1000 + math.floor(tonumber(t[2]) / 1000)
"""
_ACTIVE = """
local deadline = redis.call('ZSCORE', KEYS[1], ARGV[1])
if not deadline or tonumber(deadline) <= now then
    return 0
end
"""
_EXTEND = "redis.call('ZADD', KEYS[1], now + tonumber(ARGV[2]), ARGV[1]); return 1"


class RedisRunLeases:
    def __init__(self, redis: Redis) -> None:
        self._redis = redis
        self._start = redis.register_script(_TIME + _EXTEND)
        self._renew = redis.register_script(_TIME + _ACTIVE + _EXTEND)
        self._active = redis.register_script(_TIME + _ACTIVE + "return 1")
        self._expired = redis.register_script(
            _TIME + "return redis.call('ZRANGEBYSCORE', KEYS[1], '-inf', now, 'LIMIT', 0, ARGV[1])"
        )

    async def start(self, run_id: UUID) -> None:
        await self._start(keys=[LEASE_KEY], args=[str(run_id), LEASE_MS])

    async def renew(self, run_id: UUID) -> bool:
        return bool(await self._renew(keys=[LEASE_KEY], args=[str(run_id), LEASE_MS]))

    async def active(self, run_id: UUID) -> bool:
        return bool(await self._active(keys=[LEASE_KEY], args=[str(run_id)]))

    async def expired(self) -> list[UUID]:
        members = await self._expired(keys=[LEASE_KEY], args=[EXPIRED_BATCH_SIZE])
        return [UUID(member) for member in members]

    async def remove(self, *run_ids: UUID) -> None:
        if run_ids:
            await self._redis.zrem(LEASE_KEY, *(str(run_id) for run_id in run_ids))
