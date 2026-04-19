"""
TTL 기반 in-memory 캐시.

KSPO API 호출 결과를 (파라미터 튜플 → 결과 dict) 형태로 캐싱한다.
캐시 키는 호출 파라미터를 정렬된 tuple로 만들어 생성.
"""

import asyncio
from typing import Any, Callable, Dict, Tuple

from cachetools import TTLCache

from app.config import settings


# 전역 캐시. 싱글 프로세스 내에서만 유효.
# 캐시 키: 정렬된 파라미터 tuple. 값: API 응답 dict.
_cache: TTLCache = TTLCache(
    maxsize=settings.cache_maxsize,
    ttl=settings.cache_ttl_seconds,
)

# 동일 키에 대한 동시 호출이 여러 번 외부 API를 두드리지 않도록 per-key lock 사용.
_locks: Dict[Tuple, asyncio.Lock] = {}


def _make_key(params: Dict[str, Any]) -> Tuple:
    """딕셔너리 파라미터를 해시 가능한 정렬 tuple로 변환."""
    return tuple(sorted((k, v) for k, v in params.items() if v is not None))


async def get_or_fetch(
    params: Dict[str, Any],
    fetcher: Callable[[], Any],
) -> Any:
    """
    params를 키로 캐시를 조회하고, 없으면 fetcher()로 값을 가져와 저장한다.
    fetcher는 async 함수이며 인자를 받지 않는다 (호출자가 closure로 넘겨준다).

    동일 키에 대한 경쟁 조건을 막기 위해 key-specific lock을 사용한다.
    """
    key = _make_key(params)

    # 캐시 hit
    if key in _cache:
        return _cache[key]

    # 캐시 miss: 해당 key에 대한 lock 획득
    lock = _locks.setdefault(key, asyncio.Lock())
    async with lock:
        # Lock 획득 후 다시 한 번 체크 (다른 coroutine이 이미 채워뒀을 수 있음)
        if key in _cache:
            return _cache[key]

        value = await fetcher()
        _cache[key] = value
        return value


def clear() -> None:
    """테스트·수동 리셋용."""
    _cache.clear()
    _locks.clear()
