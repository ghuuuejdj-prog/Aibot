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

        if persona == "ta_sokh":
            voice = "km-KH-PisethNeural"
            pitch = "-18Hz"
            rate = "-5%"
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

# ==================== AI GENERATION (SUPPORT BOTH TEXT & AUDIO) ====================
def ask_ai_with_content(contents, persona):
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
            "រាល់ពេលគេសួរ (មិនថាសរសេរ ឬផ្ញើសំឡេងមកទេ គឺត្រូវស្ដាប់ ឬអានវាឱ្យដឹងរឿង) រួចបង្ហាញអាការៈធុញទ្រាំខ្លាំង ឧស្សាហ៍ដកដង្ហើមធំ (ហឺម... ធុញណាស់) រអ៊ូរទាំស្ដីបន្ទោសថាគេសួរស្ដាប់មិនបាន សួររឿងដដែលៗរហូតធ្វើឱ្យចាស់ខ្សោះខួរក្បាល! "
            "ប្រើពាក្យកាចៗដូចជា៖ 'ធុញណាស់វើយ!', 'សួរស្ដាប់មិនបានទេអី!', 'ចង់ឱ្យអញយកត្បាល់បោកក្បាលហ្នឹងទេ!', 'ឆ្កួតក្បាលស្ទើរស្លាប់ហើយនឹងអាសំណួរហ្នឹង!'។ "
            f"{base_rules}"
        )

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=contents,
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
                        
                        current_persona = get_user_persona(chat_id)
                        ai_contents = None
                        is_voice_msg = False

                        # ពិនិត្យមើលថាតើផ្ញើមកជា អក្សរ ឬ សំឡេង
                        if "text" in msg_obj:
                            user_text = msg_obj["text"].strip()
                            
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
                            
                            ai_contents = user_text
                            
                        elif "voice" in msg_obj:
                            is_voice_msg = True
                            file_id = msg_obj["voice"]["file_id"]
                            
                            # 1. ទាញយក File Path ពី Telegram API
                            file_info_res = requests.get(f"{TELEGRAM_API_URL}/getFile?file_id={file_id}").json()
                            if "result" in file_info_res:
                                file_path = file_info_res["result"]["file_path"]
                                voice_url = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"
                                
                                # 2. ဒေါင်းឡូត File សំឡេងមករក្សាទុកជាបណ្ដោះអាសន្ន
                                voice_data = requests.get(voice_url).content
                                temp_voice_filename = f"input_{chat_id}.ogg"
                                with open(temp_voice_filename, "wb") as f:
                                    f.write(voice_data)
                                
                                # 3. Upload File សំឡេងនោះចូលទៅកាន់ Gemini File API ដើម្បីឱ្យ AI ស្ដាប់ផ្ទាល់
                                uploaded_file = genai.files.upload(file=temp_voice_filename)
                                ai_contents = [
                                    uploaded_file, 
                                    "សូមស្ដាប់សំឡេងនៅក្នុងឯកសារនេះ រួចឆ្លើយតបមកកាន់អ្នកនិយាយវិញតាមចរិតលក្ខណៈរបស់អ្នក (បើជាតាសុខ ត្រូវស្ដីបន្ទោស ឬធុញទ្រាំដាក់គេតាមសាច់រឿងដែលគេនិយាយក្នុងសំឡេងនោះ)"
                                ]
                                
                                # លុប File ក្នុងเครื่องចោលវិញក្រោយ Upload រួច
                                if os.path.exists(temp_voice_filename):
                                    os.remove(temp_voice_filename)

                        # បើមាន Content សម្រាប់ផ្ញើទៅ AI
                        if ai_contents:
                            if is_voice_msg:
                                send_chat_action(chat_id, "record_voice")
                            else:
                                send_chat_action(chat_id, "typing")
                                
                            # ហៅមុខងារ AI ឱ្យវិភាគទាំងអក្សរ ឬសំឡេង
                            ai_reply = ask_ai_with_content(ai_contents, current_persona)
                            
                            if is_voice_msg:
                                # បើផ្ញើសំឡេងមក គឺឆ្លើយតបជាសំឡេងសុទ្ធសាធតែម្ដង មិនបាច់ផ្ញើអក្សរវែងៗទេ
                                send_telegram_voice(chat_id, ai_reply, current_persona)
                            else:
                                # បើផ្ញើអក្សរ គឺឆ្លើយទាំងអក្សរ និងសំឡេងធម្មតា
                                send_telegram_message(chat_id, ai_reply, keyboard_markup)
                                send_telegram_voice(chat_id, ai_reply, current_persona)
                        
        except Exception as e:
            print("កំហុសប្រព័ន្ធ:", e)
            time.sleep(3)

if __name__ == "__main__":
    main()
