"""
WindowClient Discord Admin Bot
pip install discord.py flask requests
python discord_bot.py
"""

import json, os, threading, secrets, string
from datetime import datetime
from flask import Flask, request, jsonify
import discord

BOT_TOKEN  = os.environ.get("BOT_TOKEN", "")
CHANNEL_ID = int(os.environ.get("CHANNEL_ID", "1497653793209192569"))
PORT       = int(os.environ.get("PORT", "5000"))
DB         = "users.json"
KEYS_DB    = "keys.json"
ACCOUNTS   = "accounts.json"

# ── БД ────────────────────────────────────────────────────────────────────────

def load(f=DB):
    if not os.path.exists(f): return {}
    try:
        with open(f, encoding="utf-8") as fp: return json.load(fp)
    except: return {}

def save(db, f=DB):
    with open(f, "w", encoding="utf-8") as fp:
        json.dump(db, fp, indent=2, ensure_ascii=False)

# ── Discord ───────────────────────────────────────────────────────────────────

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
loop   = None

SE = {"active":"✅ Активна","frozen":"❄️ Заморожена",
      "banned":"🚫 Заблокирована","unknown":"❓ Новый"}

def make_embed(u, title="🚀 Запуск клиента"):
    color = {"active":0x3ba55d,"frozen":0x5865f2,
             "banned":0xed4245,"unknown":0x99aab5}.get(u.get("status","unknown"), 0x99aab5)
    e = discord.Embed(title=title, color=color, timestamp=datetime.now())
    e.add_field(name="🆔 UID",     value=f"`{u.get('uid','?')}`",     inline=True)
    e.add_field(name="📋 Статус",  value=SE.get(u.get("status","unknown"),"❓"), inline=True)
    e.add_field(name="👤 Имя",     value=f"`{u.get('name','?')}`",    inline=True)
    e.add_field(name="👾 Ник MC",  value=f"`{u.get('mc','?')}`",      inline=True)
    e.add_field(name="🖥 ПК",      value=f"`{u.get('pc','?')}`",      inline=True)
    e.add_field(name="👤 ОС",      value=f"`{u.get('os_user','?')}`", inline=True)
    e.add_field(name="📦 Версия",  value=f"`{u.get('version','?')}`", inline=True)
    e.add_field(name="📊 Запусков",value=f"`{u.get('launches','?')}`",inline=True)
    e.add_field(name="🕐 Вход",    value=f"`{u.get('last','?')}`",    inline=True)
    e.add_field(name="🔑 HWID",    value=f"`{u.get('hwid','?')}`",    inline=False)
    hw = u.get("hardware","нет данных")
    e.add_field(name="🔧 Железо",  value=f"```{hw}```",               inline=False)
    if u.get("crack_detected"):
        e.add_field(name="⚠️ ВЗЛОМЩИК", value=f"```{u['crack_detected']}```", inline=False)
        e.color = 0xff0000
    return e

class UserView(discord.ui.View):
    def __init__(self, hwid):
        super().__init__(timeout=None)
        self.hwid = hwid

    @discord.ui.button(label="✅ ACTIVE", style=discord.ButtonStyle.success)
    async def active(self, i, b): await self.set_status(i, "active")

    @discord.ui.button(label="❄️ FROZEN", style=discord.ButtonStyle.primary)
    async def frozen(self, i, b): await self.set_status(i, "frozen")

    @discord.ui.button(label="🚫 BANNED", style=discord.ButtonStyle.danger)
    async def banned(self, i, b): await self.set_status(i, "banned")

    @discord.ui.button(label="🔓 UNLOCK", style=discord.ButtonStyle.success)
    async def unlock(self, i, b): await self.set_status(i, "active")

    @discord.ui.button(label="🔄 Обновить", style=discord.ButtonStyle.secondary)
    async def refresh(self, i, b):
        u = load().get(self.hwid)
        if u: await i.response.edit_message(embed=make_embed(u), view=UserView(self.hwid))
        else: await i.response.send_message("Не найден", ephemeral=True)

    async def set_status(self, i, status):
        db = load()
        if self.hwid in db:
            db[self.hwid]["status"] = status
            save(db)
            await i.response.edit_message(embed=make_embed(db[self.hwid]), view=UserView(self.hwid))
        else:
            await i.response.send_message("Не найден", ephemeral=True)

