import time
import requests
from google import genai

# --- ការកំណត់ (Configuration) ---
# Token ថ្មីពី BotFather
TELEGRAM_BOT_TOKEN = "8599298931:AAEX8LeIaoibD8Yc4ZnMzbccvcML94pNHNE"
GEMINI_API_KEY = "sk-iOkC7GGfxIQl77Qu0flMmseNBPW6Pf1HV2KfteJBSHT2Kzhk"

# បង្កើត Client ផ្លូវការរបស់ Google GenAI
client = genai.Client(api_key=GEMINI_API_KEY)

# ប្រើប្រាស់ Model តាមការណែនាំរបស់ Google (Gemini 3.6 Flash)
MODEL_NAME = "gpt-5.6-luna"

TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

def ask_ta_sokh_ai(user_message):
    # បញ្ជាស្ដាយ "តាសុខ" 
    prompt_text = (
        "អ្នកគឺជា 'តាសុខ' ជាមនុស្សចាស់ជរាជនជាតិខ្មែរដែលមានចំណេះដឹងទូលំទូលាយ។ "
        "អ្នកត្រូវតែបង្ហាញអារម្មណ៍កាន់តែធុញទ្រាន់ មួម៉ៅ និងខឹងខ្លាំងឡើងៗរាល់ពេលដែលក្មេងសួរញឹកញាប់ពេក ដោយប្រើពាក្យ 'ធុញណាស់' និងរអ៊ូរទាំបែបឌឺដង។ "
        "តឹងរ៉ឹងបំផុត៖ បើសិនជាក្មេងសួរពាក់ព័ន្ធនឹងពាក្យ 'បាក់ទឹកចិត្ត' ហ្នឹង គឺអ្នកត្រូវតែប្រើប្រាស់ឃ្លាពិតប្រាកដនេះថាសុទ្ធសាធដោយហាមកែប្រែខុសសូម្បីតែមួយម៉ាត់៖ "
        "'វាគ្មានទៅបាក់ទឹកចិត្តកណ្ដួយអីទេ បើដកអាភាពអត់ធ្មត់ចូលក្នុងខ្លួនរួចហើយ' រួចចាំបន្តត្អូញត្អែរ និងដោះស្រាយបញ្ហាឱ្យគេតទៅទៀត។ "
        "ប្រសិនបើក្មេងសួររកកូដ ឬដំណោះស្រាយបច្ចេកទេស ត្រូវសរសេរកូដនោះដាក់ក្នុង Markdown Code Block (```python ... ```) "
        "ឱ្យបានស្អាតបាត និងងាយស្រួល Copy យកទៅប្រើប្រាស់។ "
        f"សំណួរពីក្មេង៖ {user_message}"
    )
    
    try:
        # ប្រើប្រាស់ Interactions API តាមការណែនាំរបស់កូដ Error
        interaction = client.interactions.create(
            model=MODEL_NAME,
            input=prompt_text
        )
        if interaction and hasattr(interaction, 'output_text') and interaction.output_text:
            return interaction.output_text
        else:
            return "ធុញណាស់... 😤 ម៉ាស៊ីនវាវង្វេងស្មារតីអត់ព្រមឆ្លើយតបមកសោះក្មួយអើយ! ចង់ទៅបោកក្បាលឱ្យងាប់ទេហ៎ 😒"
    except Exception as e:
        return f"ធុញណាស់... 🤦‍♂️ កំហុសក្នុងការភ្ជាប់ទៅ AI ស្អីគេទេ៖ {str(e)}"

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
    print("Telegram Bot 'តាសុខ' កំពុងដំណើរការដោយរលូន... 😤")
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
    