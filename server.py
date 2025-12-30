import logging
from contextlib import asynccontextmanager


import cv2
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import base64

from cache import update_images_in_cache, get_images_from_cache, set_images_in_cache
from detection import init_model
from evo import get_images_from_stream

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()
init_model()

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        # Настройка и запуск планировщика
        scheduler.add_job(
            update_images_in_cache,
            trigger=CronTrigger.from_crontab('*/5 0-2,17-23 * * *', timezone='Europe/Samara'),
            id='update_images_in_cache',
            replace_existing=True
        )
        logger.info("scheduler start")
        scheduler.start()
        yield
    except Exception:
        logger.exception('Error')
    finally:
        # Завершение работы планировщика
        scheduler.shutdown()
        logger.info("scheduler shutdown")

def encode_images_to_base64(frames):
    """Кодирует список изображений в base64"""
    decode_frames = []
    for frame in frames:
        success, encoded_image = cv2.imencode(
            ".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85]
        )

        if success:
            # Создаем bytes buffer из закодированного изображения
            decode_frame = base64.b64encode(encoded_image.tobytes()).decode()
            decode_frames.append(decode_frame)
    return decode_frames

app = FastAPI(lifespan=lifespan)

@app.get("/", response_class=HTMLResponse)
def home():
    """Ручка для получения HTML страницы"""
    # Возвращаем шаблон без данных (данные будут загружаться позже)
    with open("static/index.html", "r", encoding="utf-8") as f:
        html_content = f.read()

    images = encode_images_to_base64(get_images_from_cache())
    image_cards = ""
    for image in images:
        image_cards += f"""
            <div class="image-card">
                        <img src="data:image/png;base64,{image}">
            </div>
            """
    html_content = html_content.replace('{%replace_block%}', image_cards)
    return HTMLResponse(content=html_content)


@app.get("/api/images")
def get_images(detect: bool = False):
    """Ручка для получения фотографий в формате JSON"""
    frames = get_images_from_stream(detect)
    set_images_in_cache(frames)

    encoded_images = encode_images_to_base64(frames)

    return encoded_images