def send_notification(user, title="🚀 Запуск клиента"):
    import asyncio
    async def _send():
        ch = client.get_channel(CHANNEL_ID)
        if ch: await ch.send(embed=make_embed(user, title), view=UserView(user["hwid"]))
    if loop and loop.is_running():
        asyncio.run_coroutine_threadsafe(_send(), loop)

# ── Flask ─────────────────────────────────────────────────────────────────────

app_flask = Flask(__name__)

@app_flask.route("/auth", methods=["POST"])
def auth():
    d      = request.get_json(force=True) or {}
    action = d.get("action", "launch")

    # Вход
    if action == "login":
        accounts = load(ACCOUNTS)
        nick = d.get("nick","").lower()
        pw   = d.get("pass","")
        if nick not in accounts:
            return jsonify({"error": True, "message": "Аккаунт не найден"})
        if accounts[nick]["password"] != pw:
            return jsonify({"error": True, "message": "Неверный пароль"})
        if accounts[nick].get("banned"):
            return jsonify({"error": True, "message": "Аккаунт заблокирован"})
        return jsonify({"ok": True})

    # Регистрация
    if action == "register":
        accounts = load(ACCOUNTS)
        keys_db  = load(KEYS_DB)
        nick = d.get("nick","").lower()
        pw   = d.get("pass","")
        key  = d.get("key","").upper()
        if nick in accounts:
            return jsonify({"error": True, "message": "Ник уже занят"})
        if key not in keys_db:
            return jsonify({"error": True, "message": "Неверный ключ продукта"})
        kd = keys_db[key]
        max_uses = kd.get("max_uses", 1)
        uses     = kd.get("uses", 0)
        if uses >= max_uses:
            return jsonify({"error": True, "message": "Ключ уже использован максимальное кол-во раз"})
        keys_db[key]["uses"]      = uses + 1
        keys_db[key]["used"]      = (uses + 1) >= max_uses
        keys_db[key]["used_by"]   = nick
        keys_db[key]["used_date"] = datetime.now().strftime("%d.%m.%Y")
        save(keys_db, KEYS_DB)
        accounts[nick] = {
            "password": pw, "key": key,
            "expires":  keys_db[key].get("expires",""),
            "created":  datetime.now().strftime("%d.%m.%Y %H:%M"),
            "banned":   False,
        }
        save(accounts, ACCOUNTS)
        import asyncio
        async def _notify():
            ch = client.get_channel(CHANNEL_ID)
            if ch:
                e = discord.Embed(title="🆕 Новая регистрация", color=0x3ba55d, timestamp=datetime.now())
                e.add_field(name="👤 Ник",  value=f"`{nick}`")
                e.add_field(name="🔑 Ключ", value=f"`{key}`")
                e.add_field(name="📅 До",   value=f"`{keys_db[key].get('expires','∞')}`")
                await ch.send(embed=e)
        if loop and loop.is_running():
            asyncio.run_coroutine_threadsafe(_notify(), loop)
        return jsonify({"ok": True})

    # Запуск клиента
    hwid  = d.get("hwid","")
    if not hwid: return jsonify({"status":"error"}), 400
    db    = load()
    user  = db.get(hwid)
    now   = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    crack = d.get("crack_detected")

    if user is None:
        uid  = len(db) + 1
        user = {
            "uid": uid, "hwid": hwid,
            "name":     d.get("client_name","?"),
            "mc":       d.get("username","?"),
            "version":  d.get("version","?"),
            "hardware": d.get("hardware","?"),
            "pc":       d.get("pc_name","?"),
            "os_user":  d.get("os_user","?"),
            "status":   "unknown",
            "launches": 1, "first": now, "last": now,
        }
    else:
        # Проверяем сброс HWID — если флаг стоит, обновляем HWID
        if user.get("hwid_reset") and user.get("hwid_reset_uses", 0) > 0:
            old_hwid = user["hwid"]
            if old_hwid != hwid:
                # Переносим запись на новый HWID
                user["hwid"]             = hwid
                user["hwid_reset_uses"] -= 1
                if user["hwid_reset_uses"] <= 0:
                    user["hwid_reset"] = False
                # Удаляем старый ключ, добавляем новый
                del db[old_hwid]
                db[hwid] = user

        user.update({
            "name":     d.get("client_name", user["name"]),
            "mc":       d.get("username",    user["mc"]),
            "hardware": d.get("hardware",    user["hardware"]),
            "pc":       d.get("pc_name",     user["pc"]),
            "os_user":  d.get("os_user",     user["os_user"]),
            "last":     now,
            "launches": user.get("launches",0)+1,
        })

    if crack:
        user["status"]         = "banned"
        user["crack_detected"] = crack
        db[hwid] = user
        save(db)
        threading.Thread(target=send_notification,
            args=(user, f"⚠️ ВЗЛОМЩИК: {crack}"), daemon=True).start()
        return jsonify({"status": "banned", "uid": user.get("uid",0)})

    db[hwid] = user
    save(db)
    threading.Thread(target=send_notification, args=(user,), daemon=True).start()
    return jsonify({"status": user["status"], "uid": user["uid"]})

