import os
import json
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
import aiohttp
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

API_TOKEN = os.getenv("API_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_SHEET_NAME = "VoiceTranscripts"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

scope = ["https://spreadsheets.google.com/feeds",
         "https://www.googleapis.com/auth/spreadsheets",
         "https://www.googleapis.com/auth/drive.file",
         "https://www.googleapis.com/auth/drive"]

creds_json = os.getenv("GOOGLE_CREDS_JSON")
creds_dict = json.loads(creds_json)
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
sheet = client.open(GOOGLE_SHEET_NAME).sheet1

async def transcribe_audio(file_path):
    url = 'https://api.openai.com/v1/audio/transcriptions'
    headers = {'Authorization': f'Bearer {OPENAI_API_KEY}'}
    files = {'file': open(file_path, 'rb'), 'model': (None, 'whisper-1')}
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, data=files) as response:
            result = await response.json()
            return result.get('text', '')

@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    await message.reply("Привет! Отправь голосовое сообщение, я расшифрую и передам Герману.")

@dp.message_handler(content_types=types.ContentType.VOICE)
async def handle_voice(message: types.Message):
    file_info = await bot.get_file(message.voice.file_id)
    file_path = file_info.file_path
    downloaded_file = await bot.download_file(file_path)

    temp_filename = f"voice_{message.from_user.id}_{datetime.now().timestamp()}.ogg"
    with open(temp_filename, 'wb') as f:
        f.write(downloaded_file.read())

    transcription = await transcribe_audio(temp_filename)

    sheet.append_row([
        str(datetime.now()),
        message.from_user.full_name,
        transcription
    ])

    await message.reply(f"Твой текст: {transcription}")
    os.remove(temp_filename)

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
