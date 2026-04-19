"""
facility_server 전역 설정.
pydantic-settings로 .env와 환경변수를 읽는다.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # KSPO 공공 API
    kspo_api_key: str
    kspo_base_url: str = "https://apis.data.go.kr/B551014/SRVC_API_SFMS_FACI"

    # HTTP 타임아웃 (초)
    kspo_timeout_seconds: float = 10.0

    # TTL 캐시 설정
    cache_ttl_seconds: int = 600  # 10분
    cache_maxsize: int = 256

    # MCP 서버 포트 (Step 8에서 이미 쓰던 값, 여기선 참고)
    mcp_port: int = 8001

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        case_sensitive=False,
    )


settings = Settings()
