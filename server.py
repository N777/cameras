import cv2
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import base64

from detection import init_model
from evo import get_images_from_stream

app = FastAPI()
init_model()


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


@app.get("/", response_class=HTMLResponse)
async def home():
    """Ручка для получения HTML страницы"""
    # Возвращаем шаблон без данных (данные будут загружаться позже)
    with open("static/index.html", "r", encoding="utf-8") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)


@app.get("/api/images")
def get_images(detect: bool = False):
    """Ручка для получения фотографий в формате JSON"""
    frames = get_images_from_stream(detect)

    encoded_images = encode_images_to_base64(frames)

    return encoded_images