# ── Discord команды ───────────────────────────────────────────────────────────

@client.event
async def on_ready():
    global loop
    import asyncio
    loop = asyncio.get_event_loop()
    print(f"[Discord] Бот запущен: {client.user}")

@client.event
async def on_message(message):
    print(f"[MSG] {message.author}: {message.content}")
    if message.author == client.user: return
    if message.guild is None: return

    text = message.content.strip()
    ch   = message.channel

    # !menu
    if text in ("!menu", "!start"):
        db = load()
        a = sum(1 for u in db.values() if u["status"]=="active")
        f = sum(1 for u in db.values() if u["status"]=="frozen")
        b = sum(1 for u in db.values() if u["status"]=="banned")
        n = sum(1 for u in db.values() if u["status"]=="unknown")
        e = discord.Embed(title="👋 WindowClient Admin Panel", color=0x5865f2)
        e.add_field(name="👥 Всего",    value=str(len(db)), inline=True)
        e.add_field(name="✅ Active",   value=str(a),       inline=True)
        e.add_field(name="❄️ Frozen",  value=str(f),       inline=True)
        e.add_field(name="🚫 Banned",  value=str(b),       inline=True)
        e.add_field(name="❓ Unknown", value=str(n),       inline=True)
        e.set_footer(text="!users | !find имя | !uid N | !del uid N | !key дата [N] | !keys | !reg ник | !hwid UID снять/сбросить [N]")
        await ch.send(embed=e)

    # !users
    elif text == "!users":
        db = load(); users = list(db.values())
        if not users: await ch.send("Нет пользователей"); return
        lines = []
        for u in users[:20]:
            em = {"active":"✅","frozen":"❄️","banned":"🚫","unknown":"❓"}.get(u["status"],"❓")
            lines.append(f"{em} **UID {u['uid']}** — `{u['name']}` | `{u['mc']}`")
        e = discord.Embed(title=f"👥 Пользователи ({len(users)})",
                          description="\n".join(lines), color=0x5865f2)
        await ch.send(embed=e)

    # !find имя
    elif text.startswith("!find "):
        q = text[6:].strip().lower()
        for hwid, u in load().items():
            if u["name"].lower()==q or u["mc"].lower()==q:
                await ch.send(embed=make_embed(u), view=UserView(hwid)); return
        await ch.send(f"❌ `{q}` не найден")

    # !uid N
    elif text.startswith("!uid "):
        try:
            uid = int(text[5:].strip())
            for hwid, u in load().items():
                if u.get("uid") == uid:
                    await ch.send(embed=make_embed(u), view=UserView(hwid)); return
            await ch.send(f"❌ UID {uid} не найден")
        except ValueError:
            await ch.send("Использование: !uid 1")

    # !del uid N
    elif text.startswith("!del uid "):
        try:
            uid = int(text[9:].strip())
            db  = load()
            hwid_to_del = None
            user_to_del = None
            for hwid, u in db.items():
                if u.get("uid") == uid:
                    hwid_to_del = hwid
                    user_to_del = u
                    break
            if hwid_to_del is None:
                await ch.send(f"❌ UID {uid} не найден"); return
            del db[hwid_to_del]
            save(db)
            e = discord.Embed(title="🗑️ Аккаунт удалён", color=0xed4245)
            e.add_field(name="UID",  value=f"`{uid}`",                         inline=True)
            e.add_field(name="Имя",  value=f"`{user_to_del.get('name','?')}`", inline=True)
            e.add_field(name="HWID", value=f"`{hwid_to_del}`",                 inline=False)
            await ch.send(embed=e)
        except ValueError:
            await ch.send("Использование: !del uid 1")

    # !key дата [кол-во активаций]  пример: !key 25.05.2026 3
    elif text.startswith("!key"):
        parts = text.split()
        if len(parts) < 2:
            await ch.send("Использование: `!key 25.05.2026` или `!key 25.05.2026 3`"); return

        expires = parts[1]
        if expires != "∞":
            try: datetime.strptime(expires, "%d.%m.%Y")
            except: await ch.send("❌ Формат даты: `!key 25.05.2026`"); return

        max_uses = 1
        if len(parts) >= 3:
            try:
                max_uses = int(parts[2])
                if max_uses < 1: raise ValueError
            except ValueError:
                await ch.send("❌ Кол-во активаций — целое число >= 1"); return

        chars   = string.ascii_uppercase + string.digits
        key     = "-".join("".join(secrets.choice(chars) for _ in range(4)) for _ in range(4))
        keys_db = load(KEYS_DB)
        keys_db[key] = {
            "expires":  expires,
            "created":  datetime.now().strftime("%d.%m.%Y %H:%M"),
            "used":     False,
            "used_by":  None,
            "max_uses": max_uses,
            "uses":     0,
        }
        save(keys_db, KEYS_DB)
        e = discord.Embed(title="🔑 Новый ключ создан", color=0x3ba55d)
        e.add_field(name="Ключ",      value=f"```{key}```",  inline=False)
        e.add_field(name="До",        value=f"`{expires}`",  inline=True)
        e.add_field(name="Активаций", value=f"`{max_uses}`", inline=True)
        e.add_field(name="Создан",    value=f"`{datetime.now().strftime('%d.%m.%Y %H:%M')}`", inline=True)
        await ch.send(embed=e)

    # !hwid UID снять|сбросить [кол-во]
    # !hwid 1 снять       — снять привязку HWID (1 раз)
    # !hwid 1 сбросить 3  — дать 3 сброса HWID
    elif text.startswith("!hwid "):
        parts = text.split()
        if len(parts) < 3:
            await ch.send(
                "Использование:\n"
                "`!hwid 1 снять` — снять привязку HWID (1 раз)\n"
                "`!hwid 1 сбросить 3` — дать 3 сброса HWID"
            ); return

        try:
            uid = int(parts[1])
        except ValueError:
            await ch.send("❌ UID должен быть числом"); return

        action = parts[2].lower()
        db = load()

        # Найти пользователя по UID
        hwid_found = None
        for hwid, u in db.items():
            if u.get("uid") == uid:
                hwid_found = hwid
                break

        if hwid_found is None:
            await ch.send(f"❌ UID {uid} не найден"); return

        u = db[hwid_found]

        if action == "снять":
            # Снимаем привязку — при следующем запуске примет любой HWID
            u["hwid_reset"]      = True
            u["hwid_reset_uses"] = 1
            db[hwid_found] = u
            save(db)
            e = discord.Embed(title="🔓 HWID снят", color=0x3ba55d)
            e.add_field(name="UID",  value=f"`{uid}`",              inline=True)
            e.add_field(name="Имя",  value=f"`{u.get('name','?')}`",inline=True)
            e.add_field(name="Инфо", value="Пользователь может зайти с любого железа **1 раз**", inline=False)
            await ch.send(embed=e)

        elif action == "сбросить":
            count = 1
            if len(parts) >= 4:
                try:
                    count = int(parts[3])
                    if count < 1: raise ValueError
                except ValueError:
                    await ch.send("❌ Кол-во сбросов должно быть числом >= 1"); return

            u["hwid_reset"]      = True
            u["hwid_reset_uses"] = count
            db[hwid_found] = u
            save(db)
            e = discord.Embed(title="🔄 HWID сброшен", color=0x5865f2)
            e.add_field(name="UID",       value=f"`{uid}`",              inline=True)
            e.add_field(name="Имя",       value=f"`{u.get('name','?')}`",inline=True)
            e.add_field(name="Сбросов",   value=f"`{count}`",            inline=True)
            e.add_field(name="Инфо", value=f"Пользователь может сменить железо **{count}** раз(а)", inline=False)
            await ch.send(embed=e)

        else:
            await ch.send("❌ Действие: `снять` или `сбросить`")
        keys_db = load(KEYS_DB)
        if not keys_db: await ch.send("Нет ключей"); return
        lines = []
        for k, v in list(keys_db.items())[:20]:
            uses     = v.get("uses", 1 if v.get("used") else 0)
            max_uses = v.get("max_uses", 1)
            st = "✅" if uses >= max_uses else "🔑"
            by = f" → `{v['used_by']}`" if v.get("used_by") else ""
            lines.append(f"{st} `{k}` до `{v['expires']}` [{uses}/{max_uses}]{by}")
        e = discord.Embed(title=f"🔑 Ключи ({len(keys_db)})",
                          description="\n".join(lines), color=0x5865f2)
        await ch.send(embed=e)

    # !reg ник
    elif text.startswith("!reg "):
        nick     = text[5:].strip().lower()
        accounts = load(ACCOUNTS)
        if nick in accounts:
            await ch.send(f"❌ Ник `{nick}` уже зарегистрирован"); return
        tmp_pass = "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(8))
        accounts[nick] = {
            "password": tmp_pass, "key": "manual",
            "expires":  "∞",
            "created":  datetime.now().strftime("%d.%m.%Y %H:%M"),
            "banned":   False,
        }
        save(accounts, ACCOUNTS)
        e = discord.Embed(title="✅ Пользователь зарегистрирован", color=0x3ba55d)
        e.add_field(name="Ник",    value=f"`{nick}`",     inline=True)
        e.add_field(name="Пароль", value=f"`{tmp_pass}`", inline=True)
        e.set_footer(text="Передай пользователю эти данные")
        await ch.send(embed=e)

