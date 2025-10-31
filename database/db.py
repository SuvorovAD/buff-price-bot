import logging
from datetime import datetime, timedelta
from typing import Optional, List
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select, delete, and_
from sqlalchemy.orm import selectinload

from database.models import Base, User, Item, PriceHistory, user_items
from config import config

logger = logging.getLogger(__name__)


class Database:
    """Класс для работы с базой данных"""
    
    def __init__(self):
        self.engine = create_async_engine(config.DATABASE_URL, echo=False)
        self.async_session = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
    
    async def init_db(self):
        """Инициализация базы данных (создание таблиц)"""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("База данных инициализирована")
    
    async def close(self):
        """Закрытие соединения с БД"""
        await self.engine.dispose()
        logger.info("Соединение с БД закрыто")
    
    # === Операции с пользователями ===
    
    async def add_user(self, user_id: int):
        """Добавить пользователя, если его еще нет"""
        async with self.async_session() as session:
            result = await session.execute(
                select(User).where(User.user_id == user_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                user = User(
                    user_id=user_id,
                    check_interval=60,  # По умолчанию 60 минут
                    notifications_enabled=True
                )
                session.add(user)
                await session.commit()
                logger.info(f"Добавлен новый пользователь: {user_id}")
    
    async def get_user(self, user_id: int) -> Optional[User]:
        """Получить пользователя по ID"""
        async with self.async_session() as session:
            result = await session.execute(
                select(User).where(User.user_id == user_id)
            )
            return result.scalar_one_or_none()
    
    async def update_user_settings(self, user_id: int, check_interval: Optional[int] = None, 
                                   notifications_enabled: Optional[bool] = None):
        """Обновить настройки пользователя"""
        async with self.async_session() as session:
            result = await session.execute(
                select(User).where(User.user_id == user_id)
            )
            user = result.scalar_one_or_none()
            
            if user:
                if check_interval is not None:
                    # Проверяем диапазон (15 минут - 24 часа)
                    if check_interval < 15 or check_interval > 1440:
                        raise ValueError("Интервал должен быть от 15 минут до 24 часов")
                    user.check_interval = check_interval
                    logger.info(f"Обновлен интервал проверки для {user_id}: {check_interval} мин")
                
                if notifications_enabled is not None:
                    user.notifications_enabled = notifications_enabled
                    logger.info(f"Уведомления для {user_id}: {'включены' if notifications_enabled else 'отключены'}")
                
                await session.commit()
    
    async def update_user_last_check(self, user_id: int):
        """Обновить время последней проверки пользователя"""
        async with self.async_session() as session:
            result = await session.execute(
                select(User).where(User.user_id == user_id)
            )
            user = result.scalar_one_or_none()
            
            if user:
                user.last_check = datetime.utcnow()
                await session.commit()
    
    async def get_users_to_check(self) -> List[User]:
        """Получить пользователей, которым пора проверять цены"""
        async with self.async_session() as session:
            now = datetime.utcnow()
            
            # Получаем пользователей с включенными уведомлениями
            result = await session.execute(
                select(User)
                .where(User.notifications_enabled == 1)
                .options(selectinload(User.items))
            )
            users = result.scalars().all()
            
            # Фильтруем по времени последней проверки
            users_to_check = []
            for user in users:
                # Если товаров нет - пропускаем
                if not user.items:
                    continue
                
                # Если никогда не проверяли - проверяем
                if user.last_check is None:
                    users_to_check.append(user)
                    continue
                
                # Проверяем, прошло ли достаточно времени
                time_passed = (now - user.last_check).total_seconds() / 60  # в минутах
                if time_passed >= user.check_interval:
                    users_to_check.append(user)
            
            return users_to_check
    
    # === Операции с товарами ===
    
    async def get_or_create_item(self, goods_id: int, market_hash_name: str, initial_price: float) -> Item:
        """Получить товар или создать, если не существует"""
        async with self.async_session() as session:
            # Ищем товар по goods_id
            result = await session.execute(
                select(Item).where(Item.goods_id == goods_id)
            )
            item = result.scalar_one_or_none()
            
            if not item:
                # Создаем новый товар
                item = Item(
                    goods_id=goods_id,
                    market_hash_name=market_hash_name,
                    last_price=initial_price
                )
                session.add(item)
                await session.commit()
                await session.refresh(item)
                logger.info(f"Создан новый товар: {goods_id} - {market_hash_name}")
            
            return item
    
    async def add_user_subscription(self, user_id: int, goods_id: int, market_hash_name: str, initial_price: float):
        """Добавить подписку пользователя на товар"""
        async with self.async_session() as session:
            # Получаем или создаем товар
            item = await self.get_or_create_item(goods_id, market_hash_name, initial_price)
            
            # Проверяем, не подписан ли уже пользователь
            result = await session.execute(
                select(user_items).where(
                    and_(
                        user_items.c.user_id == user_id,
                        user_items.c.item_id == item.id
                    )
                )
            )
            subscription = result.first()
            
            if not subscription:
                # Добавляем подписку
                await session.execute(
                    user_items.insert().values(
                        user_id=user_id,
                        item_id=item.id,
                        subscribed_at=datetime.utcnow()
                    )
                )
                await session.commit()
                logger.info(f"Пользователь {user_id} подписался на товар {goods_id}")
    
    async def remove_user_subscription(self, user_id: int, item_id: int) -> bool:
        """Удалить подписку пользователя на товар"""
        async with self.async_session() as session:
            result = await session.execute(
                delete(user_items).where(
                    and_(
                        user_items.c.user_id == user_id,
                        user_items.c.item_id == item_id
                    )
                )
            )
            await session.commit()
            
            if result.rowcount > 0:
                logger.info(f"Пользователь {user_id} отписался от товара {item_id}")
                
                # Проверяем, остались ли подписчики у товара
                subscribers = await session.execute(
                    select(user_items).where(user_items.c.item_id == item_id)
                )
                
                if not subscribers.first():
                    # Если подписчиков нет - удаляем товар
                    await session.execute(
                        delete(Item).where(Item.id == item_id)
                    )
                    await session.commit()
                    logger.info(f"Товар {item_id} удален (нет подписчиков)")
                
                return True
            
            return False
    
    async def get_user_items(self, user_id: int) -> List[Item]:
        """Получить все товары, на которые подписан пользователь"""
        async with self.async_session() as session:
            result = await session.execute(
                select(Item)
                .join(user_items)
                .where(user_items.c.user_id == user_id)
                .order_by(Item.created_at.desc())
            )
            items = result.scalars().all()
            return list(items)
    
    async def get_item_by_id(self, item_id: int) -> Optional[Item]:
        """Получить товар по ID"""
        async with self.async_session() as session:
            result = await session.execute(
                select(Item).where(Item.id == item_id)
            )
            return result.scalar_one_or_none()
    
    async def get_item_by_goods_id(self, goods_id: int) -> Optional[Item]:
        """Получить товар по goods_id"""
        async with self.async_session() as session:
            result = await session.execute(
                select(Item).where(Item.goods_id == goods_id)
            )
            return result.scalar_one_or_none()
    
    async def update_item_price(self, item_id: int, new_price: float):
        """Обновить цену товара"""
        async with self.async_session() as session:
            result = await session.execute(
                select(Item).where(Item.id == item_id)
            )
            item = result.scalar_one_or_none()
            
            if item:
                item.last_price = new_price
                item.updated_at = datetime.utcnow()
                await session.commit()
                logger.debug(f"Обновлена цена товара {item_id}: {new_price}")
    
    async def get_all_tracked_items(self) -> List[Item]:
        """Получить все отслеживаемые товары (с подписчиками)"""
        async with self.async_session() as session:
            result = await session.execute(
                select(Item)
                .join(user_items)
                .options(selectinload(Item.users))
                .distinct()
            )
            items = result.scalars().all()
            return list(items)
    
    async def get_item_subscribers(self, item_id: int) -> List[int]:
        """Получить список user_id подписчиков товара"""
        async with self.async_session() as session:
            result = await session.execute(
                select(user_items.c.user_id).where(user_items.c.item_id == item_id)
            )
            user_ids = result.scalars().all()
            return list(user_ids)
    
    async def is_user_subscribed(self, user_id: int, goods_id: int) -> bool:
        """Проверить, подписан ли пользователь на товар"""
        async with self.async_session() as session:
            # Сначала находим item_id по goods_id
            item_result = await session.execute(
                select(Item.id).where(Item.goods_id == goods_id)
            )
            item_id = item_result.scalar_one_or_none()
            
            if not item_id:
                return False
            
            # Проверяем подписку
            result = await session.execute(
                select(user_items).where(
                    and_(
                        user_items.c.user_id == user_id,
                        user_items.c.item_id == item_id
                    )
                )
            )
            return result.first() is not None
    
    # === Операции с историей цен ===
    
    async def add_price_history(self, item_id: int, price: float):
        """Добавить запись в историю цен"""
        async with self.async_session() as session:
            history = PriceHistory(
                item_id=item_id,
                price=price
            )
            session.add(history)
            await session.commit()
            logger.debug(f"Добавлена запись в историю цен: товар {item_id}, цена {price}")
    
    async def get_price_history(self, item_id: int, days: int = 7) -> List[PriceHistory]:
        """Получить историю цен товара за последние N дней"""
        async with self.async_session() as session:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            result = await session.execute(
                select(PriceHistory)
                .where(
                    and_(
                        PriceHistory.item_id == item_id,
                        PriceHistory.timestamp >= cutoff_date
                    )
                )
                .order_by(PriceHistory.timestamp.desc())
            )
            history = result.scalars().all()
            return list(history)
    
    async def cleanup_old_price_history(self, days: int = 7):
        """Очистить историю цен старше указанного количества дней"""
        async with self.async_session() as session:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            result = await session.execute(
                delete(PriceHistory).where(PriceHistory.timestamp < cutoff_date)
            )
            await session.commit()
            logger.info(f"Удалено {result.rowcount} старых записей из истории цен")


# Глобальный экземпляр базы данных
db = Database()
