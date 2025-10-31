"""
Скрипт для инициализации базы данных
Используйте если нужно создать таблицы вручную
"""

import asyncio
import logging
from database.db import db

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def main():
    """Инициализировать базу данных"""
    try:
        logger.info("Инициализация базы данных...")
        await db.init_db()
        logger.info("✅ База данных успешно инициализирована!")
        logger.info("Таблицы созданы: users, tracked_items, price_history")
    except Exception as e:
        logger.error(f"❌ Ошибка при инициализации БД: {e}")
        raise
    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(main())

