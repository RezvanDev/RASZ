#!/usr/bin/env bash
set -e

echo "==============================================="
echo "🚀 Развертывание Personal AI Finance Bot (Узбекистан)"
echo "==============================================="

# 1. Проверка наличия .env файла
if [ ! -f .env ]; then
    echo "⚠️ Файл .env не найден! Создаю из .env.example..."
    cp .env.example .env
    echo "❗ Пожалуйста, откройте .env и укажите BOT_TOKEN, ADMIN_IDS и LLM_API_KEY."
    exit 1
fi

# 2. Создание директории для постоянной базы данных SQLite
mkdir -p data
chmod 777 data

# 3. Проверка установленного Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Ошибка: Docker не установлен на сервере. Установите Docker и повторите запуск."
    exit 1
fi

# 4. Сборка и запуск контейнера в фоне
echo "📦 Сборка и запуск Docker контейнера..."
if docker compose version &> /dev/null; then
    docker compose up -d --build
else
    docker-compose up -d --build
fi

echo ""
echo "✅ Бот успешно запущен в фоновом режиме!"
echo "База данных SQLite сохраняется в папке: ./data/finance.db"
echo ""
echo "Для просмотра логов выполните:"
echo "  docker compose logs -f"
echo "Для остановки бота:"
echo "  docker compose down"

