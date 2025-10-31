import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand

from config import config
from database.db import db
from bot.handlers import router, check_user_access
from bot.scheduler import init_scheduler
from api.buff_api import buff_client

# Настройка логирования
# Создаем форматтер
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Консоль - INFO и выше
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)

# Файл - WARNING и выше
file_handler = logging.FileHandler('bot.log', encoding='utf-8')
file_handler.setLevel(logging.WARNING)
file_handler.setFormatter(formatter)

# Настраиваем root logger
logging.basicConfig(
    level=logging.INFO,  # Минимальный уровень для всех хендлеров
    handlers=[console_handler, file_handler]
)

logger = logging.getLogger(__name__)


async def set_bot_commands(bot: Bot):
    """Установить команды бота в меню"""
    commands = [
        BotCommand(command="start", description="🏠 Главное меню"),
        BotCommand(command="list", description="📋 Список отслеживаемых товаров"),
        BotCommand(command="now", description="💰 Актуальные цены"),
        BotCommand(command="help", description="ℹ️ Помощь"),
    ]
    
    await bot.set_my_commands(commands)
    logger.info("Команды бота установлены")


async def on_startup(bot: Bot, dp: Dispatcher):
    """Действия при запуске бота"""
    logger.info("Запуск бота...")
    
    # Валидируем конфигурацию
    try:
        config.validate()
    except ValueError as e:
        logger.error(f"Ошибка конфигурации: {e}")
        sys.exit(1)
    
    # Инициализируем базу данных
    try:
        await db.init_db()
        logger.info("База данных инициализирована")
    except Exception as e:
        logger.error(f"Ошибка инициализации БД: {e}")
        sys.exit(1)
    
    # Загружаем курсы валют при старте
    from api.currency_converter import currency_converter
    try:
        logger.info("Загрузка курсов валют при старте...")
        await currency_converter.update_rates()
    except Exception as e:
        logger.warning(f"Не удалось загрузить курсы валют при старте: {e}")
        logger.info("Будут использованы дефолтные курсы")
    
    # Устанавливаем команды бота
    await set_bot_commands(bot)
    
    # Инициализируем и запускаем планировщик
    scheduler = init_scheduler(bot)
    scheduler.start()
    
    # Уведомляем администраторов о запуске
    for admin_id in config.ALLOWED_USER_IDS:
        try:
            await bot.send_message(
                chat_id=admin_id,
                text=(
                    "🤖 <b>Бот запущен!</b>\n\n"
                    f"⏰ Проверка цен каждые {config.CHECK_INTERVAL} минут\n"
                    f"📊 Отслеживание товаров активно\n\n"
                    "Используйте /start для начала работы"
                )
            )
        except Exception as e:
            logger.warning(f"Не удалось отправить уведомление администратору {admin_id}: {e}")
    
    logger.info("Бот успешно запущен")


async def on_shutdown(bot: Bot, dp: Dispatcher):
    """Действия при остановке бота"""
    logger.info("Остановка бота...")
    
    # Останавливаем планировщик
    from bot.scheduler import get_scheduler
    scheduler = get_scheduler()
    if scheduler:
        scheduler.stop()
    
    # Закрываем соединение с БД
    await db.close()
    
    # Закрываем сессию Buff API
    await buff_client.close()
    
    # Уведомляем администраторов об остановке
    for admin_id in config.ALLOWED_USER_IDS:
        try:
            await bot.send_message(
                chat_id=admin_id,
                text="🛑 <b>Бот остановлен</b>"
            )
        except Exception as e:
            logger.warning(f"Не удалось отправить уведомление администратору {admin_id}: {e}")
    
    logger.info("Бот остановлен")


async def main():
    """Главная функция запуска бота"""
    
    # Создаем бота
    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    # Создаем диспетчер
    dp = Dispatcher()
    
    # Регистрируем middleware для проверки доступа
    @dp.message.middleware()
    async def access_control_middleware(handler, event, data):
        """Middleware для проверки доступа пользователя"""
        user_id = event.from_user.id
        
        # Пропускаем только разрешенных пользователей
        if not await check_user_access(user_id):
            await event.answer(
                "❌ У вас нет доступа к этому боту.\n"
                "Обратитесь к администратору для получения доступа."
            )
            return
        
        return await handler(event, data)
    
    @dp.callback_query.middleware()
    async def callback_access_control_middleware(handler, event, data):
        """Middleware для проверки доступа к callback запросам"""
        user_id = event.from_user.id
        
        if not await check_user_access(user_id):
            await event.answer(
                "❌ У вас нет доступа к этому боту.",
                show_alert=True
            )
            return
        
        return await handler(event, data)
    
    # Регистрируем роутер с обработчиками
    dp.include_router(router)
    
    # Регистрируем функции startup и shutdown
    async def startup_handler():
        await on_startup(bot, dp)
    
    async def shutdown_handler():
        await on_shutdown(bot, dp)
    
    dp.startup.register(startup_handler)
    dp.shutdown.register(shutdown_handler)
    
    # Запускаем бота
    try:
        logger.info("Начинаю polling...")
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except KeyboardInterrupt:
        logger.info("Получен сигнал остановки")
    except Exception as e:
        logger.error(f"Ошибка при работе бота: {e}")
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        sys.exit(1)

