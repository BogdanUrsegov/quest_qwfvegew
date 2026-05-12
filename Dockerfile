# Используем официальный легковесный образ Python
FROM python:3.10-slim

# Устанавливаем рабочую директорию внутри контейнера
WORKDIR /app

# Копируем только зависимости — это ускоряет повторную сборку
COPY bot/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Копируем исходный код бота
COPY bot/ ./bot/

# Создаём папку для возможных данных (на случай, если понадобится временный файл)
RUN mkdir -p /app/data

# Порт, который слушает бот (должен совпадать с docker-compose)
EXPOSE 8000

# Запуск бота
CMD ["python", "-m", "bot.main"]