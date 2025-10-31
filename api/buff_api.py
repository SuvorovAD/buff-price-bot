import logging
from typing import Optional, Dict, Any
from buff163_unofficial_api import Buff163API
from config import config
from api.currency_converter import currency_converter

logger = logging.getLogger(__name__)


class BuffAPIClient:
    """Клиент для работы с Buff API через buff163_unofficial_api"""
    
    def __init__(self, session_cookie: str):
        self.session_cookie = session_cookie
        self.api: Optional[Buff163API] = None
        self._initialize_api()
    
    def _initialize_api(self):
        """Инициализация API клиента"""
        try:
            self.api = Buff163API(session_cookie=self.session_cookie)
            logger.info("Buff API клиент инициализирован")
        except Exception as e:
            logger.error(f"Ошибка инициализации Buff API: {e}")
            raise
    
    async def get_item_price(self, goods_id: int) -> Optional[Dict[str, Any]]:
        """
        Получить информацию о цене товара по goods_id
        
        Возвращает словарь с ключами:
        - goods_id: ID товара
        - market_hash_name: название товара
        - min_price: минимальная цена в CNY (float)
        - prices: словарь с ценами в разных валютах {"CNY": ..., "USD": ..., "RUB": ...}
        """
        if not self.api:
            logger.error("API клиент не инициализирован")
            return None
        
        try:
            # Используем метод get_item для получения конкретного товара
            # Доступен в новой версии библиотеки с GitHub
            item_data = self.api.get_item(goods_id)
            
            if not item_data:
                logger.warning(f"Товар с goods_id={goods_id} не найден")
                return None
            
            # Получаем название товара
            market_hash_name = item_data.market_hash_name if hasattr(item_data, 'market_hash_name') else f"Item {goods_id}"
            
            # Получаем минимальную цену продажи
            min_price = None
            
            if hasattr(item_data, 'sell_min_price') and item_data.sell_min_price:
                try:
                    min_price = float(item_data.sell_min_price)
                except (ValueError, TypeError):
                    logger.warning(f"Некорректный формат цены для товара {goods_id}: {item_data.sell_min_price}")
            
            if min_price is None:
                logger.warning(f"Нет данных о цене для товара {goods_id}")
                return None
            
            # Конвертируем цену в разные валюты
            prices = await currency_converter.convert(min_price)
            
            return {
                "goods_id": goods_id,
                "market_hash_name": market_hash_name,
                "min_price": min_price,  # Оставляем для обратной совместимости
                "prices": prices  # Новое поле с ценами в разных валютах
            }
        
        except AttributeError as e:
            logger.error(f"Ошибка доступа к атрибутам товара {goods_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Ошибка при получении цены товара {goods_id}: {e}")
            return None
    
    async def search_item_by_name(self, name: str) -> Optional[list]:
        """
        Поиск товаров по названию
        
        Возвращает список товаров с ценами в разных валютах
        """
        if not self.api:
            logger.error("API клиент не инициализирован")
            return None
        
        try:
            results = self.api.search_item(name)
            
            items = []
            for item in results:
                try:
                    min_price = float(item.sell_min_price) if item.sell_min_price else None
                    
                    # Конвертируем цену если она есть
                    prices = None
                    if min_price:
                        prices = await currency_converter.convert(min_price)
                    
                    items.append({
                        "goods_id": getattr(item, 'id', None),
                        "market_hash_name": item.market_hash_name,
                        "min_price": min_price,
                        "prices": prices
                    })
                except Exception as e:
                    logger.warning(f"Ошибка обработки товара при поиске: {e}")
                    continue
            
            return items
        
        except Exception as e:
            logger.error(f"Ошибка при поиске товара '{name}': {e}")
            return None
    
    async def get_featured_market(self, limit: int = 50) -> Optional[list]:
        """
        Получить список популярных товаров с рынка
        
        Возвращает список товаров с ценами в разных валютах
        """
        if not self.api:
            logger.error("API клиент не инициализирован")
            return None
        
        try:
            market = self.api.get_featured_market()
            
            items = []
            count = 0
            
            for item in market:
                if count >= limit:
                    break
                
                try:
                    min_price = float(item.sell_min_price) if item.sell_min_price else None
                    
                    # Конвертируем цену если она есть
                    prices = None
                    if min_price:
                        prices = await currency_converter.convert(min_price)
                    
                    items.append({
                        "goods_id": getattr(item, 'id', None),
                        "market_hash_name": item.market_hash_name,
                        "min_price": min_price,
                        "prices": prices
                    })
                    
                    count += 1
                except Exception as e:
                    logger.warning(f"Ошибка обработки товара из featured market: {e}")
                    continue
            
            return items
        
        except Exception as e:
            logger.error(f"Ошибка при получении featured market: {e}")
            return None
    
    def reinitialize(self):
        """Переинициализировать API клиент"""
        logger.info("Переинициализация Buff API клиента...")
        self._initialize_api()
    
    async def close(self):
        """Закрыть соединение (если требуется)"""
        # buff163_unofficial_api не требует явного закрытия соединений
        logger.info("Buff API клиент закрыт")
        self.api = None


# Глобальный экземпляр клиента
buff_client = BuffAPIClient(config.BUFF_SESSION_COOKIE)
