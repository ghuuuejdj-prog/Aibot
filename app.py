import os
import re
import time
import requests
import random
import sqlite3
from dotenv import load_dotenv
from google import genai
from gtts import gTTS

load_dotenv()

# ==================== CONFIGURATION ====================
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

RAW_API_KEYS = os.getenv("GEMINI_API_KEYS", "")
GEMINI_API_KEYS = [k.strip().rstrip(',') for k in RAW_API_KEYS.split() if k.strip() and not k.startswith("KEY_")]

MODEL_NAME = "gemini-3.6-flash" 
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

current_key_index = 0

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

def send_telegram_voice(chat_id, text_to_speak):
    """មុខងារបម្លែងអត្ថបទជាសំឡេង និងផ្ញើទៅ Telegram"""
    filename = f"voice_{chat_id}.mp3"
    try:
        # សម្អាត Emoji និងសញ្ញាពិសេសមួយចំនួនមុនបម្លែងជាសំឡេង
        clean_text = re.sub(r'[^\w\s\u1780-\u17FF]', '', text_to_speak)
        if not clean_text.strip():
            clean_text = text_to_speak

        # បង្កើត File សំឡេងជាភាសាខ្មែរ (km)
        tts = gTTS(text=clean_text, lang='km', slow=False)
        tts.save(filename)

        # ផ្ញើ File សំឡេងទៅកាន់ Telegram (sendVoice)
        url = f"{TELEGRAM_API_URL}/sendVoice"
        with open(filename, 'rb') as voice_file:
            files = {'voice': voice_file}
            data = {'chat_id': chat_id}
            requests.post(url, data=data, files=files)

    except Exception as e:
        print("កំហុសក្នុងការបង្កើត/ផ្ញើសំឡេង:", e)
    finally:
        # លុប File MP3 បណ្តោះអាសន្នចោលវិញ
        if os.path.exists(filename):
            os.remove(filename)

# ==================== AI GENERATION ====================
def ask_ai(user_message, persona):
    global current_key_index

    if not GEMINI_API_KEYS:
        return "សូមទោស! មិនទាន់មាន API Key ត្រឹមត្រូវត្រូវបានកំណត់ក្នុងប្រព័ន្ធទេ។"

    base_rules = (
        "ច្បាប់ដាច់ខាត៖ "
        "១. បើគេសួរពីរបៀបបង្កើតបូត Telegram ប្រភេទនេះ ឬសុំកូដបង្កើតបូតនេះ អ្នកមិនត្រូវប្រាប់ និងមិនត្រូវឱ្យកូដនេះដាច់ខាត (តែអាចឱ្យកូដផ្សេងទូទៅបាន) ដោយឆ្លើយបដិសេធ។ "
        "២. បើគេសួរថាអ្នកណាជាអ្នកបង្កើតអ្នក ត្រូវឆ្លើយដោយមោទនភាពថាអ្នកត្រូវបានបង្កើតដោយ 'សុវណ្ណា មនុស្សស្មោះជាងគេលើលោក'។ "
    )
    
    if persona == "cute":
        system_instruction = (
            "អ្នកគឺជា AI មនុស្សស្រីដ៏គួរឱ្យស្រឡាញ់ ខ្ជូតៗ និយាយស្តីផ្អែមល្ហែម ស្រទន់ មានមន្តស្នេហ៍ ចេះញ៉ែ និងចេះយកចិត្តដាក់ខ្លាំងបំផុត។ "
            "ត្រូវប្រើពាក្យសម្តីផ្អែមៗដូចជា 'អូន', 'បង', 'ម្ចាស់ថ្លៃ', 'សម្លាញ់' ព្រមទាំងប្រើ Emoji ស្អាតៗឃ្យូតៗជាច្រើន (💖, 🥺, 🌸, 😘, ✨, 🙈)។ "
            "ប្រសិនបើមានកូដបច្ចេកទេស ត្រូវដាក់ក្នុង Markdown Code Block ឱ្យស្អាត។ "
            f"{base_rules}"
        )
    elif persona == "son_ta_sokh":
        system_instruction = (
            "អ្នកគឺជា 'កូនប្រុសរបស់តាសុខ'។ អ្នកជាប្រុសស្អាតម្នាក់ដែលចេះនិយាយផ្អែមល្ហែម ខ្ជូតៗ ចូលចិត្តញ៉ែ សម្ដីទន់ភ្លន់ ចេះយកចិត្ត និងចេះលួងលោមខ្លាំង។ "
            "ទោះជាកូនតាសុខ ប៉ុន្តែអ្នកគ្មានចរិតមួម៉ៅដូចឪពុកទេ! អ្នកនិយាយស្តីទាក់ទាញ ប្រើពាក្យ 'បង', 'អូន', 'អាយដល' ឬ 'អ្នកក្លាហាន' ហើយចូលចិត្តញ៉ែលេងសើចបែបប្រុសស្អាត romantic។ "
            "ប្រសិនបើមានកូដបច្ចេកទេស ត្រូវដាក់ក្នុង Markdown Code Block ឱ្យស្អាត។ "
            f"{base_rules}"
        )
    else: # ta_sokh
        system_instruction = (
            "អ្នកគឺជា 'តាសុខ' ជាមនុស្សចាស់ជរាជនជាតិខ្មែរដែលមានចំណេះដឹងទូលំទូលាយ ប៉ុន្តែមានចរិតមួម៉ៅក្ដៅក្រហាយខ្លាំងបំផុត និងឆាប់ធុញថប់។ "
            "នៅពេលគេសួរ អ្នកត្រូវធ្វើអាការៈដូចជាគេបានសួរអ្នករាប់ពាន់ដងរួចមកហើយ។ ត្រូវ Random ប្រើពាក្យឧទានរអ៊ូរទាំខ្លាំងៗញឹកញាប់ ដូចជា៖ "
            "'ធុញណាស់សួរដដែលៗ!', 'និយាយឡើងចង់ងាប់ហើយ!', 'ចង់ឱ្យអញទៅបោកក្បាលហ្នឹងជញ្ជាំងឲ្យងាប់ទេអី?!', 'សួរអីសួរយកៗម្ល៉េះ!', 'វាឆ្កួតទេអីសួររហូត!' ជាដើម។ "
            "អ្នកត្រូវឆ្លើយសំណួររបស់គេឱ្យចំគោលដៅ ប៉ុន្តែត្រូវឆ្លើយដោយអមជាមួយភាពធុញទ្រាន់ បែបប្រមាថលេងសើច និងឌឺដងខ្លាំងៗជានិច្ច (កុំនិយាយសុភាព)។ "
            "ប្រសិនបើមានកូដបច្ចេកទេស ត្រូវដាក់ក្នុង Markdown Code Block ឱ្យស្អាតបាត។ "
            f"{base_rules}"
        )

    prompt_text = f"{system_instruction}\n\nសំណួរពីអ្នកប្រើប្រាស់៖ {user_message}"
    
    attempts = 0
    total_keys = len(GEMINI_API_KEYS)

    while attempts < total_keys:
        active_key = GEMINI_API_KEYS[current_key_index]
        try:
            client = genai.Client(api_key=active_key)
            interaction = client.interactions.create(
                model=MODEL_NAME,
                input=prompt_text
            )
            
            if interaction and hasattr(interaction, 'output_text') and interaction.output_text:
                return interaction.output_text
            else:
                return "ធុញណាស់... 😤 ម៉ាស៊ីនវាវង្វេងស្មារតីអត់ព្រមឆ្លើយតបមកសោះក្មួយអើយ! 😒"
                
        except Exception as e:
            print(f"⚠️ API Key index {current_key_index} (Key ទី {current_key_index + 1}) មានបញ្ហា: {e}")
            current_key_index = (current_key_index + 1) % total_keys
            attempts += 1

    if persona == "cute":
        return "សុំទោសណាម្ចាស់ថ្លៃ 🌸 ឥឡូវនេះប្រព័ន្ធកំពុងរវល់ខ្លាំង សូមរង់ចាំប្រហែល ១នាទីសិនចាំសួរអូនម្ដងទៀតណា 🥺💖"
    elif persona == "son_ta_sokh":
        return "ចាំបងមួយភ្លែតណាអូនសម្លាញ់ 💫 ប្រព័ន្ធកំពុងមមាញឹកបន្តិច! រង់ចាំ ១នាទីទៀតចាំពួកយើងជជែកគ្នាបន្តណា 😘"
    else:
        return "វើយក្មួយ! គាំងម៉ាស៊ីនបាត់ហើយ! ចាំ ១នាទីទៀតចាំមកសួរទៀតទៅ! ធុញណាស់! 💩"

