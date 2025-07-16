# app/config.py
from pathlib import Path
from dotenv import dotenv_values
from pydantic import BaseModel

# Load .env using pathlib
env_path = Path(__file__).parent.parent / '.env'
env = dotenv_values(dotenv_path=env_path)


class Settings(BaseModel):
    API_BASE_URL: str = env.get('API_BASE_URL', 'http://localhost:8000')
    DB_PATH: str = env.get('DB_PATH', 'sqlite:///./comparison.db')


settings = Settings()
