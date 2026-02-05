from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from pathlib import Path
from typing import Optional, Union

class Settings(BaseSettings):
    # Bot settings
    BOT_TOKEN: str = "8598762736:AAEXphGzDnhM4fyM3IJzW0mgJLKuPTVvUlc"
    ADMIN_IDS: Union[list[int], int] = [5758764995]
    
    @field_validator("ADMIN_IDS", mode="before")
    @classmethod
    def validate_admin_ids(cls, v):
        if isinstance(v, int):
            return [v]
        return v
    
    # Rate limiting
    RATE_LIMIT: int = 30  # requests per minute
    
    # Cache settings
    CACHE_TTL: int = 3600  # 1 hour
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "data/logs/osint_bot.log"
    
    # API Keys (optional, can be set via environment variables)
    SHODAN_API_KEY: Optional[str] = None
    VIRUSTOTAL_API_KEY: Optional[str] = None
    
    # Model configuration
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

# Create data directories
Path("data/logs").mkdir(parents=True, exist_ok=True)
Path("data/cache").mkdir(parents=True, exist_ok=True)

# Create .env file if it doesn't exist
if not Path(".env").exists():
    with open(".env", "w") as f:
        f.write("""# OSINT Bot Configuration
BOT_TOKEN=your_telegram_bot_token_here
ADMIN_IDS=[123456789]  # Your Telegram ID

# Optional API Keys
# SHODAN_API_KEY=your_shodan_api_key
# VIRUSTOTAL_API_KEY=your_virustotal_api_key
""")

settings = Settings()
