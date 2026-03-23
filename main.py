import requests
import json
import time
import hashlib
import os
from datetime import datetime, date

# ====== إعدادات ======
MODEL_NAME = "gemini-2.0-flash"
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
CHECK_INTERVAL = 60 * 60
MAX_CALLS_PER_DAY = 10
HASH_FILE = "sent_hashes.txt"

# ====== حفظ الهاشات ======
def get_sent_hashes():
    if os.path.exists(HASH_FILE):
        with open(HASH_FILE, "r") as f:
            return set(f.read().splitlines())
    return set()

def save_hash(h):
    with open(HASH_FILE, "a") as f:
        f.write(h + "\n")

sent_news_hashes = get_sent_hashes()
calls_today = 0
last_call_date = date.today()

# ====== حماية الاستهلاك ======
def check_daily_limit():
    global calls_today, last_call_date
    today = date.today()
    if today != last_call_date:
        calls_today = 0
        last_call_date = today
    if calls_today >= MAX_CALLS_PER_DAY:
        print(f"وصلنا الحد اليومي {MAX_CALLS_PER_DAY}")
        return False
    return True

# ====== إرسال Telegram ======
def send_telegram(message: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        r = requests.post(url, json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"
        }, timeout=10)
        r.raise_for_status()
        print(f"تم الإرسال {datetime.now().strftime('%H:%M')}")
    except Exception as e:
        print(f"خطأ Telegram: {e}")

# ====== البحث والتحليل عبر Gemini ======
def analyze_sports_trends():
    global calls_today
    if not check_daily_limit():
        return []

    try:
        calls_today += 1
        now = datetime.now().strftime('%Y-%m-%d %H:%M')
        print(f"طلب Gemini {calls_today}/{MAX_CALLS_PER_DAY} - {now}")

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={GEMINI_API_KEY}"

        payload = {
            "contents": [{
                "parts": [{
                    "text": f"""الوقت الحالي: {now}
ابحث في الإنترنت الآن عن أحدث خبر رياضي نُشر في آخر ساعتين فقط.
أولوياتك: المنتخب المغربي، كرة القدم العالمية، فضائح اللاعبين، نتائج مفاجئة.
تجاهل أي خبر أقدم من ساعتين.
أرجع JSON فقط بهذا الهيكل:
إذا وجد خبر قوي: {{"found": true, "score": 8, "headline": "الخبر", "why": "لماذا سيترند في المغرب", "idea": "فكرة كارتون كوميدية بالدارجة"}}
إذا لم يوجد شيء حديث ومثير: {{"found": false}}"""
                }]
            }],
            "tools": [{"google_search_retrieval": {}}],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.2
            }
        }

        r = requests.post(url, json=payload, timeout=40)
        r.raise_for_status()
        data = r.json()

        raw = data["candidates"][0]["content"]["parts"][0]["text"]
        result = json.loads(raw)

        if result.get("found") and result.get("score", 0) >= 6:
            return [result]
        return []

    except Exception as e:
        print(f"خطأ Gemini: {e}")
        return []

# ====== تنسيق الرسالة ======
def format_message(item):
    score = item.get("score", 0)
    emoji = "🔥" if score >= 8 else "⚡"
    return (
        f"{emoji} *رادار الترند الرياضي {score}/10*\n\n"
        f"⚽ *الخبر:* {item.get('headline', '')}\n\n"
        f"🤔 *لماذا سيترند:* {item.get('why', '')}\n\n"
        f"🎨 *فكرة الكارتون:* {item.get('idea', '')}\n\n"
        f"🕒 _{datetime.now().strftime('%Y-%m-%d %H:%M')}_"
    )

# ====== الحلقة الرئيسية ======
def main():
    print(f"رادار الترند يعمل - {MODEL_NAME} + Google Search")
    send_telegram("🚀 *رادار الترند الرياضي* بدأ العمل\nGemini \+ Google Search \- مجاني 100%")

    while True:
        print(f"\n[{datetime.now().strftime('%H:%M')}] جاري البحث...")
        news_list = analyze_sports_trends()

        if not news_list:
            print("لا يوجد ترند قوي حالياً")
        else:
            for item in news_list:
                h = hashlib.md5(item.get("headline", "").encode()).hexdigest()
                if h not in sent_news_hashes:
                    send_telegram(format_message(item))
                    sent_news_hashes.add(h)
                    save_hash(h)
                    time.sleep(2)

        print("الفحص القادم بعد ساعة...")
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
