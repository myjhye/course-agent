from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    database_url: str
    openai_api_key: str
    
    # 추가: 기본값은 로컬 주소로 설정하되, 환경 변수가 있으면 그걸 씁니다.
    # Railway에서는 RAILWAY_PUBLIC_DOMAIN 환경 변수를 자동으로 제공하기도 합니다.
    base_url: str = "http://localhost:8000"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",  # 환경 변수에 더 많은 값이 있어도 에러나지 않게 설정
        case_sensitive=False
    )


settings = Settings()
