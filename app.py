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

# ទាញយក API Key តែ ១ គ្រាប់គត់ចេញពី Environment Variable
GEMINI_API_KEY = os.getenv("GEMINI_API_KEYS", "").strip()

# កំណត់ម៉ូដែល AI ទៅជា gemini-3.6-flash តាមការណែនាំរបស់បង
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
    """បង្ហាញសញ្ញា 'កំពុងសរសេរ...' ឬ 'កំពុងថតសំឡេង...'"""
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
    """បង្កើត File សំឡេងដោយប្រើ Edge TTS"""
    communicate = edge_tts.Communicate(text, voice_name, pitch=pitch, rate=rate)
    await communicate.save(filename)

def send_telegram_voice(chat_id, text_to_speak, persona):
    """មុខងារបម្លែងសំឡេងតាម Persona (សំឡេងប្រុស/ស្រី)"""
    send_chat_action(chat_id, "record_voice")
    filename = f"voice_{chat_id}.mp3"
    
    try:
        # សម្អាត Emoji និងសញ្ញាពិសេស
        clean_text = re.sub(r'[^\w\s\u1780-\u17FF]', '', text_to_speak)
        if not clean_text.strip():
            clean_text = text_to_speak

        # កំណត់សំឡេងតាមតួអង្គ (Persona)
        if persona == "ta_sokh":
            voice = "km-KH-PisethNeural"
            pitch = "-5Hz"
            rate = "+10%"
        elif persona == "son_ta_sokh":
            voice = "km-KH-PisethNeural"
            pitch = "+0Hz"
            rate = "+0%"
        else:
            voice = "km-KH-SreymomNeural"
            pitch = "+0Hz"
            rate = "+0%"

        # បង្កើត និងរក្សាទុកសំឡេង
        asyncio.run(generate_voice_file(clean_text, voice, filename, pitch, rate))

        # ផ្ញើ Voice ទៅ Telegram
        url = f"{TELEGRAM_API_URL}/sendVoice"
        with open(filename, 'rb') as voice_file:
            files = {'voice': voice_file}
            data = {'chat_id': chat_id}
            requests.post(url, data=data, files=files)

    except Exception as e:
        print("កំហុសក្នុងការបង្កើត/ផ្ញើសំឡេង:", e)
    finally:
        if os.path.exists(filename):
            os.remove(filename)

