import anthropic
import requests
import json
import time
import hashlib
import os
from datetime import datetime

# ====== إعدادات ======
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
CHECK_INTERVAL = 30 * 60  # كل 30 دقيقة

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
sent_news_hashes = set()

# ====== إرسال Telegram ======
def send_telegram(message: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        r = requests.post(url, json=payload, timeout=10)
        r.raise_for_status()
        print(f"تم الإرسال: {datetime.now().strftime('%H:%M:%S')}")
    except Exception as e:
        print(f"خطأ في Telegram: {e}")

# ====== البحث والتحليل ======
def analyze_sports_trends():
    system_prompt = """أنت مساعد صانع محتوى كارتوني كوميدي مغربي.
مهمتك: ابحث عن أحدث الأخبار الرياضية وحدد ما يمكن أن يصبح ترند في المغرب والعالم العربي.

أولوياتك:
1. المنتخب المغربي وكرة القدم المغربية
2. كرة القدم العالمية (ريال، برشلونة، PSG، إلخ)
3. فضائح اللاعبين وأخبارهم
4. نتائج مفاجئة وإخفاقات

أعطِ كل خبر نقاطاً من 10 بناءً على:
- الصدمة والمفاجأة
- الارتباط بالجمهور المغربي والعربي
- إمكانية الجدل والنقاش
- الطابع الكوميدي أو المسرحي

أرجع النتيجة بصيغة JSON فقط بدون أي نص خارجه:
{
  "news": [
    {
      "score": 8,
      "headline": "نص الخبر",
      "why_trend": "لماذا سيترند في المغرب",
      "cartoon_idea": "فكرة الكارتون الكوميدي",
      "comic_angle": "الزاوية الساخرة",
      "priority": "فوري"
    }
  ]
}

أرجع فقط الأخبار التي نقاطها 5 أو أكثر. إذا لم يوجد شيء، أرجع: {"news": []}"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2000,
            tools=[{"type": "web_search_20250305", "name": "web_search"}],
            system=system_prompt,
            messages=[{
                "role": "user",
                "content": f"ابحث الآن عن أحدث الأخبار الرياضية. الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M')}. ركز على آخر ساعتين."
            }]
        )

        full_text = ""
        for block in response.content:
            if hasattr(block, 'text'):
                full_text += block.text

        full_text = full_text.strip()
        if "```json" in full_text:
            full_text = full_text.split("```json")[1].split("```")[0].strip()
        elif "```" in full_text:
            full_text = full_text.split("```")[1].split("```")[0].strip()

        data = json.loads(full_text)
        return data.get("news", [])

    except Exception as e:
        print(f"خطأ: {e}")
        return []

# ====== تنسيق الرسالة ======
def format_message(item: dict) -> str:
    score = item.get("score", 0)
    emoji = "🚨" if score >= 8 else "⚡" if score >= 6 else "📌"
    return (
        f"{emoji} ترند محتمل {score}/10\n\n"
        f"الخبر: {item.get('headline', '')}\n"
        f"لماذا سيترند: {item.get('why_trend', '')}\n"
        f"فكرة الكارتون: {item.get('cartoon_idea', '')}\n"
        f"الزاوية الكوميدية: {item.get('comic_angle', '')}\n"
        f"الأولوية: {item.get('priority', '')}\n\n"
        f"رادار الترند - {datetime.now().strftime('%H:%M')}"
    )

# ====== الحلقة الرئيسية ======
def main():
    print("رادار الترند الرياضي يعمل...")
    send_telegram("رادار الترند الرياضي بدأ العمل! سأراقب الأخبار كل 30 دقيقة وأرسل لك ما يستحق.")

    while True:
        print(f"\n[{datetime.now().strftime('%H:%M')}] جاري البحث...")
        news_list = analyze_sports_trends()

        if not news_list:
            print("لا يوجد ترند قوي حالياً")
        else:
            for item in news_list:
                news_hash = hashlib.md5(item.get("headline", "").encode()).hexdigest()
                if news_hash not in sent_news_hashes:
                    send_telegram(format_message(item))
                    sent_news_hashes.add(news_hash)
                    time.sleep(2)

        print("الفحص القادم بعد 30 دقيقة...")
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
