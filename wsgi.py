"""
WSGI entry point для Railway
"""
import os
import threading
from discord_bot import app_flask, client, BOT_TOKEN

# Запускаем Discord бота в отдельном потоке
def start_bot():
    if BOT_TOKEN and BOT_TOKEN != "":
        try:
            client.run(BOT_TOKEN)
        except Exception as e:
            print(f"[!] Discord бот не запустился: {e}")

threading.Thread(target=start_bot, daemon=True).start()

# Экспортируем Flask app для gunicorn
app = app_flask

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run("0.0.0.0", port)
