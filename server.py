import cv2
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import base64

from detection import init_model
from evo import save_images

app = FastAPI()
init_model()


def get_images():
    decode_frames = []
    frames = save_images()
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
    images = get_images()
    image_cards = ""
    for image in images:
        image_cards += f"""
        <div class="image-card">
                    <img src="data:image/png;base64,{image}">
        </div>
        """

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>FastAPI Images</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 20px;
                background-color: #f5f5f5;
            }}
            .container {{
                max-width: 1200px;
                margin: 0 auto;
            }}
            .header {{
                text-align: center;
                margin-bottom: 30px;
            }}
            .image-grid {{
                display: grid;
                gap: 20px;
            }}
            .image-card {{
                background: white;
                padding: 15px;
                border-radius: 10px;
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                text-align: center;
            }}
            .image-card img {{
                width: 90vw;
                height: auto;
                border-radius: 5px;
            }}
            .caption {{
                margin-top: 10px;
                color: #666;
            }}
        </style>
    </head>
    <body>
            <div class="image-grid">
                {image_cards}
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)
