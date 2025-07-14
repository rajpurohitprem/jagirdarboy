import json
import os
import asyncio
import subprocess
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters,
)

# Replace with your actual Telegram ID (get it from @userinfobot or print it once)
AUTHORIZED_USER_ID = 6044257984  # ← change this!

CONFIG_FILE = "config.json"
copier_process = None
copier_running = False
status_message_id = None

def is_authorized(update: Update) -> bool:
    return update.effective_user and update.effective_user.id == AUTHORIZED_USER_ID

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {}

def save_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=2)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        await update.message.reply_text("❌ Unauthorized.")
        return

    keyboard = [["Run Copier"], ["Edit Config"], ["Edit Channels"], ["/stop"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        "Welcome to the Telegram Copier Bot.\nUse the buttons below to control:",
        reply_markup=reply_markup
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        await update.message.reply_text("❌ Unauthorized.")
        return

    text = update.message.text.lower()

    if "run" in text:
        await run_copier_async(update, context)
    elif "edit config" in text:
        await handle_config(update, context)
    elif "edit channels" in text:
        await handle_channels(update, context)
    else:
        await update.message.reply_text("❓ Unknown command. Use buttons.")

async def handle_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send your API ID:")
    response = await context.bot.wait_for_message(chat_id=update.effective_chat.id)
    api_id = int(response.text)

    await update.message.reply_text("Send your API Hash:")
    response = await context.bot.wait_for_message(chat_id=update.effective_chat.id)
    api_hash = response.text.strip()

    await update.message.reply_text("Send your phone number with country code:")
    response = await context.bot.wait_for_message(chat_id=update.effective_chat.id)
    phone = response.text.strip()

    config = load_config()
    config.update({
        "api_id": api_id,
        "api_hash": api_hash,
        "phone": phone
    })
    save_config(config)

    await update.message.reply_text("✅ API credentials saved.")

async def handle_channels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send new source channel (username or link):")
    response = await context.bot.wait_for_message(chat_id=update.effective_chat.id)
    source = response.text.strip()

    await update.message.reply_text("Send new target channel (username or link):")
    response = await context.bot.wait_for_message(chat_id=update.effective_chat.id)
    target = response.text.strip()

    config = load_config()
    config.update({
        "source_channel": source,
        "target_channel": target
    })
    save_config(config)

    await update.message.reply_text("✅ Source and target channels updated.")

async def run_copier_async(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global copier_process, copier_running, status_message_id

    if copier_running:
        await update.message.reply_text("⚠ Copier already running.")
        return

    await update.message.reply_text("🚀 Starting copier...")

    copier_running = True
    status_message = await update.message.reply_text("⌛ Running...")
    status_message_id = status_message.message_id

    async def run():
        global copier_process, copier_running

        copier_process = await asyncio.create_subprocess_exec(
            "python", "copier.py",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        while True:
            line = await copier_process.stdout.readline()
            if not line:
                break
            text = line.decode().strip()
            try:
                await context.bot.edit_message_text(
                    chat_id=update.effective_chat.id,
                    message_id=status_message_id,
                    text=f"📦 {text}"
                )
            except:
                pass

        stdout, stderr = await copier_process.communicate()
        copier_running = False

        result = stdout.decode() + stderr.decode()
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="✅ Copier finished.\n\n" + result[-4000:]  # last output
        )

    asyncio.create_task(run())

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global copier_process, copier_running

    if not is_authorized(update):
        await update.message.reply_text("❌ Unauthorized.")
        return

    if copier_running and copier_process:
        copier_process.terminate()
        copier_running = False
        await update.message.reply_text("🛑 Copier stopped.")
    else:
        await update.message.reply_text("⚠ Copier not running.")

async def main():
    with open("bot_token.txt") as f:
        BOT_TOKEN = f.read().strip()

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot running…")
    await app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
