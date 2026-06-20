"""
calendar_server 전역 설정.
pydantic-settings로 .env와 환경변수를 읽는다.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Google Calendar API 자격증명 (서비스 계정 JSON 문자열)
    google_service_account_info: str
    
    # 기본 대상 구글 캘린더 ID
    google_calendar_id: str

    # MCP 서버 포트
    mcp_port: int = 8002

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        case_sensitive=False,
    )


settings = Settings()
