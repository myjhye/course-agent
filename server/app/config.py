from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    openai_api_key: str

    # Langfuse (optional)
    # 키가 설정되지 않으면 관측 기능은 자동으로 비활성화된다.
    langfuse_public_key: Optional[str] = None
    langfuse_secret_key: Optional[str] = None
    # 기본값은 Langfuse 클라우드 EU 리전
    langfuse_host: Optional[str] = "https://cloud.langfuse.com"

    # 추가: 기본값은 로컬 주소로 설정하되, 환경 변수가 있으면 그걸 씁니다.
    # Railway에서는 RAILWAY_PUBLIC_DOMAIN 환경 변수를 자동으로 제공하기도 합니다.
    base_url: str = "http://localhost:8000"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",  # 환경 변수에 더 많은 값이 있어도 에러나지 않게 설정
        case_sensitive=False
    )


settings = Settings()
