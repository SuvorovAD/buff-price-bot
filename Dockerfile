# Используем официальный образ Python
FROM python:3.11-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Устанавливаем переменные окружения
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Копируем файл с зависимостями
COPY requirements.txt .

# Устанавливаем git для клонирования submodule
RUN apt-get update && apt-get install -y git && apt-get clean && rm -rf /var/lib/apt/lists/*

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Клонируем и устанавливаем buff163-unofficial-api из репозитория
RUN git clone https://github.com/markzhdan/buff163-unofficial-api.git /tmp/buff163-unofficial-api && \
    pip install --no-cache-dir /tmp/buff163-unofficial-api && \
    rm -rf /tmp/buff163-unofficial-api

# Копируем весь проект
COPY . .

# Создаем директорию для базы данных
RUN mkdir -p /app/data

# Создаем пользователя для запуска приложения (безопасность)
RUN useradd -m -u 1000 botuser && \
    chown -R botuser:botuser /app

# Переключаемся на созданного пользователя
USER botuser

# Команда запуска бота
CMD ["python", "-m", "bot.main"]

