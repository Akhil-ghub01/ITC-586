from pydantic_settings import BaseSettings



class Settings(BaseSettings):
    # General
    app_name: str = "AI Customer Service Backend"
    environment: str = "dev"

    # LLM / RAG settings
    gemini_api_key: str | None = None

    class Config:
        env_file = ".env"


settings = Settings()
