# 🎨 ArtGenius AI - Генератор изображений и видео в Telegram

Бот создает уникальные изображения и видео по текстовому описанию с помощью нейросетей Stable Diffusion 3 и Stable Video Diffusion.

## 🌟 Особенности
- **Генерация изображений** по текстовому описанию
- **Создание видео** на основе изображений с описанием движения
- **Улучшение качества** до 4K
- **8 стилей генерации**: фотореализм, аниме, цифровое искусство и др.
- Интеграция с API Stability.ai
- Асинхронная обработка запросов
- Очередь задач для длительных операций
- Поддержка форматов PNG, MP4

## 🛠 Технологический стек
- Python 3.10+
- Aiogram (асинхронный Telegram API)
- Stability.ai API (Stable Diffusion 3, Stable Video Diffusion, ESRGAN)
- Asyncio для фоновых задач
- UUID для управления файлами

## ⚙️ Установка
1. Клонируйте репозиторий:
```bash
git clone https://github.com/banhanman/ArtGenius-AI.git
cd ArtGenius-AI
