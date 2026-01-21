from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    ENV: str = "dev"
    LOG_LEVEL: str = "INFO"
    LOG_LEVEL: str = "INFO"
    LIVE_TRADING_ENABLED: bool = False
    PAPER_MODE: bool = True
    
    # Exchange Auth
    COINBASE_API_KEY: str = ""
    COINBASE_API_SECRET: str = ""
    
    # Exchange Selection
    EXCHANGE_TYPE: str = "mock"  # or "coinbase"

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()
