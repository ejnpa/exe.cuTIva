from  pydantic_settings import BaseSettings, SettingsConfigDict




class Settings(BaseSettings):
    
    storage_connection_string: str
    ollama_url: str = "http://100.89.13.43:11434"
    database_url: str = "sqlite:///./database.db"
    secret_key: str
    generated_cache_ttl_days: int = 7
    max_upload_size_bytes: int = 10 * 1024 * 1024
    cookie_secure: bool = True


    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )

settings = Settings()

        
