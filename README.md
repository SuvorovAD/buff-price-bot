# 🤖 Buff Price Bot

Telegram бот для отслеживания цен на скины CS2 с [Buff.163.com](https://buff.163.com)

## ✨ Возможности

- 🔍 Отслеживание цен на любые товары CS2
- 💱 Автоматическая конвертация CNY → USD → RUB
- 🔔 Уведомления об изменении цен
- ⏱ **Персональный интервал проверки** (от 15 минут до 24 часов)
- 🔕 **Отключение уведомлений** для каждого пользователя
- 📊 История цен
- 👤 Персональные списки для каждого пользователя

## 🚀 Quick Start

### 🐳 С Docker (рекомендуется)

```bash
# 1. Клонируйте репозиторий с подмодулями
git clone <repository-url>
cd buff-price-bot

# 2. Убедитесь, что папка buff163-unofficial-api на месте
# (она должна быть в корне проекта)

# 3. Настройте .env
cp .env.example .env
nano .env  # Заполните BOT_TOKEN, ALLOWED_USER_IDS, BUFF_SESSION_COOKIE

# 4. Соберите и запустите
docker-compose up --build -d

# 5. Проверьте логи
docker-compose logs -f
```

### 🐍 Без Docker

```bash
# 1. Клонируйте репозиторий
git clone <repository-url>
cd buff-price-bot

# 2. Создайте виртуальное окружение
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate     # Windows

# 3. Установите зависимости
pip install -r requirements.txt
pip install -e ./buff163-unofficial-api

# 4. Настройте .env
cp .env.example .env
nano .env  # Заполните переменные

# 5. Запустите
python -m bot.main
```

## ⚙️ Конфигурация (.env)

```env
# Telegram Bot Token (получить у @BotFather)
BOT_TOKEN=your_bot_token_here

# User IDs с доступом (через запятую)
ALLOWED_USER_IDS=123456789,987654321

# Cookie с buff.163.com (одна строка)
BUFF_SESSION_COOKIE=Device-Id=_; session=_; csrf_token=_

# Интервал проверки цен (минуты)
CHECK_INTERVAL=60
```

### Как получить данные:

**User ID:**
- Напишите [@userinfobot](https://t.me/userinfobot)

**Bot Token:**
- Создайте бота у [@BotFather](https://t.me/BotFather)

**Buff Cookie:**
1. Войдите на [buff.163.com](https://buff.163.com)
2. Откройте DevTools (F12) → Application/Storage → Cookies
3. Скопируйте все cookies в формат: `key=value; key2=value2`

## 📱 Использование

### Команды:
- `/start` - Главное меню
- `/list` - Список товаров
- `/now` - Актуальные цены
- `/help` - Справка

### Настройки:
- ⏱ **Интервал проверки:** от 15 минут до 24 часов
- 🔔 **Уведомления:** включить/отключить автоматические уведомления
- Каждый пользователь настраивает свой интервал независимо

### Добавить товар:
1. Найдите товар на buff.163.com
2. Скопируйте `goods_id` из URL: `https://buff.163.com/goods/43012` → `43012`
3. Нажмите "➕ Добавить товар" и отправьте ID

## 🛠 Управление

### Docker:
```bash
docker-compose up -d      # Запуск
docker-compose down       # Остановка
docker-compose restart    # Перезапуск
docker-compose logs -f    # Логи
```

### Python:
```bash
python -m bot.main        # Запуск
```

## 🗂 Структура

```
buff-price-bot/
├── bot/                  # Код бота
│   ├── main.py          # Точка входа
│   ├── handlers.py      # Обработчики
│   ├── keyboards.py     # Клавиатуры
│   └── scheduler.py     # Проверка цен
├── api/                  # API клиенты
│   ├── buff_api.py      # Buff.163.com
│   └── currency_converter.py  # Конвертация валют
├── database/             # База данных
│   ├── models.py        # Модели (нормализованная структура)
│   └── db.py            # CRUD операции
├── buff163-unofficial-api/  # ⚠️ Библиотека Buff API (обязательна для Docker!)
│   ├── buff163_unofficial_api/
│   ├── setup.py
│   └── ...
├── config.py            # Конфигурация
├── init_db.py           # Инициализация БД
├── migrate_db.py        # Миграция старой БД в новую
├── .env                 # Переменные окружения
├── requirements.txt     # Зависимости
├── Dockerfile           # Docker образ с локальной установкой библиотеки
└── docker-compose.yml
```

> **⚠️ Важно:** Папка `buff163-unofficial-api` должна находиться в корне проекта! Docker устанавливает библиотеку из этой локальной папки, а не из PyPI.

## 🗄 База данных

**Нормализованная структура:**

- `users` - пользователи (с персональными настройками: интервал, уведомления)
- `items` - товары (один товар = одна запись)
- `user_items` - подписки (many-to-many связь)
- `price_history` - история цен (привязана к товару)

**Преимущества:**
- ✅ Один товар = один запрос к API
- ✅ Общая история цен для всех пользователей
- ✅ Меньше дублирования данных
- ✅ Персональный интервал для каждого пользователя

## 🔧 Технологии

- [aiogram 3.x](https://docs.aiogram.dev/) - Telegram Bot API
- [SQLAlchemy](https://www.sqlalchemy.org/) - ORM
- [APScheduler](https://apscheduler.readthedocs.io/) - Планировщик
- [buff163_unofficial_api](https://github.com/user/repo) - Buff API (локальная версия)
- [exchangerate-api.com](https://exchangerate-api.com) - Курсы валют

## 📝 Логи

**Консоль:** INFO и выше (все операции)  
**Файл `bot.log`:** WARNING и выше (только ошибки и предупреждения)

```bash
# Просмотр логов
tail -f bot.log              # Python
docker-compose logs -f       # Docker
```

## 🐛 Troubleshooting

**Бот не запускается:**
- Проверьте `BOT_TOKEN` в `.env`
- Убедитесь, что установлены все зависимости
- Смотрите логи в консоли

**"no such table: users":**
```bash
python init_db.py  # Инициализация БД вручную
```

**Миграция со старой версии:**
```bash
python migrate_db.py  # Автоматическая миграция данных (нормализация БД)
python migrate_user_settings.py  # Добавление настроек пользователя (если нужно)
```

**Не находит товар:**
- Проверьте `BUFF_SESSION_COOKIE` (может истечь)
- Убедитесь, что установлена локальная версия `buff163_unofficial_api`

**Не приходят уведомления:**
- Добавьте товары на отслеживание
- Проверьте настройки (уведомления должны быть включены)
- Подождите согласно вашему интервалу проверки
- Проверьте логи: `docker-compose logs -f` или `bot.log`

**Курсы валют не обновляются:**
- Курсы обновляются автоматически каждый день в 00:00
- При старте бота курсы загружаются сразу
- При недоступности API используются дефолтные курсы

**Docker: "No module named 'buff163_unofficial_api'":**
```bash
# Убедитесь, что папка buff163-unofficial-api существует
ls -la buff163-unofficial-api/

# Пересоберите образ
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

> 📘 Подробнее о Docker-сборке: [DOCKER_SETUP.md](DOCKER_SETUP.md)

## 🤝 Contributing

### Разработка:

```bash
# 1. Fork и clone
git clone https://github.com/your-username/buff-price-bot
cd buff-price-bot

# 2. Создайте ветку
git checkout -b feature/your-feature

# 3. Установите зависимости
pip install -r requirements.txt
pip install -e ./buff163-unofficial-api

# 4. Внесите изменения
# ...

# 5. Запустите тесты (если есть)
python test_buff_api.py

# 6. Commit и push
git add .
git commit -m "Add: your feature"
git push origin feature/your-feature

# 7. Создайте Pull Request
```

### Структура кода:

- **bot/handlers.py** - обработчики команд и callback
- **bot/keyboards.py** - клавиатуры
- **bot/scheduler.py** - логика проверки цен
- **api/buff_api.py** - работа с Buff API
- **api/currency_converter.py** - конвертация валют
- **database/** - модели и работа с БД

### Добавление новой функции:

1. Создайте обработчик в `bot/handlers.py`
2. Добавьте клавиатуру в `bot/keyboards.py` (если нужно)
3. Зарегистрируйте роутер в `bot/main.py`
4. Обновите документацию в README.md

### Code Style:

- Python 3.10+
- Async/await для всех IO операций
- Type hints где возможно
- Docstrings для функций
- Логирование через `logging`

## ⚠️ Важно

- Бот доступен только пользователям из `ALLOWED_USER_IDS`
- Используется локальная версия `buff163_unofficial_api` (не PyPI)
- Курсы валют обновляются каждый час
- История цен очищается раз в 7 дней
- Cookie действуют ограниченное время

## 📄 Лицензия

MIT License

---

**Приятного использования! 🎮**
