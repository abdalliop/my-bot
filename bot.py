import os
import requests
import time
import random
import string
import re
import telebot
from telebot import types
from deep_translator import GoogleTranslator

# --- إعدادات الأمان ---
BOT_TOKEN = os.getenv("BOT_TOKEN") 
bot = telebot.TeleBot(BOT_TOKEN)

class CakuAPI:
    def __init__(self):
        self.base_url = "https://caku.ai"
        self.mail_url = "https://api.mail.tm"
        self.session = requests.Session()
        self.session.headers.update({
            "accept": "*/*",
            "content-type": "application/json",
            "origin": "https://caku.ai",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        self.email = None
        self.mail_token = None

    def _rand(self, n=10):
        return ''.join(random.choices(string.ascii_lowercase + string.digits, k=n))

    def _create_mail(self):
        try:
            r = requests.get(f"{self.mail_url}/domains")
            domain = r.json()["hydra:member"][0]["domain"]
            self.email = f"{self._rand(12)}@{domain}"
            pwd = f"Pass{random.randint(1000,9999)}!"
            payload = {"address": self.email, "password": pwd}
            requests.post(f"{self.mail_url}/accounts", json=payload)
            r = requests.post(f"{self.mail_url}/token", json=payload)
            self.mail_token = r.json().get("token")
            return True
        except: return False

    def _get_verify_link(self, timeout=60):
        if not self.mail_token: return None
        headers = {"Authorization": f"Bearer {self.mail_token}"}
        start = time.time()
        while time.time() - start < timeout:
            try:
                r = requests.get(f"{self.mail_url}/messages", headers=headers)
                msgs = r.json().get("hydra:member", [])
                if msgs:
                    r = requests.get(f"{self.mail_url}/messages/{msgs[0]['id']}", headers=headers)
                    text = r.json().get("html", [""])[0]
                    m = re.search(r"token=([a-zA-Z0-9._-]{20,})", text)
                    if m:
                        # تصحيح الخطأ البرمجي هنا (إزالة المائل العكسي من الـ f-string)
                        clean_token = m.group(1).strip("'\"&;")
                        return self.base_url + "/api/auth/verify-email?token=" + clean_token + "&callbackURL=/dashboard"
            except: pass
            time.sleep(5)
        return None

    def register(self):
        if not self._create_mail(): return False
        data = {"email": self.email, "password": self._rand(12), "name": self._rand(8), "callbackURL": "/dashboard"}
        self.session.post(f"{self.base_url}/api/auth/sign-up/email", json=data)
        link = self._get_verify_link()
        if link:
            self.session.get(link)
            return True
        return False

    def modify_image(self, prompt, image_url):
        boundary = self._rand(16)
        form_data = (
            f"------{boundary}\r\n"
            f'Content-Disposition: form-data; name="prompt"\r\n\r\n{prompt}\r\n'
            f"------{boundary}\r\n"
            f'Content-Disposition: form-data; name="model"\r\n\r\nnano-banana\r\n'
            f"------{boundary}\r\n"
            f'Content-Disposition: form-data; name="inputMode"\r\n\r\nurl\r\n'
            f"------{boundary}\r\n"
            f'Content-Disposition: form-data; name="imageUrls"\r\n\r\n["{image_url}"]\r\n'
            f"------{boundary}--\r\n"
        )
        headers = self.session.headers.copy()
        headers["content-type"] = f"multipart/form-data; boundary=----{boundary}"
        try:
            r = self.session.post(f"{self.base_url}/api/image/generate", data=form_data.encode('utf-8'), headers=headers)
            task_id = r.json().get("taskId")
            return self._wait(task_id)
        except: return None

    def _wait(self, task_id):
        if not task_id: return None
        for _ in range(30):
            try:
                r = self.session.get(f"{self.base_url}/api/image/status/{task_id}")
                res = r.json()
                if res.get("status") == 1: return res.get("outputImage")
            except: pass
            time.sleep(3)
        return None

# --- معالجة البوت ---
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "🚀 أهلاً بك! أرسل لي أي صورة واكتب في الوصف (Caption) التعديل المطلوب.")

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    if not message.caption:
        bot.reply_to(message, "❌ أرسل الوصف مع الصورة.")
        return

    status_msg = bot.reply_to(message, "⏳ جاري المعالجة.. انتظر قليلاً.")
    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        image_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info.file_path}"
        
        prompt = message.caption
        if re.search('[\u0600-\u06FF]', prompt):
            prompt = GoogleTranslator(source='auto', target='en').translate(prompt)

        api = CakuAPI()
        if api.register():
            result = api.modify_image(prompt, image_url)
            if result:
                bot.send_photo(message.chat.id, result, caption="✅ تم التعديل")
                bot.delete_message(message.chat.id, status_msg.message_id)
            else:
                bot.edit_message_text("❌ فشل التعديل.", message.chat.id, status_msg.message_id)
        else:
            bot.edit_message_text("❌ فشل إنشاء الحساب.", message.chat.id, status_msg.message_id)
    except Exception as e:
        bot.edit_message_text(f"⚠️ خطأ: {str(e)}", message.chat.id, status_msg.message_id)

if __name__ == "__main__":
    bot.infinity_polling()
# تشغيل البوت
if __name__ == "__main__":
    print("Bot is running...")
    bot.infinity_polling()
