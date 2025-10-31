import logging
import aiohttp
from typing import Optional, Dict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class CurrencyConverter:
    """Конвертер валют с кешированием курсов"""
    
    def __init__(self):
        self.rates: Dict[str, float] = {}
        self.last_update: Optional[datetime] = None
        self.cache_duration = timedelta(hours=24)  # Курсы действительны 24 часа
    
    async def update_rates(self) -> bool:
        """
        Обновить курсы валют из API
        
        Возвращает True при успехе, False при ошибке
        """
        logger.info("Обновление курсов валют...")
        try:
            # Используем бесплатный API exchangerate-api.com
            async with aiohttp.ClientSession() as session:
                url = "https://api.exchangerate-api.com/v4/latest/CNY"
                
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        self.rates = {
                            "USD": data["rates"].get("USD", 0.14),  # Примерный курс
                            "RUB": data["rates"].get("RUB", 13.0)   # Примерный курс
                        }
                        self.last_update = datetime.now()
                        
                        logger.info(f"✅ Курсы валют обновлены: 1 CNY = {self.rates['USD']:.4f} USD, {self.rates['RUB']:.2f} RUB")
                        return True
                    else:
                        logger.warning(f"Не удалось получить курсы валют: HTTP {response.status}")
                        return False
        
        except Exception as e:
            logger.error(f"Ошибка при получении курсов валют: {e}")
            return False
    
    async def get_rates(self) -> Dict[str, float]:
        """
        Получить текущие курсы валют
        
        Возвращает словарь: {"USD": rate, "RUB": rate}
        где rate - сколько стоит 1 CNY в этой валюте
        """
        # Если курсов нет - загружаем дефолтные
        if not self.rates:
            logger.warning("Курсы валют еще не загружены, используем дефолтные")
            self.rates = {
                "USD": 0.14,   # Примерный курс 1 CNY = 0.14 USD
                "RUB": 13.0    # Примерный курс 1 CNY = 13 RUB
            }
        
        return self.rates
    
    async def convert(self, amount_cny: float) -> Dict[str, float]:
        """
        Конвертировать сумму из CNY в другие валюты
        
        Args:
            amount_cny: Сумма в CNY
        
        Returns:
            Словарь с суммами в разных валютах:
            {"CNY": amount, "USD": amount, "RUB": amount}
        """
        rates = await self.get_rates()
        
        return {
            "CNY": round(amount_cny, 2),
            "USD": round(amount_cny * rates["USD"], 2),
            "RUB": round(amount_cny * rates["RUB"], 2)
        }
    
    def format_price(self, prices: Dict[str, float]) -> str:
        """
        Форматировать цены для отображения
        
        Args:
            prices: Словарь с ценами {"CNY": ..., "USD": ..., "RUB": ...}
        
        Returns:
            Отформатированная строка с ценами
        """
        return (
            f"💴 {prices['CNY']:.2f} CNY\n"
            f"💵 ${prices['USD']:.2f} USD\n"
            f"💸 {prices['RUB']:.2f} RUB"
        )


# Глобальный экземпляр конвертера
currency_converter = CurrencyConverter()

