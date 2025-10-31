"""
Скрипт для тестирования Buff API
Используйте для проверки работы API и отладки
"""

import asyncio
import logging
from buff163_unofficial_api import Buff163API
from config import config
from api.currency_converter import currency_converter

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def test_api():
    """Тестирование Buff API"""
    
    print("=" * 60)
    print("🧪 Тестирование Buff API")
    print("=" * 60)
    
    # Загружаем курсы валют
    print("\n0️⃣ Загрузка курсов валют...")
    try:
        await currency_converter.update_rates()
        rates = await currency_converter.get_rates()
        print(f"✅ Курсы валют загружены: 1 CNY = {rates['USD']:.4f} USD, {rates['RUB']:.2f} RUB")
    except Exception as e:
        print(f"⚠️ Ошибка загрузки курсов: {e}")
        print("Будут использованы дефолтные курсы")
    
    try:
        # Инициализация API
        print("\n1️⃣ Инициализация API...")
        api = Buff163API(session_cookie=config.BUFF_SESSION_COOKIE)
        print("✅ API инициализирован")
        
        # Проверяем доступные методы
        print("\n2️⃣ Доступные методы API:")
        methods = [method for method in dir(api) if not method.startswith('_')]
        for method in methods:
            print(f"   - {method}")
        
        # Тестируем получение товара
        goods_id = 43011  # ID для теста
        print(f"\n3️⃣ Тестирование получения товара {goods_id}...")
        
        # Пробуем разные методы
        print("\n   Попытка 1: get_item() - новая версия библиотеки")
        try:
            result = api.get_item(goods_id)
            print(f"   ✅ Успешно! Тип: {type(result)}")
            print(f"   Атрибуты: {dir(result)}")
            
            # Получаем информацию о товаре
            if hasattr(result, 'market_hash_name'):
                print(f"   📦 Название: {result.market_hash_name}")
            
        if hasattr(result, 'sell_min_price'):
            price = float(result.sell_min_price) if result.sell_min_price else 0
            print(f"   💰 Минимальная цена: {result.sell_min_price} CNY")
            
            # Тестируем конвертацию
            if price > 0:
                prices = await currency_converter.convert(price)
                print(f"\n   💱 Конвертация:")
                print(f"   {currency_converter.format_price(prices)}")
            
            if hasattr(result, 'sell_num'):
                print(f"   📊 Количество предложений: {result.sell_num}")
            
            if hasattr(result, 'id'):
                print(f"   🔑 ID товара: {result.id}")
            
            # Проверяем goods_info (Steam цена)
            if hasattr(result, 'goods_info'):
                print(f"\n   📊 goods_info найден!")
                if hasattr(result.goods_info, 'steam_price_cny'):
                    print(f"   💲 Steam цена: {result.goods_info.steam_price_cny} CNY")
            
        except Exception as e:
            print(f"   ❌ Ошибка: {e}")
            import traceback
            traceback.print_exc()
        
        print("\n   Попытка 2: get_featured_market()")
        try:
            market = api.get_featured_market()
            print(f"   ✅ Успешно! Получено товаров: {len(list(market)) if market else 0}")
            
            # Смотрим первый товар
            market_list = list(market)
            if market_list:
                first_item = market_list[0]
                print(f"   Атрибуты товара: {dir(first_item)}")
                if hasattr(first_item, 'market_hash_name'):
                    print(f"   Пример товара: {first_item.market_hash_name}")
                if hasattr(first_item, 'sell_min_price'):
                    print(f"   Цена: {first_item.sell_min_price}")
                if hasattr(first_item, 'id'):
                    print(f"   ID: {first_item.id}")
                elif hasattr(first_item, 'goods_id'):
                    print(f"   goods_id: {first_item.goods_id}")
        except Exception as e:
            print(f"   ❌ Ошибка: {e}")
        
        print("\n" + "=" * 60)
        print("✅ Тестирование завершено!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_api())

