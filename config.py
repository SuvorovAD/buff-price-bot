import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Конфигурация бота"""
    
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    ALLOWED_USER_IDS = [
        int(uid.strip()) 
        for uid in os.getenv("ALLOWED_USER_IDS", "").split(",") 
        if uid.strip()
    ]
    BUFF_SESSION_COOKIE = os.getenv("BUFF_SESSION_COOKIE")
    CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "60"))
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///data/bot.db")
    
    @classmethod
    def validate(cls):
        """Проверка наличия обязательных переменных"""
        if not cls.BOT_TOKEN:
            raise ValueError("BOT_TOKEN не задан в .env")
        if not cls.ALLOWED_USER_IDS:
            raise ValueError("ALLOWED_USER_IDS не задан в .env")
        if not cls.BUFF_SESSION_COOKIE:
            raise ValueError("BUFF_SESSION_COOKIE не задан в .env")


config = Config()