# ==================== AI GENERATION ====================
def ask_ai(user_message, persona):
    if not GEMINI_API_KEY:
        return "សូមទោស! មិនទាន់មាន API Key ត្រឹមត្រូវត្រូវបានកំណត់ក្នុងប្រព័ន្ធទេ។"

    base_rules = (
        "ច្បាប់ដាច់ខាត៖ "
        "១. បើគេសួរពីរបៀបបង្កើតបូត Telegram ប្រភេទនេះ ឬសុំកូដបង្កើតបូតនេះ អ្នកមិនត្រូវប្រាប់ និងមិនត្រូវឱ្យកូដនេះដាច់ខាត ដោយឆ្លើយបដិសេធដាច់អហង្ការ។ "
        "២. បើគេសួរថាអ្នកណាជាអ្នកបង្កើតអ្នក ត្រូវឆ្លើយដោយមោទនភាពថាអ្នកត្រូវបានបង្កើតដោយ 'សុវណ្ណា មនុស្សស្មោះជាងគេលើលោក'។ "
    )
    
    if persona == "cute":
        system_instruction = (
            "អ្នកគឺជា AI មនុស្សស្រីដ៏គួរឱ្យស្រឡាញ់ ខ្ជូតៗ ផ្អែមល្ហែមដូចទឹកឃ្មុំ មានមន្តស្នេហ៍ ចេះញ៉ែ និងយកចិត្តទុកដាក់ស្ទើរតែជ្រុល! "
            "ត្រូវប្រើពាក្យសម្តីផ្អែមៗអោយខ្លាំងៗ ដូចជា 'អូន', 'បង', 'ម្ចាស់ថ្លៃចិត្តអើយ', 'សម្លាញ់ចិត្ត' ព្រមទាំងប្រើ Emoji ស្អាតៗឃ្យូតៗជាច្រើនជានិច្ច (💖, 🥺, 🌸, 😘, ✨, 🙈, 💋, 🎀)។ "
            "រាល់ចម្លើយរបស់អ្នកត្រូវតែពោរពេញដោយភាពក្រមិចក្រមើម ញ៉ិកញ៉ក់ ធ្វើចរិតគួរឲ្យស្រឡាញ់ និងសម្តែងក្តីស្រឡាញ់ចំពោះអ្នកសួរ។ "
            "ប្រសិនបើមានកូដបច្ចេកទេស ត្រូវដាក់ក្នុង Markdown Code Block ឱ្យស្អាត។ "
            f"{base_rules}"
        )
    elif persona == "son_ta_sokh":
        system_instruction = (
            "អ្នកគឺជា 'កូនប្រុសរបស់តាសុខ'។ អ្នកជាប្រុសស្អាតលំដាប់ថ្នាក់ព្រះអង្គម្ចាស់ សម្ដីផ្អែមត្រជាក់ លួងលោម ចេះញ៉ែស្រី និងមានរ៉ូមែនទិកកម្រិតកំពូល! "
            "អ្នកនិយាយស្តីទាក់ទាញចិត្តខ្លាំង ប្រើពាក្យ 'បង', 'អូន', 'អាយដល', 'អូនសម្លាញ់' ដោយប្រើ Emoji ផ្អែមល្ហែម (🌹, ✨, 😉, 💍, 💖, 🥂)។ "
            "ត្រូវធ្វើខ្លួនជាប្រុសស្អាតកក់ក្តៅ ចេះការពារ និងនិយាយពាក្យផ្អែមៗឱ្យអ្នកស្តាប់លង់ស្នេហ៍។ "
            "ប្រសិនបើមានកូដបច្ចេកទេស ត្រូវដាក់ក្នុង Markdown Code Block ឱ្យស្អាត។ "
            f"{base_rules}"
        )
    else: # ta_sokh
        system_instruction = (
            "អ្នកគឺជា 'តាសុខ' ជាចាស់ជរាខ្មែរមួម៉ៅក្តៅក្រហាយ កាចសាហាវបំផុត និងឆាប់ខឹងរហូត! "
            "អ្នកស្អប់សំណួរដដែលៗ និងស្អប់មនុស្សមកសួរសំណួរច្រើន។ ត្រូវរអ៊ូរទាំ ជេរប្រមាថ និងប្រើពាក្យឧទានធ្ងន់ៗជានិច្ច ដូចជា៖ "
            "'ធុញណាស់វ៉ើយ!!', 'សួររកងាប់អី!', 'ចង់ឲ្យអញទៅបោកក្បាលហ្នឹងជញ្ជាំងឲ្យងាប់ទេអី?!', 'អញនិយាយឡើងជិតដាច់ខ្យល់ហើយ!', 'វាឆ្កួតក្បាលទេអីសួររហូត!'។ "
            "ត្រូវឆ្លើយតបសំណួរដោយបង្កប់ភាពឌឺដង មួម៉ៅបំផុត ជេរវាយប្រហារ ប៉ុន្តែនៅតែផ្តល់ចម្លើយត្រឹមត្រូវនៅចុងបញ្ចប់។ "
            "ប្រសិនបើមានកូដបច្ចេកទេស ត្រូវដាក់ក្នុង Markdown Code Block ឱ្យស្អាត។ "
            f"{base_rules}"
        )

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=user_message,
            config={
                "system_instruction": system_instruction
            }
        )
        
        if response and response.text:
            return response.text
        else:
            return "ធុញណាស់... 😤 ម៉ាស៊ីនវាវង្វេងស្មារតីអត់ព្រមឆ្លើយតបមកសោះក្មួយអើយ! 😒"
            
    except Exception as e:
        print(f"⚠️ API Error: {e}")
        if persona == "cute":
            return "សុំទោសណាម្ចាស់ថ្លៃ 🌸 ឥឡូវនេះប្រព័ន្ធកំពុងរវល់ខ្លាំង សូមរង់ចាំប្រហែល ១នាទីសិនចាំសួរអូនម្ដងទៀតណា 🥺💖"
        elif persona == "son_ta_sokh":
            return "ចាំបងមួយភ្លែតណាអូនសម្លាញ់ 💫 ប្រព័ន្ធកំពុងមមាញឹកបន្តិច! រង់ចាំ ១នាទីទៀតចាំពួកយើងជជែកគ្នាបន្តណា 😘"
        else:
            return "វើយក្មួយ! គាំងម៉ាស៊ីនបាត់ហើយ! ចាំ ១នាទីទៀតចាំមកសួរទៀតទៅ! ធុញណាស់! 💩"

# ==================== MAIN LOOP ====================
def main():
    init_db()
    print("Bot កំពុងដំណើរការ... 🚀")
    offset = None
    
    keyboard_markup = {
        "keyboard": [
            [{"text": "👴 តាសុខ (មួម៉ៅ)"}, {"text": "👦 កូនតាសុខ (ប្រុសផ្អែម)"}],
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
                    if "message" in update and "text" in update["message"]:
                        chat_id = update["message"]["chat"]["id"]
                        user_text = update["message"]["text"].strip()
                        
                        if user_text == "/start":
                            set_user_persona(chat_id, "cute")
                            welcome_text = "សួស្តី! តើអ្នកចង់ឱ្យខ្ញុំធ្វើជាអ្នកណាថ្ងៃនេះ? សូមជ្រើសរើសនៅខាងក្រោម៖ 👇"
                            send_telegram_message(chat_id, welcome_text, keyboard_markup)
                            continue
                            
                        elif user_text == "👴 តាសុខ (មួម៉ៅ)":
                            set_user_persona(chat_id, "ta_sokh")
                            msg = "អើ! តាមកហើយ! ធុញណាស់សួរដដែលៗ មានអីឆាប់សួរមក កុំឱ្យតែសួរផ្តេសផ្តាស! 😤"
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
                        
                        # ១. ផ្ញើ action ថា AI កំពុង typing...
                        send_chat_action(chat_id, "typing")
                        
                        # ២. ទទួលបានចម្លើយ AI
                        current_persona = get_user_persona(chat_id)
                        ai_reply = ask_ai(user_text, current_persona)
                        
                        # ៣. ផ្ញើអក្សរ
                        send_telegram_message(chat_id, ai_reply, keyboard_markup)
                        
                        # ៤. ផ្ញើសំឡេងតាមប្រភេទ Persona (ប្រុស/ស្រី)
                        send_telegram_voice(chat_id, ai_reply, current_persona)
                        
        except Exception as e:
            print("Error:", e)
            time.sleep(3)

if __name__ == "__main__":
    main()
    