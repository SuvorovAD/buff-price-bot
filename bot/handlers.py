import logging
from aiogram import Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from typing import Any

from config import config
from database.db import db
from api.buff_api import buff_client
from api.currency_converter import currency_converter
from bot.keyboards import (
    get_main_menu_keyboard,
    get_tracked_items_keyboard,
    get_item_actions_keyboard,
    get_confirm_delete_keyboard,
    get_cancel_keyboard,
    get_back_to_menu_keyboard,
    get_settings_keyboard,
    get_interval_keyboard,
    get_notifications_keyboard
)

logger = logging.getLogger(__name__)

# Создаем роутер
router = Router()


# FSM состояния для добавления товара
class AddItemStates(StatesGroup):
    waiting_for_goods_id = State()


# === Middleware для проверки доступа ===

async def check_user_access(user_id: int) -> bool:
    """Проверить, есть ли у пользователя доступ к боту"""
    return user_id in config.ALLOWED_USER_IDS


# === Обработчики команд ===

@router.message(CommandStart())
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    user_id = message.from_user.id
    
    if not await check_user_access(user_id):
        await message.answer(
            "❌ У вас нет доступа к этому боту.\n"
            "Обратитесь к администратору для получения доступа."
        )
        return
    
    # Добавляем пользователя в БД
    await db.add_user(user_id)
    
    await message.answer(
        f"👋 Добро пожаловать, {message.from_user.first_name}!\n\n"
        "🤖 Я бот для отслеживания цен на скины CS2 с сайта Buff.163.com\n\n"
        "📊 Что я умею:\n"
        "• Отслеживать цены на выбранные товары\n"
        "• Уведомлять об изменении цен\n"
        "• Показывать актуальные цены\n\n"
        "Выберите действие:",
        reply_markup=get_main_menu_keyboard()
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Обработчик команды /help"""
    user_id = message.from_user.id
    
    if not await check_user_access(user_id):
        await message.answer("❌ У вас нет доступа к этому боту.")
        return
    
    help_text = (
        "ℹ️ <b>Помощь по использованию бота</b>\n\n"
        "<b>Как добавить товар:</b>\n"
        "1. Нажмите '➕ Добавить товар'\n"
        "2. Найдите товар на buff.163.com\n"
        "3. В URL товара найдите goods_id\n"
        "   Пример: https://buff.163.com/goods/<b>43012</b>\n"
        "4. Отправьте этот номер боту\n\n"
        "<b>Команды:</b>\n"
        "/start - Главное меню\n"
        "/list - Список отслеживаемых товаров\n"
        "/now - Актуальные цены\n"
        "/help - Эта справка\n\n"
        "<b>Уведомления:</b>\n"
        f"Бот проверяет цены каждые {config.CHECK_INTERVAL} минут "
        "и уведомляет вас об изменениях."
    )
    
    await message.answer(help_text, reply_markup=get_back_to_menu_keyboard())


@router.message(Command("list"))
async def cmd_list(message: Message):
    """Обработчик команды /list"""
    user_id = message.from_user.id
    
    if not await check_user_access(user_id):
        await message.answer("❌ У вас нет доступа к этому боту.")
        return
    
    items = await db.get_user_items(user_id)
    
    if not items:
        await message.answer(
            "📭 У вас нет отслеживаемых товаров.\n\n"
            "Нажмите '➕ Добавить товар' для начала отслеживания.",
            reply_markup=get_main_menu_keyboard()
        )
        return
    
    await message.answer(
        f"📋 <b>Ваши отслеживаемые товары ({len(items)}):</b>",
        reply_markup=get_tracked_items_keyboard(items)
    )


@router.message(Command("now"))
async def cmd_now(message: Message):
    """Обработчик команды /now - показать актуальные цены"""
    user_id = message.from_user.id
    
    if not await check_user_access(user_id):
        await message.answer("❌ У вас нет доступа к этому боту.")
        return
    
    items = await db.get_user_items(user_id)
    
    if not items:
        await message.answer(
            "📭 У вас нет отслеживаемых товаров.",
            reply_markup=get_main_menu_keyboard()
        )
        return
    
    status_msg = await message.answer("🔄 Загружаю актуальные цены...")
    
    response_text = "💰 <b>Актуальные цены:</b>\n\n"
    
    for item in items:
        price_data = await buff_client.get_item_price(item.goods_id)
        
        if price_data:
            current_price = price_data["min_price"]
            prices = price_data.get("prices", {})
            old_price = item.last_price
            
            # Вычисляем изменение цены
            change_text = ""
            if old_price:
                diff = current_price - old_price
                percent = (diff / old_price) * 100
                
                if diff > 0:
                    change_text = f" 📈 +{diff:.2f} CNY (+{percent:.1f}%)"
                elif diff < 0:
                    change_text = f" 📉 {diff:.2f} CNY ({percent:.1f}%)"
                else:
                    change_text = " ➡️ без изменений"
            
            # Форматируем цены
            price_text = currency_converter.format_price(prices) if prices else f"{current_price:.2f} CNY"
            
            response_text += (
                f"<b>{item.market_hash_name}</b>\n"
                f"{price_text}\n"
                f"{change_text}\n"
                f"🔗 goods_id: {item.goods_id}\n\n"
            )
        else:
            response_text += (
                f"<b>{item.market_hash_name}</b>\n"
                f"❌ Не удалось получить цену\n"
                f"🔗 goods_id: {item.goods_id}\n\n"
            )
    
    await status_msg.delete()
    await message.answer(response_text, reply_markup=get_back_to_menu_keyboard())


# === Обработчики callback кнопок ===

@router.callback_query(F.data == "back_to_menu")
async def callback_back_to_menu(callback: CallbackQuery):
    """Возврат в главное меню"""
    await callback.message.edit_text(
        "🏠 <b>Главное меню</b>\n\n"
        "Выберите действие:",
        reply_markup=get_main_menu_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "add_item")
async def callback_add_item(callback: CallbackQuery, state: FSMContext):
    """Начало процесса добавления товара"""
    await callback.message.edit_text(
        "➕ <b>Добавление товара</b>\n\n"
        "Отправьте goods_id товара с сайта Buff.163.com\n\n"
        "📌 Как найти goods_id:\n"
        "1. Откройте страницу товара на buff.163.com\n"
        "2. В адресной строке найдите число после /goods/\n"
        "   Пример: https://buff.163.com/goods/<b>43012</b>\n\n"
        "Отправьте это число:",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(AddItemStates.waiting_for_goods_id)
    await callback.answer()


@router.callback_query(F.data == "list_items")
async def callback_list_items(callback: CallbackQuery):
    """Показать список отслеживаемых товаров"""
    user_id = callback.from_user.id
    items = await db.get_user_items(user_id)
    
    if not items:
        await callback.message.edit_text(
            "📭 У вас нет отслеживаемых товаров.\n\n"
            "Нажмите '➕ Добавить товар' для начала отслеживания.",
            reply_markup=get_main_menu_keyboard()
        )
    else:
        await callback.message.edit_text(
            f"📋 <b>Ваши отслеживаемые товары ({len(items)}):</b>\n\n"
            "Нажмите на товар для просмотра деталей:",
            reply_markup=get_tracked_items_keyboard(items)
        )
    
    await callback.answer()


@router.callback_query(F.data == "current_prices")
async def callback_current_prices(callback: CallbackQuery):
    """Показать актуальные цены"""
    user_id = callback.from_user.id
    items = await db.get_user_items(user_id)
    
    if not items:
        await callback.message.edit_text(
            "📭 У вас нет отслеживаемых товаров.",
            reply_markup=get_main_menu_keyboard()
        )
        await callback.answer()
        return
    
    await callback.answer("🔄 Загружаю цены...")
    
    response_text = "💰 <b>Актуальные цены:</b>\n\n"
    
    for item in items:
        price_data = await buff_client.get_item_price(item.goods_id)
        
        if price_data:
            current_price = price_data["min_price"]
            prices = price_data.get("prices", {})
            old_price = item.last_price
            
            change_text = ""
            if old_price:
                diff = current_price - old_price
                percent = (diff / old_price) * 100
                
                if diff > 0:
                    change_text = f" 📈 +{diff:.2f} CNY (+{percent:.1f}%)"
                elif diff < 0:
                    change_text = f" 📉 {diff:.2f} CNY ({percent:.1f}%)"
                else:
                    change_text = " ➡️"
            
            # Форматируем цены
            price_text = currency_converter.format_price(prices) if prices else f"{current_price:.2f} CNY"
            
            response_text += (
                f"<b>{item.market_hash_name}</b>\n"
                f"{price_text}\n"
                f"{change_text}\n\n"
            )
        else:
            response_text += (
                f"<b>{item.market_hash_name}</b>\n"
                f"❌ Ошибка загрузки\n\n"
            )
    
    try:
        await callback.message.edit_text(
            response_text, 
            reply_markup=get_back_to_menu_keyboard()
        )
    except Exception as e:
        # Игнорируем ошибку "message is not modified"
        if "message is not modified" not in str(e):
            raise


@router.callback_query(F.data == "help")
async def callback_help(callback: CallbackQuery):
    """Показать справку"""
    help_text = (
        "ℹ️ <b>Помощь по использованию бота</b>\n\n"
        "<b>Как добавить товар:</b>\n"
        "1. Нажмите '➕ Добавить товар'\n"
        "2. Найдите товар на buff.163.com\n"
        "3. В URL товара найдите goods_id\n"
        "   Пример: https://buff.163.com/goods/<b>43012</b>\n"
        "4. Отправьте этот номер боту\n\n"
        "<b>Уведомления:</b>\n"
        f"Бот проверяет цены каждые {config.CHECK_INTERVAL} минут "
        "и уведомляет об изменениях."
    )
    
    await callback.message.edit_text(
        help_text,
        reply_markup=get_back_to_menu_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("item_info_"))
async def callback_item_info(callback: CallbackQuery):
    """Показать информацию о товаре"""
    item_id = int(callback.data.split("_")[2])
    user_id = callback.from_user.id
    
    items = await db.get_user_items(user_id)
    item = next((i for i in items if i.id == item_id), None)
    
    if not item:
        await callback.answer("❌ Товар не найден", show_alert=True)
        return
    
    # Получаем актуальную цену
    price_data = await buff_client.get_item_price(item.goods_id)
    
    if price_data:
        current_price = price_data["min_price"]
        prices = price_data.get("prices", {})
        old_price = item.last_price
        
        change_text = ""
        if old_price:
            diff = current_price - old_price
            percent = (diff / old_price) * 100
            
            if diff > 0:
                change_text = f"\n📈 Изменение: +{diff:.2f} CNY (+{percent:.1f}%)"
            elif diff < 0:
                change_text = f"\n📉 Изменение: {diff:.2f} CNY ({percent:.1f}%)"
            else:
                change_text = "\n➡️ Цена не изменилась"
        
        # Форматируем цены
        price_text = currency_converter.format_price(prices) if prices else f"💵 {current_price:.2f} CNY"
        
        last_price_text = f"💾 Последняя известная: {old_price:.2f} CNY\n" if old_price else ""
        
        info_text = (
            f"📦 <b>{item.market_hash_name}</b>\n\n"
            f"💰 <b>Текущая цена:</b>\n{price_text}\n"
            f"{change_text}\n\n"
            f"{last_price_text}"
            f"🔗 goods_id: {item.goods_id}\n"
            f"📅 Добавлен: {item.created_at.strftime('%d.%m.%Y %H:%M')}"
        )
    else:
        info_text = (
            f"📦 <b>{item.market_hash_name}</b>\n\n"
            f"🔗 goods_id: {item.goods_id}\n"
            f"❌ Не удалось загрузить актуальную цену\n"
            f"💾 Последняя известная: {item.last_price:.2f} CNY\n" if item.last_price else ""
            f"📅 Добавлен: {item.created_at.strftime('%d.%m.%Y %H:%M')}"
        )
    
    await callback.message.edit_text(
        info_text,
        reply_markup=get_item_actions_keyboard(item_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("refresh_price_"))
async def callback_refresh_price(callback: CallbackQuery):
    """Обновить цену товара"""
    item_id = int(callback.data.split("_")[2])
    user_id = callback.from_user.id
    
    items = await db.get_user_items(user_id)
    item = next((i for i in items if i.id == item_id), None)
    
    if not item:
        await callback.answer("❌ Товар не найден", show_alert=True)
        return
    
    await callback.answer("🔄 Обновляю...")
    
    # Получаем актуальную цену
    price_data = await buff_client.get_item_price(item.goods_id)
    
    if price_data:
        current_price = price_data["min_price"]
        prices = price_data.get("prices", {})
        
        # Обновляем в БД
        await db.update_item_price(item_id, current_price)
        await db.add_price_history(item_id, current_price)
        
        # Форматируем цены
        price_text = currency_converter.format_price(prices) if prices else f"💵 {current_price:.2f} CNY"
        
        await callback.message.answer(
            f"✅ Цена обновлена!\n\n"
            f"📦 {item.market_hash_name}\n"
            f"{price_text}"
        )
    else:
        await callback.message.answer(
            f"❌ Не удалось обновить цену для {item.market_hash_name}"
        )


@router.callback_query(F.data.startswith("remove_item_"))
async def callback_remove_item(callback: CallbackQuery):
    """Запрос подтверждения удаления товара"""
    item_id = int(callback.data.split("_")[2])
    user_id = callback.from_user.id
    
    items = await db.get_user_items(user_id)
    item = next((i for i in items if i.id == item_id), None)
    
    if not item:
        await callback.answer("❌ Товар не найден", show_alert=True)
        return
    
    await callback.message.edit_text(
        f"🗑 <b>Удалить товар из отслеживания?</b>\n\n"
        f"📦 {item.market_hash_name}\n"
        f"🔗 goods_id: {item.goods_id}\n\n"
        f"⚠️ Это действие нельзя отменить.",
        reply_markup=get_confirm_delete_keyboard(item_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_delete_"))
async def callback_confirm_delete(callback: CallbackQuery):
    """Подтверждение удаления товара"""
    item_id = int(callback.data.split("_")[2])
    user_id = callback.from_user.id
    
    items = await db.get_user_items(user_id)
    item = next((i for i in items if i.id == item_id), None)
    
    if not item:
        await callback.answer("❌ Товар не найден", show_alert=True)
        return
    
    item_name = item.market_hash_name
    
    # Удаляем товар
    success = await db.remove_user_subscription(user_id, item_id)
    
    if success:
        await callback.message.edit_text(
            f"✅ Товар удален из отслеживания\n\n"
            f"📦 {item_name}",
            reply_markup=get_back_to_menu_keyboard()
        )
        await callback.answer("✅ Товар удален")
    else:
        await callback.answer("❌ Ошибка удаления", show_alert=True)


# === Обработчик добавления товара через FSM ===

@router.message(AddItemStates.waiting_for_goods_id)
async def process_goods_id(message: Message, state: FSMContext):
    """Обработка введенного goods_id"""
    user_id = message.from_user.id
    
    # Проверяем, что это число
    if not message.text.isdigit():
        await message.answer(
            "❌ Пожалуйста, отправьте корректный goods_id (только цифры)\n\n"
            "Пример: 43012",
            reply_markup=get_cancel_keyboard()
        )
        return
    
    goods_id = int(message.text)
    
    # Проверяем, не подписан ли уже пользователь на этот товар
    is_subscribed = await db.is_user_subscribed(user_id, goods_id)
    if is_subscribed:
        await message.answer(
            "⚠️ Вы уже подписаны на этот товар!",
            reply_markup=get_main_menu_keyboard()
        )
        await state.clear()
        return
    
    status_msg = await message.answer("🔄 Проверяю товар...")
    
    # Получаем информацию о товаре
    price_data = await buff_client.get_item_price(goods_id)
    
    if not price_data:
        await status_msg.edit_text(
            f"❌ Товар с goods_id {goods_id} не найден.\n\n"
            "Проверьте правильность введенного ID.",
            reply_markup=get_main_menu_keyboard()
        )
        await state.clear()
        return
    
    # Добавляем товар в БД
    market_hash_name = price_data["market_hash_name"]
    min_price = price_data["min_price"]
    prices = price_data.get("prices", {})
    
    await db.add_user_subscription(
        user_id=user_id,
        goods_id=goods_id,
        market_hash_name=market_hash_name,
        initial_price=min_price
    )
    
    # Добавляем первую запись в историю
    item = await db.get_item_by_goods_id(goods_id)
    if item:
        await db.add_price_history(item.id, min_price)
    
    # Форматируем цены
    price_text = currency_converter.format_price(prices) if prices else f"💵 {min_price:.2f} CNY"
    
    # Получаем настройки пользователя
    user = await db.get_user(user_id)
    interval_text = f"{user.check_interval} минут" if user else f"{config.CHECK_INTERVAL} минут"
    
    await status_msg.edit_text(
        f"✅ <b>Товар добавлен в отслеживание!</b>\n\n"
        f"📦 {market_hash_name}\n"
        f"🔗 goods_id: {goods_id}\n\n"
        f"💰 <b>Текущая цена:</b>\n{price_text}\n\n"
        f"🔔 Я буду уведомлять вас об изменении цены каждые {interval_text}.",
        reply_markup=get_main_menu_keyboard()
    )
    
    await state.clear()


# === Обработчики настроек ===

@router.callback_query(F.data == "settings")
async def callback_settings(callback: CallbackQuery):
    """Показать меню настроек"""
    user_id = callback.from_user.id
    user = await db.get_user(user_id)
    
    if not user:
        await callback.answer("❌ Ошибка получения настроек", show_alert=True)
        return
    
    # Форматируем интервал
    interval = user.check_interval
    if interval < 60:
        interval_text = f"{interval} минут"
    elif interval == 60:
        interval_text = "1 час"
    elif interval < 1440:
        hours = interval // 60
        interval_text = f"{hours} {'час' if hours == 1 else 'часа' if hours < 5 else 'часов'}"
    else:
        interval_text = "24 часа"
    
    notifications_text = "🔔 Включены" if user.notifications_enabled else "🔕 Отключены"
    
    settings_text = (
        "⚙️ <b>Настройки</b>\n\n"
        f"⏱ <b>Интервал проверки:</b> {interval_text}\n"
        f"🔔 <b>Уведомления:</b> {notifications_text}\n\n"
        "Выберите, что хотите изменить:"
    )
    
    await callback.message.edit_text(
        settings_text,
        reply_markup=get_settings_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "settings_interval")
async def callback_settings_interval(callback: CallbackQuery):
    """Показать меню выбора интервала"""
    user_id = callback.from_user.id
    user = await db.get_user(user_id)
    
    if not user:
        await callback.answer("❌ Ошибка получения настроек", show_alert=True)
        return
    
    interval_text = (
        "⏱ <b>Выбор интервала проверки</b>\n\n"
        f"Текущий интервал: <b>{user.check_interval} минут</b>\n\n"
        "Выберите новый интервал (от 15 минут до 24 часов):"
    )
    
    await callback.message.edit_text(
        interval_text,
        reply_markup=get_interval_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("set_interval_"))
async def callback_set_interval(callback: CallbackQuery):
    """Установить новый интервал проверки"""
    user_id = callback.from_user.id
    interval = int(callback.data.split("_")[2])
    
    try:
        await db.update_user_settings(user_id, check_interval=interval)
        
        # Форматируем для отображения
        if interval < 60:
            interval_text = f"{interval} минут"
        elif interval == 60:
            interval_text = "1 час"
        elif interval < 1440:
            hours = interval // 60
            interval_text = f"{hours} {'час' if hours == 1 else 'часа' if hours < 5 else 'часов'}"
        else:
            interval_text = "24 часа"
        
        await callback.answer(f"✅ Интервал установлен: {interval_text}", show_alert=True)
        
        # Возвращаемся в меню настроек
        user = await db.get_user(user_id)
        notifications_text = "🔔 Включены" if user.notifications_enabled else "🔕 Отключены"
        
        settings_text = (
            "⚙️ <b>Настройки</b>\n\n"
            f"⏱ <b>Интервал проверки:</b> {interval_text}\n"
            f"🔔 <b>Уведомления:</b> {notifications_text}\n\n"
            "Выберите, что хотите изменить:"
        )
        
        await callback.message.edit_text(
            settings_text,
            reply_markup=get_settings_keyboard()
        )
    
    except ValueError as e:
        await callback.answer(f"❌ {str(e)}", show_alert=True)


@router.callback_query(F.data == "settings_notifications")
async def callback_settings_notifications(callback: CallbackQuery):
    """Показать меню управления уведомлениями"""
    user_id = callback.from_user.id
    user = await db.get_user(user_id)
    
    if not user:
        await callback.answer("❌ Ошибка получения настроек", show_alert=True)
        return
    
    status_text = "включены" if user.notifications_enabled else "отключены"
    
    notifications_text = (
        "🔔 <b>Управление уведомлениями</b>\n\n"
        f"Статус: <b>{status_text}</b>\n\n"
        "Когда уведомления отключены, бот не будет проверять цены "
        "и отправлять уведомления об изменениях.\n\n"
        "Вы можете включить/отключить уведомления:"
    )
    
    await callback.message.edit_text(
        notifications_text,
        reply_markup=get_notifications_keyboard(user.notifications_enabled)
    )
    await callback.answer()


@router.callback_query(F.data == "toggle_notifications")
async def callback_toggle_notifications(callback: CallbackQuery):
    """Переключить уведомления"""
    user_id = callback.from_user.id
    user = await db.get_user(user_id)
    
    if not user:
        await callback.answer("❌ Ошибка получения настроек", show_alert=True)
        return
    
    # Переключаем
    new_status = not user.notifications_enabled
    await db.update_user_settings(user_id, notifications_enabled=new_status)
    
    status_text = "включены" if new_status else "отключены"
    await callback.answer(f"✅ Уведомления {status_text}", show_alert=True)
    
    # Обновляем сообщение
    notifications_text = (
        "🔔 <b>Управление уведомлениями</b>\n\n"
        f"Статус: <b>{status_text}</b>\n\n"
        "Когда уведомления отключены, бот не будет проверять цены "
        "и отправлять уведомления об изменениях.\n\n"
        "Вы можете включить/отключить уведомления:"
    )
    
    await callback.message.edit_text(
        notifications_text,
        reply_markup=get_notifications_keyboard(new_status)
    )

