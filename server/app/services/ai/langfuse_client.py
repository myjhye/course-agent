"""
Langfuse 클라이언트를 싱글톤으로 관리하고, 버퍼를 강제 전송한다.

함수:
- get_langfuse()   : Langfuse 클라이언트 싱글톤 반환
- flush_langfuse() : 버퍼에 쌓인 기록을 Langfuse 서버로 강제 전송

설계 포인트:
- Langfuse는 선택적으로 쓴다. 키가 있으면 켜지고(LLM 호출 추적), 없으면 꺼진다.
- 키가 없거나 초기화에 실패해도 None만 반환하고 앱은 그대로 동작한다.
  호출부는 대부분 `if not langfuse` / trace 없음 분기로 None을 처리한다.
"""
from typing import Optional

from langfuse import Langfuse

from app.config import settings


_client: Optional[Langfuse] = None
_initialized: bool = False


def get_langfuse() -> Optional[Langfuse]:
    """
    Langfuse 클라이언트를 한 번만 만들어 재사용하는 싱글톤 접근자다.

    처음 호출할 때만 클라이언트를 생성하고, 이후 호출에서는 만들어둔 걸 그대로 반환한다.
    API 키가 없거나 초기화에 실패하면 None을 반환한다.
    호출부는 None 여부를 확인해 Langfuse 없이도 정상 동작하도록 처리한다.
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
    버퍼에 쌓인 Langfuse 이벤트를 서버로 강제 전송한다.

    Langfuse는 기록을 버퍼에 모았다가 배치로 보낸다.
    FastAPI처럼 요청이 짧게 끝나면 버퍼가 차기 전에 컨텍스트가 끝나 유실될 수 있어,
    chat_service 등이 요청 종료 시점에 이 함수를 호출해 비운다.
    """
    client = get_langfuse()
    if not client:
        return

    try:
        client.flush()
    except Exception:
        # flush 실패는 기록이 일부 유실될 뿐, 비즈니스 로직에는 영향을 주지 않는다.
        return
