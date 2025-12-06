import io
import time
from os import getenv
import cv2
from dotenv import load_dotenv

from telegram import Update, ReplyKeyboardMarkup, InputMediaPhoto
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

from evo import save_images, generate_etalon_for_cameras

load_dotenv()

# Токен бота из переменных окружения
BOT_TOKEN = getenv("BOT_TOKEN")


# Функции для Telegram бота
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    keyboard = [["📸 Получить фото с камер"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        "Привет! Я бот для получения фото с камер наблюдения.\n"
        "Нажмите кнопку ниже, чтобы получить текущие фото:",
        reply_markup=reply_markup,
    )


async def create_new_etalon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    await update.message.reply_text("Generate new etalon.")
    try:
        start_time = time.time()
        # Получаем кадры с камер
        frames = generate_etalon_for_cameras()
        finish_time = time.time()
        await update.message.reply_text(
            f"⌛ Времени заняло {finish_time - start_time:.2f}s"
        )

        media_group, _ = await group_by_frames_in_media(frames)

        await update.message.reply_media_group(media=media_group)

        await update.message.reply_text(f"New etalon created")
    except Exception:
        await update.message.reply_text("Error while generate new etalon.")


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
        start_time = time.time()
        # Получаем кадры с камер
        frames = save_images()
        finish_time = time.time()
        await update.message.reply_text(
            f"⌛ Времени заняло {finish_time - start_time:.2f}s"
        )

        if not frames or all(frame is None for frame in frames):
            await update.message.reply_text("❌ Не удалось получить фото с камер")
            return

        media_group, valid_frames_count = await group_by_frames_in_media(frames)

        if not media_group:
            await update.message.reply_text("❌ Не удалось получить ни одного фото")
            return

        # Отправляем все фото одним сообщением
        await update.message.reply_media_group(media=media_group)

        await update.message.reply_text(
            f"✅ Успешно получено {valid_frames_count} фото"
        )

    except Exception as e:
        print(f"Ошибка: {e}")
        await update.message.reply_text("❌ Произошла ошибка при получении фото")


async def group_by_frames_in_media(frames):
    # Подготавливаем медиа-группу для отправки
    media_group = []
    valid_frames_count = 0

    # Обрабатываем кадры в памяти
    for i, frame in enumerate(frames):
        if frame is not None:
            try:
                # Кодируем изображение в память в формате JPEG
                success, encoded_image = cv2.imencode(
                    ".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85]
                )

                if success:
                    # Создаем bytes buffer из закодированного изображения
                    bio = io.BytesIO(encoded_image.tobytes())
                    bio.name = f"camera_{i + 1}.jpg"

                    if valid_frames_count == 0:
                        # Первое фото с подписью
                        media_group.append(
                            InputMediaPhoto(
                                media=bio,
                                caption=f"📹 Фото с камер наблюдения\nПолучено фото с {sum(1 for f in frames if f is not None)} камер",
                            )
                        )
                    else:
                        # Остальные фото без подписи
                        media_group.append(InputMediaPhoto(media=bio))

                    valid_frames_count += 1

            except Exception as e:
                print(f"Ошибка при обработке фото с камеры {i + 1}: {e}")
    return media_group, valid_frames_count


def main():
    """Запуск бота"""
    if not BOT_TOKEN:
        print("Ошибка: BOT_TOKEN не найден в переменных окружения")
        return

    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()

    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("new_etalon", create_new_etalon))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    # Запускаем бота
    print("Бот запущен...")
    application.run_polling()


if __name__ == "__main__":
    main()
