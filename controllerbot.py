import json, os, subprocess, threading, time
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# --- CONFIGURE THESE ---
BOT_TOKEN = "7794369165:AAHZxoqFtXfsl6F9B6LrrZxHjGeGZXcJ0k8"
AUTHORIZED_USER = 6044257984 # your Telegram ID
COPIER_CMD = ["python", "copier.py", "--auto"]
CONFIG_FILE = "config.json"
PROGRESS_FILE = "progress.json"
PID_FILE = "copier_pid.txt"
# --------------------------

def restricted(func):
    async def wrapper(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != AUTHORIZED_USER:
            await update.message.reply_text("❌ Unauthorized.")
            return
        return await func(update, ctx)
    return wrapper

@restricted
async def start_cmd(update: Update, ctx):
    # If config doesn't exist, run setup
    if not os.path.exists(CONFIG_FILE):
        await update.message.reply_text("⚙️ No config found. Let's set it up.")
        await setup_cmd(update, ctx)
    else:
        await update.message.reply_text("✅ Bot ready. Use /config, /copy, /status, /stop.")

@restricted
async def setup_cmd(update: Update, ctx):
    await update.message.reply_text("🔧 Please enter your API ID:")
    msg = await ctx.bot.wait_for('message', timeout=300)
    api_id = int(msg.text)
    await update.message.reply_text("🔧 Now enter your API Hash:")
    msg = await ctx.bot.wait_for('message', timeout=300)
    api_hash = msg.text
    await update.message.reply_text("🔧 Now enter your phone (+91...):")
    msg = await ctx.bot.wait_for('message', timeout=300)
    phone = msg.text

    # Use Telethon to fetch dialogs
    from telethon import TelegramClient
    client = TelegramClient("anon", api_id, api_hash)
    await client.start(phone=phone)
    dialogs = await client.get_dialogs()
    channels = [d for d in dialogs if d.is_channel and not d.is_user]

    text = "📡 Choose source channel (enter number):\n"
    for i, d in enumerate(channels):
        text += f"{i+1}. {d.name}\n"
    await update.message.reply_text(text)
    msg = await ctx.bot.wait_for('message', timeout=300)
    src = channels[int(msg.text)-1]

    text = "📡 Choose target channel (enter number):\n"
    for i, d in enumerate(channels):
        text += f"{i+1}. {d.name}\n"
    await update.message.reply_text(text)
    msg = await ctx.bot.wait_for('message', timeout=300)
    tgt = channels[int(msg.text)-1]

    config = {
        "api_id": api_id,
        "api_hash": api_hash,
        "phone": phone,
        "source_channel_id": src.id,
        "target_channel_id": tgt.id
    }
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)

    await update.message.reply_text("✅ Configuration saved.")
    await client.disconnect()

@restricted
async def config_cmd(update: Update, ctx):
    if not os.path.exists(CONFIG_FILE):
        return await update.message.reply_text("⚠️ No config set. Use /setup.")
    cfg = json.load(open(CONFIG_FILE))
    await update.message.reply_text("📦 Current Config:\n" + "\n".join(f"{k}: {v}" for k,v in cfg.items()))

@restricted
async def copy_cmd(update: Update, ctx):
    if os.path.exists(PID_FILE):
        return await update.message.reply_text("⚠️ Copier already running.")
    subprocess.Popen(COPIER_CMD)
    await update.message.reply_text("🚀 Copier started. Live updates incoming.")
    threading.Thread(target=progress_updater, args=(ctx,)).start()

def progress_updater(ctx):
    time.sleep(1)
    msg = ctx.bot.send_message(chat_id=AUTHORIZED_USER, text="✅ Starting copy...")
    while os.path.exists(PROGRESS_FILE):
        data = json.load(open(PROGRESS_FILE))
        txt = f"📊 Progress: {data['copied']}/{data['total']}\nStatus: {data['status']}"
        ctx.bot.edit_message_text(chat_id=AUTHORIZED_USER, message_id=msg.message_id, text=txt)
        time.sleep(2)
    final = json.load(open(PROGRESS_FILE)) if os.path.exists(PROGRESS_FILE) else {"status":"Done"}
    ctx.bot.edit_message_text(chat_id=AUTHORIZED_USER, message_id=msg.message_id,
                              text=f"✅ Completed.\n{final['copied']}/{final.get('total','?')}")

@restricted
async def status_cmd(update: Update, ctx):
    if os.path.exists(PROGRESS_FILE):
        data = json.load(open(PROGRESS_FILE))
        await update.message.reply_text(f"📊 Progress: {data['copied']}/{data['total']}\nStatus: {data['status']}")
    else:
        await update.message.reply_text("⚠️ Copier not running.")

@restricted
async def stop_cmd(update: Update, ctx):
    if os.path.exists(PID_FILE):
        pid = int(open(PID_FILE).read())
        try:
            os.kill(pid, 9)
            os.remove(PID_FILE)
            await update.message.reply_text("🛑 Copier stopped.")
        except Exception as e:
            await update.message.reply_text("❌ Stop error: " + str(e))
    else:
        await update.message.reply_text("⚠️ Copier is not running.")

async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("setup", setup_cmd))
    app.add_handler(CommandHandler("config", config_cmd))
    app.add_handler(CommandHandler("copy", copy_cmd))
    app.add_handler(CommandHandler("status", status_cmd))
    app.add_handler(CommandHandler("stop", stop_cmd))
    print("Bot running…")
    await app.run_polling()

if __name__ == "__main__":
    import asyncio; asyncio.run(main())
