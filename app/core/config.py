import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # App
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", 8000))
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"
    
    # Database
    DB_URL = os.getenv("DB_URL", "postgresql+asyncpg://user:pass@localhost/banking")
    
    # Security
    SECRET_KEY = os.getenv("SECRET_KEY", "secret-key-change-me")
    JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", 30))

settings = Config()
