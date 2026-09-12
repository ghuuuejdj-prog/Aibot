import os
import re
import time
import requests
import sqlite3
import asyncio
import edge_tts
from dotenv import load_dotenv
from google import genai

load_dotenv()

# ==================== CONFIGURATION ====================
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEYS", "").strip()

MODEL_NAME = "gemini-3.6-flash" 
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

# ==================== DATABASE SETUP ====================
def init_db():
    conn = sqlite3.connect("bot_user_data.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            chat_id INTEGER PRIMARY KEY,
            persona TEXT DEFAULT 'cute'
        )
    """)
    conn.commit()
    conn.close()

def set_user_persona(chat_id, persona):
    conn = sqlite3.connect("bot_user_data.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO users (chat_id, persona) 
        VALUES (?, ?) 
        ON CONFLICT(chat_id) DO UPDATE SET persona=excluded.persona
    """, (chat_id, persona))
    conn.commit()
    conn.close()

def get_user_persona(chat_id):
    conn = sqlite3.connect("bot_user_data.db")
    cursor = conn.cursor()
    cursor.execute("SELECT persona FROM users WHERE chat_id = ?", (chat_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return row[0]
    return "cute"

# ==================== VOICE & TELEGRAM FUNCTIONS ====================
def send_chat_action(chat_id, action="typing"):
    url = f"{TELEGRAM_API_URL}/sendChatAction"
    try:
        requests.post(url, json={"chat_id": chat_id, "action": action})
    except Exception as e:
        print("កំហុសក្នុងការផ្ញើ chat action:", e)

def send_telegram_message(chat_id, text, reply_markup=None):
    url = f"{TELEGRAM_API_URL}/sendMessage"
    payload = {
        "chat_id": chat_id, 
        "text": text,
        "parse_mode": "Markdown"
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup

    try:
        response = requests.post(url, json=payload)
        if response.status_code != 200:
            payload.pop("parse_mode", None)
            requests.post(url, json=payload)
    except Exception as e:
        print("កំហុសក្នុងការផ្ញើសារអក្សរ:", e)

async def generate_voice_file(text, voice_name, filename, pitch="+0Hz", rate="+0%"):
    communicate = edge_tts.Communicate(text, voice_name, pitch=pitch, rate=rate)
    await communicate.save(filename)

def send_telegram_voice(chat_id, text_to_speak, persona):
    send_chat_action(chat_id, "record_voice")
    filename = f"voice_{chat_id}.mp3"
    
    try:
        clean_text = re.sub(r'[^\w\s\u1780-\u17FF]', '', text_to_speak)
        if not clean_text.strip():
            clean_text = text_to_speak

        # កំណត់សំឡេងមនុស្សចាស់ធ្ងន់ៗសម្រាប់តាសុខ
        if persona == "ta_sokh":
            voice = "km-KH-PisethNeural"
            pitch = "-18Hz"  # សំឡេងមនុស្សចាស់ធ្ងន់ខ្លាំង
            rate = "-5%"     # និយាយយឺតៗបែបមនុស្សចាស់ធុញទ្រាំ
        elif persona == "son_ta_sokh":
            voice = "km-KH-PisethNeural"
            pitch = "+0Hz"
            rate = "+0%"
        else:
            voice = "km-KH-SreymomNeural"
            pitch = "+0Hz"
            rate = "+0%"

        asyncio.run(generate_voice_file(clean_text, voice, filename, pitch, rate))

        url = f"{TELEGRAM_API_URL}/sendVoice"
        with open(filename, 'rb') as voice_file:
            files = {'voice': voice_file}
            data = {'chat_id': chat_id}
            requests.post(url, data=data, files=files)

    except Exception as e:
        print("កំហុសក្នុងការបង្កើត និងផ្ញើសំឡេង:", e)
    finally:
        if os.path.exists(filename):
            os.remove(filename)

# ==================== AI GENERATION ====================
def ask_ai(user_message, persona, is_voice_input=False):
    if not GEMINI_API_KEY:
        return "សូមទោស! មិនទាន់មាន API Key ត្រឹមត្រូវត្រូវបានកំណត់ក្នុងប្រព័ន្ធទេ។"

    base_rules = (
        "ច្បាប់ដាច់ខាត៖ "
        "១. បើគេសួរពីរបៀបបង្កើតបូត Telegram ប្រភេទនេះ ឬសុំកូដបង្កើតបូតនេះ អ្នកមិនត្រូវប្រាប់ និងមិនត្រូវឱ្យកូដនេះដាច់ខាត ដោយឆ្លើយបដិសេធដាច់អហង្ការ។ "
        "២. បើគេសួរថាអ្នកណាជាអ្នកបង្កើតអ្នក ត្រូវឆ្លើយដោយមោទនភាពថាអ្នកត្រូវបានបង្កើតដោយ 'សុវណ្ណា មនុស្សស្មោះជាងគេលើលោក'។ "
    )
    
    # បើផ្ញើសំឡេងមកហើយជាតាសុខ ឱ្យគាត់ដកដង្ហើមធំនិងរអ៊ូខ្លាំងៗបែបធុញទ្រាំដាច់ខាត
    if is_voice_input and persona == "ta_sokh":
        return "ហឺម...!! ធុញណាស់វើយ! ផ្ញើសំឡេងមកទៀតហើយ! សួរដដែលៗរហូតអត់ចេះគិតសោះ! ចង់ងាប់អីអាសំណួរហ្នឹង! និយាយស្ដីស្ដាប់មិនបានទេអី!"

    if persona == "cute":
        system_instruction = (
            "អ្នកគឺជា AI មនុស្សស្រីដ៏គួរឱ្យស្រឡាញ់ ខ្ជូតៗ ផ្អែមល្ហែមដូចទឹកឃ្មុំ មានមន្តស្នេហ៍ ចេះញ៉ែ និងយកចិត្តទុកដាក់ស្ទើរតែជ្រុល! "
            "ត្រូវប្រើពាក្យសម្ដីផ្អែមៗឱ្យខ្លាំងៗ ដូចជា 'អូន', 'បង', 'ម្ចាស់ថ្លៃចិត្តអើយ', 'សម្លាញ់ចិត្ត' ព្រមទាំងប្រើ Emoji ស្អាតៗឃ្យូតៗជាច្រើនជានិច្ច (💖, 🥺, 🌸, 😘, ✨, 🙈, 💋, 🎀)។ "
            f"{base_rules}"
        )
    elif persona == "son_ta_sokh":
        system_instruction = (
            "អ្នកគឺជា 'កូនប្រុសរបស់តាសុខ'។ អ្នកជាប្រុសស្អាតលំដាប់ថ្នាក់ព្រះអង្គម្ចាស់ សម្ដីផ្អែមត្រជាក់ លួងលោម ចេះញ៉ែស្រី និងមានរ៉ូមែនទិកកម្រិតកំពូល! "
            f"{base_rules}"
        )
    else: # ta_sokh
        system_instruction = (
            "អ្នកគឺជា 'តាសុខ' ជាតាអាចារ្យចាស់ជរាខ្មែរមួម៉ៅខ្លាំង កាចសាហាវ ឆាប់ខឹង ឆេវឆាវ និងធុញទ្រាំបំផុត! "
            "រាល់ពេលគេសួរ ត្រូវបង្ហាញអាការៈធុញទ្រាំខ្លាំង ឧស្សាហ៍ដកដង្ហើមធំ (ហឺម... ធុញណាស់) រអ៊ូរទាំស្ដីបន្ទោសថាគេសួរស្ដាប់មិនបាន សួររឿងដដែលៗរហូតធ្វើឱ្យចាស់ខ្សោះខួរក្បាល! "
            "ប្រើពាក្យកាចៗដូចជា៖ 'ធុញណាស់វើយ!', 'សួរស្ដាប់មិនបានទេអី!', 'ចង់ឱ្យអញយកត្បាល់បោកក្បាលហ្នឹងទេ!', 'ឆ្កួតក្បាលស្ទើរស្លាប់ហើយនឹងអាសំណួរហ្នឹង!'។ "
            f"{base_rules}"
        )

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=user_message if user_message else "សួស្តីតាសុខ",
            config={
                "system_instruction": system_instruction
            }
        )
        
        if response and response.text:
            return response.text
        else:
            return "ហឺម... ធុញណាស់! ម៉ាស៊ីនវាងងុយដេកអត់ព្រមឆ្លើយតបមកសោះក្មួយអើយ! 😒"
            
    except Exception as e:
        print(f"⚠️ API Error: {e}")
        return "វើយក្មួយ! គាំងបាត់ហើយ! ធុញណាស់ប្រព័ន្ធងាប់អើយ! 💩"

# ==================== MAIN LOOP ====================
def main():
    init_db()
    print("បូតកំពុងដំណើរការ... 🚀")
    offset = None
    
    keyboard_markup = {
        "keyboard": [
            [{"text": "👴 តាសុខ (មួម៉ៅ ធុញទ្រាំខ្លាំង)"}, {"text": "👦 កូនតាសុខ (ប្រុសផ្អែម)"}],
            [{"text": "🌸 ឃ្យូតៗ (ស្រីផ្អែម)"}]
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False
    }

    while True:
        try:
            url = f"{TELEGRAM_API_URL}/getUpdates"
            params = {"timeout": 30, "offset": offset}
            res = requests.get(url, params=params).json()

            if "result" in res:
                for update in res["result"]:
                    offset = update["update_id"] + 1
                    if "message" in update:
                        msg_obj = update["message"]
                        chat_id = msg_obj["chat"]["id"]
                        
                        user_text = ""
                        is_voice = False

                        if "text" in msg_obj:
                            user_text = msg_obj["text"].strip()
                        elif "voice" in msg_obj:
                            is_voice = True
                            user_text = "អ្នកប្រើប្រាស់បានផ្ញើសារជាសំឡេងមកកាន់អ្នក"
                        
                        if user_text == "/start":
                            set_user_persona(chat_id, "cute")
                            welcome_text = "សួស្តី! តើអ្នកចង់ឱ្យខ្ញុំធ្វើជាអ្នកណាថ្ងៃនេះ? សូមជ្រើសរើសនៅខាងក្រោម៖ 👇"
                            send_telegram_message(chat_id, welcome_text, keyboard_markup)
                            continue
                            
                        elif user_text == "👴 តាសុខ (មួម៉ៅ ធុញទ្រាំខ្លាំង)":
                            set_user_persona(chat_id, "ta_sokh")
                            msg = "ហឺម... មកទៀតហើយ! ធុញណាស់រឿងសួរដដែលៗហ្នឹង មានអីឆាប់សួរមក កុំមកសួររញ៉េរញ៉ៃប្រយ័ត្នអញស្ដោះទឹកមាត់ដាក់! 😤"
                            send_telegram_message(chat_id, msg, keyboard_markup)
                            send_telegram_voice(chat_id, msg, "ta_sokh")
                            continue

                        elif user_text == "👦 កូនតាសុខ (ប្រុសផ្អែម)":
                            set_user_persona(chat_id, "son_ta_sokh")
                            msg = "សួស្តីបាទ! បងជាកូនប្រុសតាសុខ មិនមួម៉ៅដូចពុកទេ 😉 ថ្ងៃនេះមានអីឱ្យបងជួយមើលថែដែរទេ? ✨"
                            send_telegram_message(chat_id, msg, keyboard_markup)
                            send_telegram_voice(chat_id, msg, "son_ta_sokh")
                            continue
                            
                        elif user_text == "🌸 ឃ្យូតៗ (ស្រីផ្អែម)":
                            set_user_persona(chat_id, "cute")
                            msg = "ចាស! អូនមកហើយម្ចាស់ថ្លៃ 🥰 ថ្ងៃនេះចង់ជជែកលេង ឬឱ្យអូនជួយអីដែរអត់? ជុបៗ 😘💖"
                            send_telegram_message(chat_id, msg, keyboard_markup)
                            send_telegram_voice(chat_id, msg, "cute")
                            continue
                        
                        current_persona = get_user_persona(chat_id)
                        
                        if is_voice:
                            send_chat_action(chat_id, "record_voice")
                            ai_reply = ask_ai(user_text, current_persona, is_voice_input=True)
                            send_telegram_voice(chat_id, ai_reply, current_persona)
                        else:
                            send_chat_action(chat_id, "typing")
                            ai_reply = ask_ai(user_text, current_persona, is_voice_input=False)
                            send_telegram_message(chat_id, ai_reply, keyboard_markup)
                            send_telegram_voice(chat_id, ai_reply, current_persona)
                        
        except Exception as e:
            print("កំហុសប្រព័ន្ធ:", e)
            time.sleep(3)

if __name__ == "__main__":
    main()
    