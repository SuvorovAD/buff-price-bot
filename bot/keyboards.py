from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import List
from database.models import Item


def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Главное меню бота"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text="➕ Добавить товар",
            callback_data="add_item"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="📋 Мои товары",
            callback_data="list_items"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🔄 Актуальные цены",
            callback_data="current_prices"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="⚙️ Настройки",
            callback_data="settings"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="ℹ️ Помощь",
            callback_data="help"
        )
    )
    
    return builder.as_markup()


def get_tracked_items_keyboard(items: List[Item]) -> InlineKeyboardMarkup:
    """
    Клавиатура со списком отслеживаемых товаров
    
    Каждый товар имеет кнопку для удаления
    """
    builder = InlineKeyboardBuilder()
    
    if not items:
        builder.row(
            InlineKeyboardButton(
                text="📭 Список пуст",
                callback_data="empty"
            )
        )
    else:
        for item in items:
            # Сокращаем название если слишком длинное
            name = item.market_hash_name
            if len(name) > 40:
                name = name[:37] + "..."
            
            price_text = f"💰 {item.last_price:.2f}" if item.last_price else "❓"
            button_text = f"{name} - {price_text}"
            
            builder.row(
                InlineKeyboardButton(
                    text=button_text,
                    callback_data=f"item_info_{item.id}"
                )
            )
    
    # Кнопка "Назад"
    builder.row(
        InlineKeyboardButton(
            text="🔙 Назад",
            callback_data="back_to_menu"
        )
    )
    
    return builder.as_markup()


def get_item_actions_keyboard(item_id: int) -> InlineKeyboardMarkup:
    """Клавиатура с действиями для конкретного товара"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text="🔄 Обновить цену",
            callback_data=f"refresh_price_{item_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🗑 Удалить из отслеживания",
            callback_data=f"remove_item_{item_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🔙 К списку товаров",
            callback_data="list_items"
        )
    )
    
    return builder.as_markup()


def get_confirm_delete_keyboard(item_id: int) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения удаления товара"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text="✅ Да, удалить",
            callback_data=f"confirm_delete_{item_id}"
        ),
        InlineKeyboardButton(
            text="❌ Отмена",
            callback_data=f"item_info_{item_id}"
        )
    )
    
    return builder.as_markup()


def get_cancel_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура отмены действия"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text="❌ Отмена",
            callback_data="back_to_menu"
        )
    )
    
    return builder.as_markup()


def get_back_to_menu_keyboard() -> InlineKeyboardMarkup:
    """Простая клавиатура с кнопкой возврата в меню"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text="🔙 Главное меню",
            callback_data="back_to_menu"
        )
    )
    
    return builder.as_markup()


def get_settings_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура настроек"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text="⏱ Интервал проверки",
            callback_data="settings_interval"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🔔 Уведомления",
            callback_data="settings_notifications"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🔙 Главное меню",
            callback_data="back_to_menu"
        )
    )
    
    return builder.as_markup()


def get_interval_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора интервала проверки"""
    builder = InlineKeyboardBuilder()
    
    intervals = [
        ("15 минут", 15),
        ("30 минут", 30),
        ("1 час", 60),
        ("2 часа", 120),
        ("3 часа", 180),
        ("6 часов", 360),
        ("12 часов", 720),
        ("24 часа", 1440),
    ]
    
    for text, minutes in intervals:
        builder.row(
            InlineKeyboardButton(
                text=text,
                callback_data=f"set_interval_{minutes}"
            )
        )
    
    builder.row(
        InlineKeyboardButton(
            text="🔙 Назад к настройкам",
            callback_data="settings"
        )
    )
    
    return builder.as_markup()


def get_notifications_keyboard(enabled: bool) -> InlineKeyboardMarkup:
    """Клавиатура включения/выключения уведомлений"""
    builder = InlineKeyboardBuilder()
    
    if enabled:
        builder.row(
            InlineKeyboardButton(
                text="🔕 Отключить уведомления",
                callback_data="toggle_notifications"
            )
        )
    else:
        builder.row(
            InlineKeyboardButton(
                text="🔔 Включить уведомления",
                callback_data="toggle_notifications"
            )
        )
    
    builder.row(
        InlineKeyboardButton(
            text="🔙 Назад к настройкам",
            callback_data="settings"
        )
    )
    
    return builder.as_markup()

