import os, logging
from huggingface_hub import InferenceClient
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

logging.basicConfig(level=logging.INFO)

# جلب الإعدادات
BOT_TOKEN = os.getenv("BOT_TOKEN")
HF_TOKEN = os.getenv("HF_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

# الاتصال المباشر بـ Hugging Face (هذا يمنع خطأ 402)
client = InferenceClient(token=HF_TOKEN)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    keyboard = [['📸 صورة إلى فيديو'], ['🎨 نص إلى صورة']]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("🚀 أهلاً بك! اختر المهمة:", reply_markup=reply_markup)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    text = update.message.text

    if text == '📸 صورة إلى فيديو':
        context.user_data['mode'] = 'i2v'
        await update.message.reply_text("أرسل الصورة الآن...")
    elif text == '🎨 نص إلى صورة':
        context.user_data['mode'] = 't2i'
        await update.message.reply_text("أرسل وصف الصورة بالإنجليزية:")
    elif context.user_data.get('mode') == 't2i':
        msg = await update.message.reply_text("⏳ جاري التوليد مجاناً...")
        try:
            # استخدام موديل مجاني مباشرة بدون وسيط
            image = client.text_to_image(text, model="black-forest-labs/FLUX.1-schnell")
            image.save("out.png")
            await update.message.reply_photo(photo=open("out.png", "rb"))
        except Exception as e:
            await msg.edit_text(f"❌ خطأ: تأكد من الـ Token في Railway")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('mode') == 'i2v':
        msg = await update.message.reply_text("⏳ جاري تحويل الصورة لفيديو (مجاناً)...")
        photo = await update.message.photo[-1].get_file()
        await photo.download_to_drive("img.jpg")
        try:
            with open("img.jpg", "rb") as f:
                video_data = client.image_to_video(f.read(), model="ali-vilab/i2vgen-xl")
            with open("vid.mp4", "wb") as f: f.write(video_data)
            await update.message.reply_video(video=open("vid.mp4", "rb"))
        except Exception as e:
            await msg.edit_text("❌ السيرفر مزدحم حالياً، حاول مرة أخرى بعد قليل.")

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.run_polling()