if __name__ == "__main__":
    print(f"[*] Запуск на порту {PORT}")

    # Запускаем Flask
    threading.Thread(
        target=lambda: app_flask.run("0.0.0.0", PORT, debug=False, use_reloader=False),
        daemon=True).start()

    # Автозапуск localtunnel (npm install -g localtunnel)
    def start_tunnel():
        try:
            import subprocess, re
            print("[*] Запуск туннеля localtunnel...")
            proc = subprocess.Popen(
                ["lt", "--port", str(PORT)],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
            )
            for line in proc.stdout:
                line = line.strip()
                if line:
                    print(f"[tunnel] {line}")
                    match = re.search(r"https://[^\s]+", line)
                    if match:
                        url = match.group(0)
                        print(f"\n{'='*55}")
                        print(f"[!] ВСТАВЬ В HwidManager.java:")
                        print(f"    {url}/auth")
                        print(f"{'='*55}\n")
        except FileNotFoundError:
            print("[!] localtunnel не найден.")
            print("[!] Установи: npm install -g localtunnel")
            print(f"[!] Или вручную: lt --port {PORT}")
        except Exception as e:
            print(f"[tunnel] Ошибка: {e}")

    threading.Thread(target=start_tunnel, daemon=True).start()

    client.run(BOT_TOKEN)

