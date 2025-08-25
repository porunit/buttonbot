# syntax=docker/dockerfile:1
FROM python:3.11-slim

# Быстрый и «шумящий» лог в stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_NO_CACHE_DIR=on \
    TZ=Europe/Tallinn

# Опционально ставим tzdata (для корректного TZ)
RUN apt-get update \
 && apt-get install -y --no-install-recommends tzdata \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 1) Сначала зависимости — лучше кэшируются
#   Если у тебя нет requirements.txt — см. вариант ниже
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 2) Затем код
COPY . .

# Безопасный non-root пользователь
RUN useradd -m appuser && chown -R appuser /app
USER appuser

# Боту не нужно EXPOSE — он работает исходящими запросами
CMD ["python", "bot.py"]
