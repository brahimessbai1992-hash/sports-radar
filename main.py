import requests
import json
import time
import hashlib
import os
from datetime import datetime, date, timedelta

# ====== إعدادات ======
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
NEWS_API_KEY = os.environ.get("NEWS_API_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
CHECK_INTERVAL = 60 * 60
MAX_CALLS_PER_DAY = 10

sent_news_hashes = set()
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
        r = requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message}, timeout=10)
        r.raise_for_status()
        print(f"تم الإرسال {datetime.now().strftime('%H:%M')}")
    except Exception as e:
        print(f"خطأ Telegram: {e}")

# ====== جلب الأخبار من NewsAPI ======
def fetch_sports_news():
    try:
        from_time = (datetime.utcnow() - timedelta(hours=2)).strftime('%Y-%m-%dT%H:%M:%S')
        url = "https://newsapi.org/v2/everything"

        params = {
            "apiKey": NEWS_API_KEY,
            "q": "football OR soccer OR Morocco OR FIFA OR كرة القدم",
            "sortBy": "publishedAt",
            "from": from_time,
            "pageSize": 5
        }
        r = requests.get(url, params=params, timeout=10)
        data = r.json()
        articles = data.get("articles", [])

        if not articles:
            print("لا توجد أخبار جديدة من NewsAPI")
            return ""

        headlines = []
        for a in articles[:5]:
            title = a.get("title", "")
            published = a.get("publishedAt", "")
            if title and title != "[Removed]":
                headlines.append(f"- {title} ({published})")

        return "\n".join(headlines)

    except Exception as e:
        print(f"خطأ NewsAPI: {e}")
        return ""

# ====== تحليل الأخبار عبر Gemini (مجاني) ======
def analyze_news(headlines: str):
    global calls_today
    if not check_daily_limit():
        return []
    if not headlines:
        return []

    try:
        calls_today += 1
        print(f"طلب Gemini {calls_today}/{MAX_CALLS_PER_DAY}")

        prompt = f"""أنت محلل محتوى كارتوني كوميدي مغربي.
هذه أحدث الأخبار الرياضية:
{headlines}

حدد أفضل خبر يمكن أن يترند في المغرب والعالم العربي.
أرجع JSON فقط بدون أي نص آخر:
إذا وجد خبر قوي: {{"found": true, "score": 8, "headline": "الخبر", "why": "لماذا سيترند في المغرب", "idea": "فكرة كارتون كوميدية"}}
إذا لم يوجد شيء مثير: {{"found": false}}"""

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"maxOutputTokens": 300, "temperature": 0.3}
        }

        r = requests.post(url, json=payload, timeout=15)
        r.raise_for_status()
        data = r.json()

        full_text = data["candidates"][0]["content"]["parts"][0]["text"].strip()

        if "{" in full_text:
            start = full_text.index("{")
            end = full_text.rindex("}") + 1
            full_text = full_text[start:end]

        result = json.loads(full_text)
        if result.get("found") and result.get("score", 0) >= 5:
            return [result]
        return []

    except Exception as e:
        print(f"خطأ Gemini: {e}")
        return []

# ====== تنسيق الرسالة ======
def format_message(item):
    score = item.get("score", 0)
    emoji = "🚨" if score >= 8 else "⚡" if score >= 6 else "📌"
    return (
        f"{emoji} ترند محتمل {score}/10\n\n"
        f"الخبر: {item.get('headline', '')}\n\n"
        f"لماذا سيترند: {item.get('why', '')}\n\n"
        f"فكرة الكارتون: {item.get('idea', '')}\n\n"
        f"رادار الترند - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )

# ====== الحلقة الرئيسية ======
def main():
    print("رادار الترند يعمل - NewsAPI + Gemini مجاناً")
    send_telegram("رادار الترند بدأ العمل - NewsAPI + Gemini - مجاني 100%")

    while True:
        print(f"\n[{datetime.now().strftime('%H:%M')}] جاري جلب الأخبار...")

        headlines = fetch_sports_news()

        if not headlines:
            print("لا توجد أخبار جديدة")
        else:
            print("وجدنا أخبار - نحللها...")
            news_list = analyze_news(headlines)

            if not news_list:
                print("لا يوجد ترند قوي حالياً")
            else:
                for item in news_list:
                    h = hashlib.md5(item.get("headline", "").encode()).hexdigest()
                    if h not in sent_news_hashes:
                        send_telegram(format_message(item))
                        sent_news_hashes.add(h)
                        time.sleep(2)

        print("الفحص القادم بعد ساعة...")
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
