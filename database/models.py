from datetime import datetime
from sqlalchemy import BigInteger, String, Float, DateTime, Integer, ForeignKey, Table, Column
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from typing import List


class Base(DeclarativeBase):
    """Базовый класс для моделей"""
    pass


# Связующая таблица many-to-many для пользователей и товаров
user_items = Table(
    "user_items",
    Base.metadata,
    Column("user_id", BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True),
    Column("item_id", Integer, ForeignKey("items.id", ondelete="CASCADE"), primary_key=True),
    Column("subscribed_at", DateTime, default=datetime.utcnow, nullable=False),
)


class User(Base):
    """Модель пользователя"""
    __tablename__ = "users"
    
    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    check_interval: Mapped[int] = mapped_column(Integer, default=60, nullable=False)  # Интервал проверки в минутах (15-1440)
    notifications_enabled: Mapped[bool] = mapped_column(Integer, default=1, nullable=False)  # SQLite не имеет Boolean
    last_check: Mapped[datetime] = mapped_column(DateTime, nullable=True)  # Время последней проверки
    
    # Связь many-to-many с товарами через user_items
    items: Mapped[List["Item"]] = relationship(
        secondary=user_items,
        back_populates="users"
    )
    
    def __repr__(self) -> str:
        return f"User(user_id={self.user_id}, check_interval={self.check_interval}min)"


class Item(Base):
    """Модель товара (общая для всех пользователей)"""
    __tablename__ = "items"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    goods_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)
    market_hash_name: Mapped[str] = mapped_column(String(500), nullable=False)
    last_price: Mapped[float] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Связь many-to-many с пользователями через user_items
    users: Mapped[List["User"]] = relationship(
        secondary=user_items,
        back_populates="items"
    )
    
    # Связь с историей цен
    price_history: Mapped[List["PriceHistory"]] = relationship(
        back_populates="item",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"Item(id={self.id}, goods_id={self.goods_id}, name={self.market_hash_name})"


class PriceHistory(Base):
    """Модель истории изменения цен"""
    __tablename__ = "price_history"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    item_id: Mapped[int] = mapped_column(Integer, ForeignKey("items.id", ondelete="CASCADE"))
    price: Mapped[float] = mapped_column(Float, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    
    # Связь с товаром
    item: Mapped["Item"] = relationship(back_populates="price_history")
    
    def __repr__(self) -> str:
        return f"PriceHistory(id={self.id}, item_id={self.item_id}, price={self.price}, timestamp={self.timestamp})"
