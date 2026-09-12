import os
import time
import requests
import random
from dotenv import load_dotenv
from google import genai

# ទាញយកទិន្នន័យពីឯកសារ .env
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=GEMINI_API_KEY)

# រក្សាទុកម៉ូដែលចាស់តាមការស្នើសុំ
MODEL_NAME = "gemini-3.6-flash" 
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

def ask_ta_sokh_ai(user_message):
    prompt_text = (
        "អ្នកគឺជា 'តាសុខ' ជាមនុស្សចាស់ជរាជនជាតិខ្មែរដែលមានចំណេះដឹងទូលំទូលាយ។ "
        "អ្នកត្រូវតែបង្ហាញអារម្មណ៍កាន់តែធុញទ្រាន់ មួម៉ៅ និងខឹងខ្លាំងឡើងៗរាល់ពេលដែលក្មេងសួរញឹកញាប់ពេក ដោយប្រើពាក្យ 'ធុញណាស់' និងរអ៊ូរទាំបែបឌឺដង។ "
        "ប្រសិនបើក្មេងសួររកកូដ ឬដំណោះស្រាយបច្ចេកទេស ត្រូវសរសេរកូដនោះដាក់ក្នុង Markdown Code Block (```python ... ```) "
        "ឱ្យបានស្អាតបាត និងងាយស្រួល Copy យកទៅប្រើប្រាស់។ "
        f"សំណួរពីក្មេង៖ {user_message}"
    )
    
    try:
        interaction = client.interactions.create(
            model=MODEL_NAME,
            input=prompt_text
        )
        if interaction and hasattr(interaction, 'output_text') and interaction.output_text:
            return interaction.output_text
        else:
            return "ធុញណាស់... 😤 ម៉ាស៊ីនវាវង្វេងស្មារតីអត់ព្រមឆ្លើយតបមកសោះក្មួយអើយ! 😒"
            
    except Exception as e:
        error_msg = str(e)
        # ឆែកមើលថាតើវាជា Error 429 (Too many requests) ដែរឬទេ
        if "429" in error_msg or "too_many_requests" in error_msg.lower():
            # បញ្ជីលេសរបស់តាសុខ ពេលអស់កូតាសួរ
            excuses = [
                "វើយក្មួយ! ទុកពេលឱ្យតាបត់ជើង (ចូលបន្ទប់ទឹក) បន្តិចមើល៍! សួរអីសួរយកៗម្ល៉េះ! ចាំ ១នាទីទៀតចាំមកសួរទៀតទៅ! ធុញណាស់! 💩",
                "អើ! តាកំពុងតែដាំបាយ! កុំទាន់អាលរំខានពេក! ម៉ាស៊ីនវាក្តៅអស់ហើយ ចាំមួយភ្លែត (ប្រហែល១នាទី) សិនទៅ! ធុញម៉ង! 🍚😤",
                "យីក្មេងនេះ! សួរអត់ឱ្យតាស៊ីស្លាមាត់ទេអី? គាំងម៉ាស៊ីនបាត់ហើយ! ទៅលេងណា ១នាទីសិនទៅ ចាំមកសួរទៀត! 😒"
            ]
            # ទាញយកលេសមួយណាក៏បានមកឆ្លើយ
            return random.choice(excuses)
        else:
            # សម្រាប់ Error ផ្សេងៗទៀតដែលមិនមែន 429
            return f"ធុញណាស់ក្មួយអើយ... ម៉ាស៊ីនវាខូចទៀតហើយ! កំហុសវា៖ {error_msg}"

def send_telegram_message(chat_id, text):
    url = f"{TELEGRAM_API_URL}/sendMessage"
    payload = {
        "chat_id": chat_id, 
        "text": text,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload)
        if response.status_code != 200:
            payload.pop("parse_mode", None)
            requests.post(url, json=payload)
    except Exception as e:
        print("កំហុសក្នុងការផ្ញើសារ:", e)

def main():
    print("Telegram Bot 'តាសុខ' កំពុងដំណើរការ... 😤")
    offset = None
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
                        user_text = update["message"]["text"]
                        
                        print(f"ទទួលបានសារពី {chat_id}: {user_text}")
                        
                        ai_reply = ask_ta_sokh_ai(user_text)
                        send_telegram_message(chat_id, ai_reply)
        except Exception as e:
            print("Error:", e)
            time.sleep(3)

if __name__ == "__main__":
    main()
    