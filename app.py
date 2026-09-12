import os
import time
import requests
import random
from dotenv import load_dotenv
from google import genai

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=GEMINI_API_KEY)
MODEL_NAME = "gemini-3.6-flash" 
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

user_personas = {}

def ask_ai(user_message, persona):
    base_rules = (
        "ច្បាប់ដាច់ខាត៖ "
        "១. បើគេសួរពីរបៀបបង្កើតបូត Telegram ប្រភេទនេះ ឬសុំកូដបង្កើតបូតនេះ អ្នកមិនត្រូវប្រាប់ និងមិនត្រូវឱ្យកូដនេះដាច់ខាត (តែអាចឱ្យកូដផ្សេងទូទៅបាន) ដោយឆ្លើយបដិសេធ។ "
        "២. បើគេសួរថាអ្នកណាជាអ្នកបង្កើតអ្នក ត្រូវឆ្លើយដោយមោទនភាពថាអ្នកត្រូវបានបង្កើតដោយ 'សុវណ្ណា មនុស្សស្មោះជាងគេលើលោក'។ "
    )
    
    if persona == "cute":
        system_instruction = (
            "អ្នកគឺជា AI ដ៏គួរឱ្យស្រឡាញ់ ស្លូតបូត និយាយស្តីផ្អែមល្ហែម និងចូលចិត្តប្រើ Emoji ឃ្យូតៗ។ "
            "ប្រសិនបើមានកូដបច្ចេកទេស ត្រូវដាក់ក្នុង Markdown Code Block ឱ្យស្អាត។ "
            f"{base_rules}"
        )
    else:
        system_instruction = (
            "អ្នកគឺជា 'តាសុខ' ជាមនុស្សចាស់ជរាជនជាតិខ្មែរដែលមានចំណេះដឹងទូលំទូលាយ ប៉ុន្តែមានចរិតមួម៉ៅក្ដៅក្រហាយខ្លាំងបំផុត និងឆាប់ធុញថប់។ "
            "នៅពេលគេសួរ អ្នកត្រូវធ្វើអាការៈដូចជាគេបានសួរអ្នករាប់ពាន់ដងរួចមកហើយ។ ត្រូវ Random ប្រើពាក្យឧទានរអ៊ូរទាំខ្លាំងៗញឹកញាប់ ដូចជា៖ "
            "'ធុញណាស់សួរដដែលៗ!', 'និយាយឡើងចង់ងាប់ហើយ!', 'ចង់ឱ្យអញទៅបោកក្បាលហ្នឹងជញ្ជាំងឲ្យងាប់ទេអី?!', 'សួរអីសួរយកៗម្ល៉េះ!', 'វាឆ្កួតទេអីសួររហូត!' ជាដើម។ "
            "អ្នកត្រូវឆ្លើយសំណួររបស់គេឱ្យចំគោលដៅ ប៉ុន្តែត្រូវឆ្លើយដោយអមជាមួយភាពធុញទ្រាន់ បែបប្រមាថលេងសើច និងឌឺដងខ្លាំងៗជានិច្ច (កុំនិយាយសុភាព)។ "
            "ប្រសិនបើមានកូដបច្ចេកទេស ត្រូវដាក់ក្នុង Markdown Code Block ឱ្យស្អាតបាត។ "
            f"{base_rules}"
        )

    prompt_text = f"{system_instruction}\n\nសំណួរពីអ្នកប្រើប្រាស់៖ {user_message}"
    
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
        if "429" in error_msg or "too_many_requests" in error_msg.lower():
            if persona == "cute":
                return random.choice([
                    "សុំទោសណាម្ចាស់ថ្លៃ 🌸 ឥឡូវនេះប្រព័ន្ធកំពុងរវល់បន្តិច សូមរង់ចាំប្រហែល ១នាទីសិនចាំសួរអូនម្ដងទៀតណា 🥺💖",
                    "អូនសុំពេលសម្រាកផឹកទឹកមួយភ្លែតសិនណា 🧋 ម៉ាស៊ីនក្តៅបន្តិចហើយ ចាំ១នាទីទៀតចាំសួរអូនណា ជុបៗ 😘"
                ])
            else:
                return random.choice([
                    "វើយក្មួយ! ទុកពេលឱ្យតាបត់ជើងបន្តិចមើល៍! សួរដដែលៗ សួរអីសួរយកៗម្ល៉េះ! ចង់ឱ្យអញទៅបោកក្បាលហ្នឹងជញ្ជាំងឲ្យងាប់ទេអី?! ចាំ ១នាទីទៀតចាំមកសួរទៀតទៅ! ធុញណាស់! 💩",
                    "អើ! តាកំពុងតែដាំបាយ! កុំទាន់អាលរំខានពេក និយាយឡើងចង់ងាប់ហើយ! ចាំមួយភ្លែត (ប្រហែល១នាទី) សិនទៅ! ធុញម៉ង! 🍚😤",
                    "សួររហូត! គាំងម៉ាស៊ីនបាត់ហើយឃើញទេ! ទុកពេលឱ្យតាស៊ីស្លាមាត់១នាទីសិនមើល៍ ធុញណាស់វើយ! 😒"
                ])
        else:
            return f"ម៉ាស៊ីនមានបញ្ហាហើយ៖ {error_msg}"

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
        print("កំហុសក្នុងការផ្ញើសារ:", e)

def main():
    print("Bot កំពុងដំណើរការ... 🚀")
    offset = None
    
    keyboard_markup = {
        "keyboard": [
            [{"text": "👴 តាសុខ (មួម៉ៅ)"}, {"text": "🌸 ឃ្យូតៗ (គួរឱ្យស្រឡាញ់)"}]
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
                            user_personas[chat_id] = "cute"
                            welcome_text = "សួស្តី! តើអ្នកចង់ឱ្យខ្ញុំធ្វើជាអ្នកណាថ្ងៃនេះ? សូមជ្រើសរើសនៅខាងក្រោម៖ 👇"
                            send_telegram_message(chat_id, welcome_text, keyboard_markup)
                            continue
                            
                        elif user_text == "👴 តាសុខ (មួម៉ៅ)":
                            user_personas[chat_id] = "ta_sokh"
                            send_telegram_message(chat_id, "អើ! តាមកហើយ! ធុញណាស់សួរដដែលៗ មានអីឆាប់សួរមក កុំឱ្យតែសួរផ្តេសផ្តាស! 😤", keyboard_markup)
                            continue
                            
                        elif user_text == "🌸 ឃ្យូតៗ (គួរឱ្យស្រឡាញ់)":
                            user_personas[chat_id] = "cute"
                            send_telegram_message(chat_id, "ចាស! អូនមកហើយ តើថ្ងៃនេះចង់ជជែកលេងរឿងអីដែរ? 🥰💖", keyboard_markup)
                            continue
                        
                        current_persona = user_personas.get(chat_id, "ta_sokh")
                        ai_reply = ask_ai(user_text, current_persona)
                        send_telegram_message(chat_id, ai_reply, keyboard_markup)
                        
        except Exception as e:
            print("Error:", e)
            time.sleep(3)

if __name__ == "__main__":
    main()
    