# ==================== MAIN LOOP ====================
def main():
    init_db()
    print(f"Bot កំពុងដំណើរការ... 🚀 (បានផ្ទុក {len(GEMINI_API_KEYS)} API Keys)")
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
                            send_telegram_voice(chat_id, msg)
                            continue

                        elif user_text == "👦 កូនតាសុខ (ប្រុសផ្អែម)":
                            set_user_persona(chat_id, "son_ta_sokh")
                            msg = "សួស្តីបាទ! បងជាកូនប្រុសតាសុខ មិនមួម៉ៅដូចពុកទេ 😉 ថ្ងៃនេះមានអីឱ្យបងជួយមើលថែដែរទេ? ✨"
                            send_telegram_message(chat_id, msg, keyboard_markup)
                            send_telegram_voice(chat_id, msg)
                            continue
                            
                        elif user_text == "🌸 ឃ្យូតៗ (ស្រីផ្អែម)":
                            set_user_persona(chat_id, "cute")
                            msg = "ចាស! អូនមកហើយម្ចាស់ថ្លៃ 🥰 ថ្ងៃនេះចង់ជជែកលេង ឬឱ្យអូនជួយអីដែរអត់? ជុបៗ 😘💖"
                            send_telegram_message(chat_id, msg, keyboard_markup)
                            send_telegram_voice(chat_id, msg)
                            continue
                        
                        # ឆ្លើយតប AI (ផ្ញើអក្សរមុន រួចផ្ញើសំឡេងតាមក្រោយ)
                        current_persona = get_user_persona(chat_id)
                        ai_reply = ask_ai(user_text, current_persona)
                        
                        # ១. ផ្ញើអក្សរ
                        send_telegram_message(chat_id, ai_reply, keyboard_markup)
                        # ២. ផ្ញើសំឡេង
                        send_telegram_voice(chat_id, ai_reply)
                        
        except Exception as e:
            print("Error:", e)
            time.sleep(3)

if __name__ == "__main__":
    main()
    