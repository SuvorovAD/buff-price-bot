import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot

from config import config
from database.db import db
from api.buff_api import buff_client
from api.currency_converter import currency_converter

logger = logging.getLogger(__name__)


class PriceScheduler:
    """Планировщик для проверки цен"""
    
    def __init__(self, bot: Bot):
        self.bot = bot
        self.scheduler = AsyncIOScheduler()
        self.is_running = False
    
    async def check_prices(self):
        """Проверить цены для пользователей, которым пора проверять"""
        logger.info("Начинаю проверку цен...")
        
        try:
            # Получаем пользователей, которым пора проверять цены
            users_to_check = await db.get_users_to_check()
            
            if not users_to_check:
                logger.debug("Нет пользователей для проверки в данный момент")
                return
            
            logger.info(f"Проверяю цены для {len(users_to_check)} пользователей...")
            
            # Для каждого пользователя проверяем его товары
            for user in users_to_check:
                try:
                    logger.info(f"Проверяю товары пользователя {user.user_id} ({len(user.items)} товаров)")
                    
                    # Собираем уникальные товары для этого пользователя
                    items_to_check = user.items
                    
                    for item in items_to_check:
                        try:
                            # Получаем актуальную цену
                            price_data = await buff_client.get_item_price(item.goods_id)
                            
                            if not price_data:
                                logger.warning(
                                    f"Не удалось получить цену для товара {item.goods_id}"
                                )
                                continue
                            
                            current_price = price_data["min_price"]
                            prices = price_data.get("prices", {})
                            old_price = item.last_price
                            
                            # Добавляем запись в историю
                            await db.add_price_history(item.id, current_price)
                            
                            # Проверяем, изменилась ли цена
                            if old_price is None:
                                # Первая проверка цены - просто сохраняем
                                await db.update_item_price(item.id, current_price)
                                logger.info(
                                    f"Установлена начальная цена {current_price} "
                                    f"для товара {item.goods_id}"
                                )
                            elif current_price != old_price:
                                # Цена изменилась - отправляем уведомление
                                diff = current_price - old_price
                                percent = (diff / old_price) * 100
                                
                                # Обновляем цену в БД
                                await db.update_item_price(item.id, current_price)
                                
                                # Формируем сообщение
                                if diff > 0:
                                    emoji = "📈"
                                    change_text = f"+{diff:.2f} CNY (+{percent:.1f}%)"
                                else:
                                    emoji = "📉"
                                    change_text = f"{diff:.2f} CNY ({percent:.1f}%)"
                                
                                # Форматируем цены
                                price_text = currency_converter.format_price(prices) if prices else f"💵 {current_price:.2f} CNY"
                                old_prices = await currency_converter.convert(old_price) if old_price else {}
                                old_price_text = currency_converter.format_price(old_prices) if old_prices else f"💵 {old_price:.2f} CNY"
                                
                                message = (
                                    f"{emoji} <b>Изменение цены!</b>\n\n"
                                    f"📦 {item.market_hash_name}\n"
                                    f"🔗 goods_id: {item.goods_id}\n\n"
                                    f"💰 <b>Новая цена:</b>\n{price_text}\n\n"
                                    f"💾 <b>Старая цена:</b>\n{old_price_text}\n\n"
                                    f"📊 Изменение: {change_text}\n\n"
                                    f"🕒 {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}"
                                )
                                
                                # Отправляем уведомление пользователю
                                try:
                                    await self.bot.send_message(
                                        chat_id=user.user_id,
                                        text=message
                                    )
                                    logger.info(
                                        f"Отправлено уведомление пользователю {user.user_id} "
                                        f"о товаре {item.goods_id}"
                                    )
                                except Exception as e:
                                    logger.error(
                                        f"Ошибка при отправке уведомления пользователю "
                                        f"{user.user_id}: {e}"
                                    )
                            else:
                                logger.debug(
                                    f"Цена товара {item.goods_id} не изменилась: "
                                    f"{current_price}"
                                )
                        
                        except Exception as e:
                            logger.error(
                                f"Ошибка при проверке товара {item.goods_id}: {e}"
                            )
                            continue
                    
                    # Обновляем время последней проверки для пользователя
                    await db.update_user_last_check(user.user_id)
                    logger.info(f"Проверка для пользователя {user.user_id} завершена")
                
                except Exception as e:
                    logger.error(
                        f"Ошибка при проверке цен для пользователя {user.user_id}: {e}"
                    )
                    continue
            
            logger.info("Проверка цен завершена")
        
        except Exception as e:
            logger.error(f"Ошибка при проверке цен: {e}")
    
    async def cleanup_old_history(self):
        """Очистить старую историю цен (старше 7 дней)"""
        logger.info("Очистка старой истории цен...")
        try:
            await db.cleanup_old_price_history(days=7)
            logger.info("Старая история цен очищена")
        except Exception as e:
            logger.error(f"Ошибка при очистке истории: {e}")
    
    async def update_currency_rates(self):
        """Обновить курсы валют"""
        logger.info("Плановое обновление курсов валют...")
        try:
            success = await currency_converter.update_rates()
            if success:
                logger.info("Курсы валют успешно обновлены")
            else:
                logger.warning("Не удалось обновить курсы валют")
        except Exception as e:
            logger.error(f"Ошибка при обновлении курсов валют: {e}")
    
    def start(self):
        """Запустить планировщик"""
        if self.is_running:
            logger.warning("Планировщик уже запущен")
            return
        
        # Добавляем задачу проверки цен (проверяем каждую минуту, кому пора проверять)
        self.scheduler.add_job(
            self.check_prices,
            trigger="interval",
            minutes=1,  # Проверяем каждую минуту, но проверяем только тех, кому пора
            id="check_prices",
            name="Проверка цен товаров",
            replace_existing=True
        )
        
        # Добавляем задачу очистки истории (раз в неделю по воскресеньям в 3:00)
        self.scheduler.add_job(
            self.cleanup_old_history,
            trigger="cron",
            day_of_week="sun",
            hour=3,
            minute=0,
            id="cleanup_history",
            name="Очистка старой истории цен",
            replace_existing=True
        )
        
        # Добавляем задачу обновления курсов валют (каждый день в 00:00)
        self.scheduler.add_job(
            self.update_currency_rates,
            trigger="cron",
            hour=0,
            minute=0,
            id="update_currency",
            name="Обновление курсов валют",
            replace_existing=True
        )
        
        self.scheduler.start()
        self.is_running = True
        logger.info("Планировщик запущен. Проверка пользователей каждую минуту (персональные интервалы)")
    
    def stop(self):
        """Остановить планировщик"""
        if not self.is_running:
            logger.warning("Планировщик не запущен")
            return
        
        self.scheduler.shutdown()
        self.is_running = False
        logger.info("Планировщик остановлен")


def init_scheduler(bot: Bot) -> PriceScheduler:
    """Инициализировать планировщик"""
    return PriceScheduler(bot)
