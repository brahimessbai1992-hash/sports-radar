import anthropic
import requests
import json
import time
import hashlib
import os
from datetime import datetime, date

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
CHECK_INTERVAL = 60 * 60
MAX_CALLS_PER_DAY = 10

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
sent_news_hashes = set()
calls_today = 0
last_call_date = date.today()

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

def send_telegram(message: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        r = requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message}, timeout=10)
        r.raise_for_status()
        print(f"تم الإرسال {datetime.now().strftime('%H:%M')}")
    except Exception as e:
        print(f"خطأ Telegram: {e}")

def analyze_sports_trends():
    global calls_today
    if not check_daily_limit():
        return []

    try:
        calls_today += 1
        print(f"طلب {calls_today}/{MAX_CALLS_PER_DAY}")

        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=500,
            tools=[{"type": "web_search_20250305", "name": "web_search"}],
            system="أنت محلل أخبار رياضية. ابحث عن أهم خبر رياضي الآن يمكن أن يترند في المغرب. أرجع JSON فقط بهذا الشكل بدون أي نص آخر: {\"found\": true, \"score\": 8, \"headline\": \"الخبر\", \"why\": \"السبب\", \"idea\": \"فكرة كارتون\"} أو {\"found\": false} إذا لم يوجد شيء مثير.",
            messages=[{"role": "user", "content": f"ابحث عن أخبار رياضية الآن. {datetime.now().strftime('%Y-%m-%d %H:%M')}"}]
        )

        full_text = ""
        for block in response.content:
            if hasattr(block, 'text'):
                full_text += block.text

        full_text = full_text.strip()
        # تنظيف JSON
        if "{" in full_text:
            start = full_text.index("{")
            end = full_text.rindex("}") + 1
            full_text = full_text[start:end]

        data = json.loads(full_text)
        if data.get("found") and data.get("score", 0) >= 5:
            return [data]
        return []

    except Exception as e:
        print(f"خطأ: {e}")
        return []

def format_message(item):
    score = item.get("score", 0)
    emoji = "🚨" if score >= 8 else "⚡" if score >= 6 else "📌"
    return (
        f"{emoji} ترند محتمل {score}/10\n\n"
        f"الخبر: {item.get('headline', '')}\n\n"
        f"لماذا سيترند: {item.get('why', '')}\n\n"
        f"فكرة الكارتون: {item.get('idea', '')}\n\n"
        f"رادار الترند - {datetime.now().strftime('%H:%M')}"
    )

def main():
    print("رادار الترند يعمل...")
    send_telegram("رادار الترند بدأ العمل - فحص كل ساعة - حد يومي 10 طلبات")

    while True:
        print(f"\n[{datetime.now().strftime('%H:%M')}] جاري البحث...")
        news_list = analyze_sports_trends()

        if not news_list:
            print("لا يوجد ترند حالياً")
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
