import os, logging
from huggingface_hub import InferenceClient
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# إعداد السجلات لمراقبة العمل
logging.basicConfig(level=logging.INFO)

# جلب الإعدادات من متغيرات البيئة في Railway
BOT_TOKEN = os.getenv("BOT_TOKEN")
HF_TOKEN = os.getenv("HF_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

# إنشاء العميل للاتصال بـ Hugging Face مجاناً
client = InferenceClient(token=HF_TOKEN)

# قائمة النماذج المجانية والمستقرة
MODELS = {
    "t2i": "black-forest-labs/FLUX.1-schnell", # نص إلى صورة
    "i2v": "ali-vilab/i2vgen-xl",               # صورة إلى فيديو
    "t2v": "ali-vilab/i2vgen-xl"                # نص إلى فيديو
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    
    keyboard = [
        ['📸 صورة إلى فيديو', '🎥 نص إلى فيديو'],
        ['🎨 نص إلى صورة']
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("🚀 بوت الذكاء الاصطناعي الشامل جاهز!\nاختر المهمة من القائمة:", reply_markup=reply_markup)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    text = update.message.text

    if text == '📸 صورة إلى فيديو':
        context.user_data['mode'] = 'i2v'
        await update.message.reply_text("الآن أرسل لي (الصورة) التي تريد تحريكها.")
    
    elif text == '🎥 نص إلى فيديو':
        context.user_data['mode'] = 't2v'
        await update.message.reply_text("أرسل وصف الفيديو بالإنجليزية (مثلاً: A flying bird):")
    
    elif text == '🎨 نص إلى صورة':
        context.user_data['mode'] = 't2i'
        await update.message.reply_text("أرسل وصف الصورة بالإنجليزية:")

    elif 'mode' in context.user_data:
        mode = context.user_data['mode']
        if mode == 'i2v': return # ننتظر صورة وليس نصاً
        
        status_msg = await update.message.reply_text("⏳ جاري التوليد... قد يستغرق الأمر دقيقة.")
        try:
            if mode == 't2v':
                video_data = client.text_to_video(text, model=MODELS["t2v"])
                with open("video.mp4", "wb") as f: f.write(video_data)
                await update.message.reply_video(video=open("video.mp4", "rb"), caption="✅ تم توليد الفيديو")
            elif mode == 't2i':
                image = client.text_to_image(text, model=MODELS["t2i"])
                image.save("image.png")
                await update.message.reply_photo(photo=open("image.png", "rb"), caption="✅ تم توليد الصورة")
        except Exception as e:
            await status_msg.edit_text(f"❌ حدث خطأ: {str(e)}")
        finally:
            context.user_data.clear()

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    
    if context.user_data.get('mode') == 'i2v':
        status_msg = await update.message.reply_text("⏳ جاري معالجة الصورة وتحويلها لفيديو...")
        photo_file = await update.message.photo[-1].get_file()
        photo_path = "input.jpg"
        await photo_file.download_to_drive(photo_path)
        
        try:
            with open(photo_path, "rb") as f:
                img_bytes = f.read()
            video_data = client.image_to_video(img_bytes, model=MODELS["i2v"])
            with open("out.mp4", "wb") as f: f.write(video_data)
            await update.message.reply_video(video=open("out.mp4", "rb"), caption="✨ فيديو من صورتك جاهز!")
        except Exception as e:
            await status_msg.edit_text(f"❌ خطأ: {str(e)}")
        finally:
            context.user_data.clear()
    else:
        await update.message.reply_text("اختر '📸 صورة إلى فيديو' أولاً.")

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.run_polling()
