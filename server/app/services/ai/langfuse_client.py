from typing import Optional

from langfuse import Langfuse

from app.config import settings


_client: Optional[Langfuse] = None
_initialized: bool = False


def get_langfuse() -> Optional[Langfuse]:
    """
    Langfuse 클라이언트 싱글톤.

    - LANGFUSE_* 설정이 없으면 None을 반환하여 앱이 평소처럼 동작하도록 한다.
    - SDK 내부 에러는 삼켜지므로, 여기서는 초기화 에러만 조용히 무시한다.

    Langfuse가 없어도 에이전트/서비스가 전부 동작해야 하므로,
    옵저버블리티는 항상 \"best effort\" 수준으로만 붙인다.
    """

    global _client, _initialized

    if _initialized:
        return _client

    _initialized = True

    public_key = settings.langfuse_public_key
    secret_key = settings.langfuse_secret_key
    host = settings.langfuse_host

    if not public_key or not secret_key:
        # 키가 없으면 관측 비활성화. 프로덕션/개발 환경을 설정 값만으로 쉽게 토글할 수 있게 한다.
        _client = None
        return _client

    try:
        _client = Langfuse(
            public_key=public_key,
            secret_key=secret_key,
            base_url=host,
        )
    except Exception:
        # 초기화 실패 시에도 애플리케이션이 깨지지 않도록 한다.
        _client = None

    return _client


def flush_langfuse() -> None:
    """
    Langfuse 버퍼를 비우기 위한 flush 헬퍼.

    FastAPI처럼 수명이 짧은 워커/비동기 작업에서는 프로세스 종료 전에 flush를 호출하지 않으면
    일부 이벤트가 전송되지 않을 수 있어, chat_service 등에서 종료 시점에 한 번 호출해 준다.
    """
    client = get_langfuse()
    if not client:
        return

    try:
        client.flush()
    except Exception:
        # flush 실패는 무시 (관측 기능만 부분 실패). 본 기능에 영향이 가면 안 된다.
        return

