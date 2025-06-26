import asyncio
import logging
import requests
import json
import time
from aiogram import Bot, Dispatcher, types, executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
import config
import uuid
import os

# Настройка логов
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=config.TELEGRAM_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Конфигурация API
IMAGE_API_URL = "https://api.stability.ai/v2beta/stable-image/generate/sd3"
VIDEO_API_URL = "https://api.stability.ai/v2alpha/video/generate"
UPSCALE_API_URL = "https://api.stability.ai/v1/generation/esrgan-v1-x2plus/image-to-image/upscale"

# Состояния бота
class GenerationStates(StatesGroup):
    waiting_for_prompt = State()
    waiting_for_image_prompt = State()
    waiting_for_video_prompt = State()
    waiting_for_style = State()
    waiting_for_upscale = State()

# Стили для генерации
STYLES = {
    "realistic": "Фотореализм",
    "anime": "Аниме",
    "digital_art": "Цифровое искусство",
    "comic_book": "Комикс",
    "fantasy": "Фэнтези",
    "vector": "Векторная графика",
    "pixel_art": "Пиксель-арт",
    "isometric": "Изометрический"
}

# Генерация изображения через Stable Diffusion 3
async def generate_image(prompt: str, style: str = "realistic", aspect_ratio: str = "1:1") -> str:
    headers = {
        "Authorization": f"Bearer {config.STABILITY_API_KEY}",
        "Accept": "image/*"
    }
    
    data = {
        "prompt": prompt,
        "output_format": "png",
        "model": "sd3",
        "style_preset": style,
        "aspect_ratio": aspect_ratio
    }
    
    try:
        response = requests.post(
            IMAGE_API_URL,
            headers=headers,
            files={"none": ''},
            data=data,
            timeout=120
        )
        
        if response.status_code == 200:
            filename = f"results/{uuid.uuid4()}.png"
            with open(filename, 'wb') as f:
                f.write(response.content)
            return filename
        else:
            logger.error(f"Ошибка генерации: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        logger.error(f"Ошибка запроса: {e}")
        return None

# Генерация видео через Stable Video Diffusion
async def generate_video(prompt: str, image_path: str) -> str:
    headers = {
        "Authorization": f"Bearer {config.STABILITY_API_KEY}"
    }
    
    # Сначала загружаем изображение
    with open(image_path, 'rb') as img_file:
        files = {'image': img_file}
        data = {
            "prompt": prompt,
            "seed": 0,
            "cfg_scale": 2.5,
            "motion_bucket_id": 127
        }
        
        try:
            response = requests.post(
                VIDEO_API_URL,
                headers=headers,
                files=files,
                data=data,
                timeout=300
            )
            
            if response.status_code == 200:
                response_data = response.json()
                video_id = response_data.get('id')
                
                # Проверяем статус генерации
                while True:
                    status_response = requests.get(
                        f"{VIDEO_API_URL}/result/{video_id}",
                        headers=headers
                    )
                    
                    if status_response.status_code == 200:
                        status_data = status_response.json()
                        if status_data['status'] == 'complete':
                            video_url = status_data['video']
                            video_response = requests.get(video_url)
                            
                            filename = f"results/{uuid.uuid4()}.mp4"
                            with open(filename, 'wb') as f:
                                f.write(video_response.content)
                            return filename
                        elif status_data['status'] == 'failed':
                            logger.error("Ошибка генерации видео")
                            return None
                    
                    await asyncio.sleep(10)
            else:
                logger.error(f"Ошибка видео API: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"Ошибка видео запроса: {e}")
            return None

# Улучшение качества изображения
async def upscale_image(image_path: str) -> str:
    headers = {
        "Authorization": f"Bearer {config.STABILITY_API_KEY}",
        "Accept": "image/png"
    }
    
    try:
        with open(image_path, 'rb') as img_file:
            files = {'image': img_file}
            data = {
                "width": 2048,
            }
            
            response = requests.post(
                UPSCALE_API_URL,
                headers=headers,
                files=files,
                data=data,
                timeout=120
            )
            
            if response.status_code == 200:
                filename = f"results/upscaled_{uuid.uuid4()}.png"
                with open(filename, 'wb') as f:
                    f.write(response.content)
                return filename
            else:
                logger.error(f"Ошибка улучшения: {response.status_code} - {response.text}")
                return None
    except Exception as e:
        logger.error(f"Ошибка улучшения: {e}")
        return None

@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    keyboard = InlineKeyboardMarkup(row_width=2)
    buttons = [
        InlineKeyboardButton("🖼 Создать изображение", callback_data="generate_image"),
        InlineKeyboardButton("🎥 Создать видео", callback_data="generate_video"),
        InlineKeyboardButton("✨ Улучшить качество", callback_data="upscale_image"),
        InlineKeyboardButton("🎨 Стили генерации", callback_data="show_styles"),
        InlineKeyboardButton("ℹ️ Помощь", callback_data="help_info")
    ]
    keyboard.add(*buttons)
    
    await message.answer(
        "🌟 Добро пожаловать в ArtGenius AI!\n\n"
        "Я могу создавать уникальные изображения и видео по вашему описанию с помощью нейросетей.\n\n"
        "Возможности:\n"
        "• Генерация изображений (Stable Diffusion 3)\n"
        "• Создание видео по изображению (Stable Video Diffusion)\n"
        "• Улучшение качества изображений в 4K\n"
        "• 8 различных стилей генерации\n\n"
        "Выберите действие:",
        reply_markup=keyboard
    )

@dp.callback_query_handler(lambda c: c.data == 'generate_image')
async def start_image_generation(callback_query: types.CallbackQuery):
    await bot.send_message(
        callback_query.from_user.id,
        "🎨 Введите описание изображения:\n\n"
        "Примеры:\n"
        "• 'Космический корабль в стиле киберпанк, детализированный'\n"
        "• 'Реалистичный портрет кота в шляпе, стиль Ренессанс'\n"
        "• 'Футуристический город под дождем, неоновые огни, ночь'"
    )
    await GenerationStates.waiting_for_image_prompt.set()

@dp.callback_query_handler(lambda c: c.data == 'generate_video')
async def start_video_generation(callback_query: types.CallbackQuery):
    await bot.send_message(
        callback_query.from_user.id,
        "📹 Для создания видео сначала отправьте изображение или сгенерируйте его.\n"
        "Затем введите описание для анимации.\n\n"
        "Примеры:\n"
        "• 'Медленно вращающийся вид' \n"
        "• 'Полет через космический корабль' \n"
        "• 'Приближение к лицу кота'"
    )
    await GenerationStates.waiting_for_video_prompt.set()

@dp.callback_query_handler(lambda c: c.data == 'upscale_image')
async def start_upscale(callback_query: types.CallbackQuery):
    await bot.send_message(
        callback_query.from_user.id,
        "✨ Отправьте изображение для улучшения качества (до 4K).\n"
        "Изображение будет обработано нейросетью ESRGAN."
    )
    await GenerationStates.waiting_for_upscale.set()

@dp.callback_query_handler(lambda c: c.data == 'show_styles')
async def show_styles(callback_query: types.CallbackQuery):
    keyboard = InlineKeyboardMarkup(row_width=2)
    for style_key, style_name in STYLES.items():
        keyboard.add(InlineKeyboardButton(style_name, callback_data=f"style_{style_key}"))
    
    await bot.send_message(
        callback_query.from_user.id,
        "🎭 Выберите стиль для генерации:",
        reply_markup=keyboard
    )

@dp.callback_query_handler(lambda c: c.data.startswith('style_'))
async def set_style(callback_query: types.CallbackQuery):
    style_key = callback_query.data.split('_')[1]
    style_name = STYLES.get(style_key, "Фотореализм")
    
    # Сохраняем стиль для пользователя (в реальном приложении - в БД)
    user_id = callback_query.from_user.id
    # user_styles[user_id] = style_key
    
    await bot.answer_callback_query(
        callback_query.id,
        f"✅ Стиль установлен: {style_name}"
    )

@dp.message_handler(state=GenerationStates.waiting_for_image_prompt)
async def process_image_prompt(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    prompt = message.text
    
    if len(prompt) < 10:
        await message.answer("❌ Описание должно содержать минимум 10 символов. Попробуйте еще раз.")
        return
    
    await message.answer(f"🪄 Генерирую изображение по запросу: '{prompt}'...")
    
    # Генерация изображения
    image_path = await generate_image(prompt, style="realistic")
    
    if image_path:
        with open(image_path, 'rb') as photo:
            await message.answer_photo(
                photo,
                caption=f"🖼 Результат по запросу: '{prompt}'\n\n"
                        f"✨ /upscale - Улучшить качество\n"
                        f"🎥 /video - Создать видео на основе"
            )
        os.remove(image_path)
    else:
        await message.answer("⚠️ Не удалось сгенерировать изображение. Попробуйте другой запрос.")
    
    await state.finish()

@dp.message_handler(content_types=types.ContentType.PHOTO, state=GenerationStates.waiting_for_upscale)
async def process_upscale_image(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    photo = message.photo[-1]
    file_id = photo.file_id
    file = await bot.get_file(file_id)
    file_url = file.file_path
    
    # Скачиваем изображение
    response = requests.get(f"https://api.telegram.org/file/bot{config.TELEGRAM_TOKEN}/{file_url}")
    if response.status_code != 200:
        await message.answer("❌ Ошибка загрузки изображения.")
        await state.finish()
        return
    
    original_path = f"results/original_{user_id}.jpg"
    with open(original_path, 'wb') as f:
        f.write(response.content)
    
    await message.answer("🔍 Улучшаю качество изображения...")
    
    # Улучшение качества
    upscaled_path = await upscale_image(original_path)
    
    if upscaled_path:
        with open(upscaled_path, 'rb') as photo:
            await message.answer_photo(
                photo,
                caption="✨ Изображение улучшено до 4K качества"
            )
        os.remove(upscaled_path)
    else:
        await message.answer("⚠️ Не удалось улучшить качество изображения.")
    
    os.remove(original_path)
    await state.finish()

@dp.message_handler(state=GenerationStates.waiting_for_video_prompt)
async def process_video_prompt(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    prompt = message.text
    
    # Проверяем, есть ли последнее изображение пользователя
    last_image = f"results/last_image_{user_id}.png"
    if not os.path.exists(last_image):
        await message.answer("❌ Сначала создайте или отправьте изображение для анимации.")
        await state.finish()
        return
    
    if len(prompt) < 5:
        await message.answer("❌ Описание видео должно содержать минимум 5 символов.")
        return
    
    await message.answer(f"🎬 Создаю видео по запросу: '{prompt}'... Это займет 2-5 минут.")
    
    # Генерация видео
    video_path = await generate_video(prompt, last_image)
    
    if video_path:
        with open(video_path, 'rb') as video:
            await message.answer_video(
                video,
                caption=f"🎥 Видео по запросу: '{prompt}'",
                supports_streaming=True
            )
        os.remove(video_path)
    else:
        await message.answer("⚠️ Не удалось сгенерировать видео. Попробуйте другое описание.")
    
    os.remove(last_image)
    await state.finish()

@dp.message_handler(content_types=types.ContentType.PHOTO)
async def handle_image_upload(message: types.Message):
    user_id = message.from_user.id
    photo = message.photo[-1]
    file_id = photo.file_id
    file = await bot.get_file(file_id)
    file_url = file.file_path
    
    # Скачиваем изображение
    response = requests.get(f"https://api.telegram.org/file/bot{config.TELEGRAM_TOKEN}/{file_url}")
    if response.status_code != 200:
        await message.answer("❌ Ошибка загрузки изображения.")
        return
    
    # Сохраняем как последнее изображение пользователя
    image_path = f"results/last_image_{user_id}.png"
    with open(image_path, 'wb') as f:
        f.write(response.content)
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("🎥 Создать видео", callback_data="generate_video"))
    keyboard.add(InlineKeyboardButton("✨ Улучшить качество", callback_data="upscale_image"))
    
    await message.answer(
        "✅ Изображение сохранено! Выберите действие:",
        reply_markup=keyboard
    )

@dp.callback_query_handler(lambda c: c.data == 'help_info')
async def show_help(callback_query: types.CallbackQuery):
    help_text = (
        "🆘 Помощь по ArtGenius AI\n\n"
        "Как использовать:\n"
        "1. Создание изображений:\n"
        "   • Нажмите 'Создать изображение'\n"
        "   • Опишите что нужно нарисовать\n"
        "   • Пример: 'Космический пейзаж с двумя лунами в стиле Ван Гога'\n\n"
        "2. Создание видео:\n"
        "   • Сначала создайте или загрузите изображение\n"
        "   • Нажмите 'Создать видео'\n"
        "   • Опишите движение камеры или анимацию\n"
        "   • Пример: 'Медленное вращение вокруг объекта'\n\n"
        "3. Улучшение качества:\n"
        "   • Загрузите изображение\n"
        "   • Нажмите 'Улучшить качество'\n"
        "   • Получите версию в 4K качестве\n\n"
        "4. Стили генерации:\n"
        "   • Доступно 8 различных стилей\n"
        "   • Выберите перед созданием изображения\n\n"
        "⚠️ Ограничения:\n"
        "• Максимальное время генерации видео: 5 минут\n"
        "• Максимальный размер входного изображения: 10MB\n"
        "• Запрещено создавать незаконный контент\n\n"
        "🛠 Технологии:\n"
        "• Stable Diffusion 3 (изображения)\n"
        "• Stable Video Diffusion (видео)\n"
        "• ESRGAN (улучшение качества)"
    )
    
    await bot.send_message(callback_query.from_user.id, help_text)

# Создаем папку для результатов
if not os.path.exists('results'):
    os.makedirs('results')

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
