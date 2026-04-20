"""
앱 설정. 환경 변수 및 .env에서 로드한다.

pydantic-settings를 사용해 타입 검증과 기본값을 한 곳에서 관리하고,
.env에 정의되지 않은 변수도 있어도 앱이 깨지지 않도록 extra='ignore'를 쓴다.
"""

from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    openai_api_key: str

    # Langfuse (optional): 키가 없으면 langfuse_client.get_langfuse()가 None을 반환해 관측이 비활성화된다.
    langfuse_public_key: Optional[str] = None
    langfuse_secret_key: Optional[str] = None
    langfuse_host: Optional[str] = "https://cloud.langfuse.com"

    # CORS/앱 URL: 클라이언트가 접근하는 서버 주소. Railway 등에서는 RAILWAY_PUBLIC_DOMAIN 등으로 덮어쓴다.
    base_url: str = "http://localhost:8000"

    # Facility MCP Server (Step 11~)
    # URL이 비어 있으면 facility_agent는 호출 시 예외를 내고, 상위 재라우팅 경로가 동작한다.
    facility_mcp_url: Optional[str] = None
    facility_mcp_timeout_seconds: float = 10.0

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        case_sensitive=False,
    )


settings = Settings()
