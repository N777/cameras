import io
import json
import os
from os import getenv
import requests
import cv2
from dotenv import load_dotenv
from jwt import JWT
from jwt.exceptions import JWTDecodeError

from telegram import Update, ReplyKeyboardMarkup, InputMediaPhoto
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

load_dotenv()

# Токен бота из переменных окружения
BOT_TOKEN = getenv("BOT_TOKEN")


class EvoClient:
    _token = ""
    _login = getenv("login")
    _password = getenv("password")
    _token_file = "evo_token.json"

    def __init__(self):
        self._load_token_from_cache()

    def _load_token_from_cache(self):
        """Загружает токен из файлового кеша"""
        try:
            if os.path.exists(self._token_file):
                with open(self._token_file, 'r') as f:
                    token_data = json.load(f)
                    self._token = token_data['token']
            return False
        except Exception as e:
            print(f"Ошибка загрузки токена из кеша: {e}")
            return False

    def _save_token_to_cache(self, token):
        """Сохраняет токен в файловый кеш"""
        token_data = {
            'token': token,
        }
        with open(self._token_file, 'w') as f:
            json.dump(token_data, f, indent=2)

    def get_new_token(self):
        data = {"login": self._login, "password": self._password}
        response = requests.post("https://api.vms.evo73.ru/v2/login", data=data)
        self._token = response.json()["data"]["token"]
        self._save_token_to_cache(self._token)

    @property
    def token(self):
        jwt_class = JWT()
        try:
            jwt_class.decode(self._token, do_verify=False)
        except JWTDecodeError:
            self.get_new_token()
        return "Bearer" + self._token

    def get_playlists(self):
        response = requests.get(
            "https://api.vms.evo73.ru/v2/playlist",
            headers={"Authorization": self.token},
        )
        return response.json()

    def get_cameras_from_playlist(self, playlist_id):
        response = requests.get(
            f"https://api.vms.evo73.ru/v2/playlist/{playlist_id}?get-all=true",
            headers={"Authorization": self.token},
        )
        return response.json()["cameras"]


def get_frame_from_stream(stream_url):
    """
    Простой способ чтения HLS потока с помощью OpenCV
    """
    cap = cv2.VideoCapture(stream_url)

    if not cap.isOpened():
        print("Ошибка: не удалось открыть поток")
        return

    ret, frame = cap.read()

    if not ret:
        print("Не удалось получить кадр")

    cap.release()
    return frame


def save_images():
    client = EvoClient()
    playlists = client.get_playlists()["playlists"]
    park_playlist = next(filter(lambda p: p["name"] == "parking", playlists))
    park_playlist_id = park_playlist["id"]
    cameras = client.get_cameras_from_playlist(park_playlist_id)
    frames = [get_frame_from_stream(camera["stream_url"]) for camera in cameras]
    return frames


# Функции для Telegram бота
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    keyboard = [["📸 Получить фото с камер"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        "Привет! Я бот для получения фото с камер наблюдения.\n"
        "Нажмите кнопку ниже, чтобы получить текущие фото:",
        reply_markup=reply_markup
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений"""
    text = update.message.text

    if text == "📸 Получить фото с камер":
        await get_camera_images(update, context)
    else:
        await update.message.reply_text("Используйте кнопки для взаимодействия с ботом")


async def get_camera_images(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получает и отправляет все фото в одном сообщении без временных файлов"""
    await update.message.reply_text("🔄 Получаю фото с камер...")

    try:
        # Получаем кадры с камер
        frames = save_images()

        if not frames or all(frame is None for frame in frames):
            await update.message.reply_text("❌ Не удалось получить фото с камер")
            return

        # Подготавливаем медиа-группу для отправки
        media_group = []
        valid_frames_count = 0

        # Обрабатываем кадры в памяти
        for i, frame in enumerate(frames):
            if frame is not None:
                try:
                    # Кодируем изображение в память в формате JPEG
                    success, encoded_image = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])

                    if success:
                        # Создаем bytes buffer из закодированного изображения
                        bio = io.BytesIO(encoded_image.tobytes())
                        bio.name = f'camera_{i + 1}.jpg'

                        if valid_frames_count == 0:
                            # Первое фото с подписью
                            media_group.append(
                                InputMediaPhoto(
                                    media=bio,
                                    caption=f"📹 Фото с камер наблюдения\nПолучено фото с {sum(1 for f in frames if f is not None)} камер"
                                )
                            )
                        else:
                            # Остальные фото без подписи
                            media_group.append(InputMediaPhoto(media=bio))

                        valid_frames_count += 1

                except Exception as e:
                    print(f"Ошибка при обработке фото с камеры {i + 1}: {e}")

        if not media_group:
            await update.message.reply_text("❌ Не удалось получить ни одного фото")
            return

        # Отправляем все фото одним сообщением
        await update.message.reply_media_group(media=media_group)

        await update.message.reply_text(f"✅ Успешно получено {valid_frames_count} фото")

    except Exception as e:
        print(f"Ошибка: {e}")
        await update.message.reply_text("❌ Произошла ошибка при получении фото")


def main():
    """Запуск бота"""
    if not BOT_TOKEN:
        print("Ошибка: BOT_TOKEN не найден в переменных окружения")
        return

    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()

    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Запускаем бота
    print("Бот запущен...")
    application.run_polling()


if __name__ == "__main__":
    main()
