"""
Langfuse 클라이언트 싱글톤 관리 + 버퍼 강제 전송.

- get_langfuse()   : 싱글톤 클라이언트 반환. 키 없거나 초기화 실패하면 None 반환.
- flush_langfuse() : 버퍼에 쌓인 기록을 즉시 전송. 채팅 요청 끝날 때 호출.

Langfuse는 보조 시스템이라 실패해도 앱은 그대로 동작해야 한다.
키가 없거나 오류가 나면 None을 반환하고, 호출부에서 `if not trace:` 분기로 처리한다.
"""
from typing import Optional

from langfuse import Langfuse

from app.config import settings


_client: Optional[Langfuse] = None
_initialized: bool = False


def get_langfuse() -> Optional[Langfuse]:
    """
    Langfuse 클라이언트 싱글톤 접근자.
    처음 호출할 때만 생성하고, 이후엔 캐시된 인스턴스를 그대로 반환한다.

    - API 키 없으면 None 반환 → 환경변수 설정만으로 모니터링 on/off 가능
    - 초기화 실패해도 None 반환 → Langfuse 서버 문제가 채팅에 영향 안 줌
    """
    global _client, _initialized

    # 이후 호출: 이미 한 번 결정했으므로 캐시만 반환한다.
    if _initialized:
        return _client

    _initialized = True

    public_key = settings.langfuse_public_key
    secret_key = settings.langfuse_secret_key
    host = settings.langfuse_host

    # 첫 호출: 키 없으면 관측 비활성화(프로덕션/개발을 설정만으로 토글).
    if not public_key or not secret_key:
        _client = None
        return _client

    try:
        _client = Langfuse(
            public_key=public_key,
            secret_key=secret_key,
            base_url=host,
        )
    except Exception:
        # 초기화 실패 시에도 애플리케이션은 깨지지 않게 한다.
        _client = None

    return _client


def flush_langfuse() -> None:
    """
    버퍼에 쌓인 기록을 Langfuse 서버로 즉시 전송한다.

    Langfuse는 기록을 버퍼에 모았다가 일정량이 되면 한꺼번에 보낸다.
    FastAPI는 요청이 끝나도 프로세스가 살아있어서 버퍼가 차기 전까지 전송이 안 된다.
    서버가 비정상 종료되면 버퍼에 쌓인 기록이 유실되니까, 채팅 요청이 끝나는
    시점에 이 함수를 호출해서 버퍼를 즉시 비운다.

    flush 실패는 기록 일부 유실일 뿐, 채팅 응답에는 영향 없다.
    """
    client = get_langfuse()
    if not client:
        return

    try:
        client.flush()
    except Exception:
        # flush 실패는 기록이 일부 유실될 뿐, 비즈니스 로직에는 영향을 주지 않는다.
        return
