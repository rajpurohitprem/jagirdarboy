import json, os, subprocess, time
from threading import Thread
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext

BOT_TOKEN = "7673016994:AAGdTRce4G2tD5ayeUJxjs1c_AM1ItFV40s"
AUTHORIZED_USER = 6044257984
CONFIG_FILE = "config.json"
COPIER_SCRIPT = "python copier.py --auto"
PROGRESS_FILE = "progress.json"
PID_FILE = "copier_pid.txt"

def restricted(func):
    def wr(update, ctx):
        if update.effective_user.id != AUTHORIZED_USER:
            update.message.reply_text("❌ Unauthorized.")
            return
        return func(update, ctx)
    return wr

@restricted
def start(update: Update, ctx: CallbackContext):
    update.message.reply_text("🤖 Copier Bot ready. Use /copy, /stop, /status.")

@restricted
def show_config(update, ctx):
    cfg = json.load(open(CONFIG_FILE)) if os.path.exists(CONFIG_FILE) else {}
    update.message.reply_text("📤 Config:\n" + "\n".join(f"{k}: {v}" for k,v in cfg.items()))

@restricted
def copy_cmd(update, ctx):
    if os.path.exists(PID_FILE):
        return update.message.reply_text("⚠️ Copier already running.")
    process = subprocess.Popen(COPIER_SCRIPT.split())
    update.message.reply_text("🚀 Copier started.")
    Thread(target=progress_updater, args=(update, ctx)).start()

def progress_updater(update, ctx):
    msg = ctx.bot.send_message(chat_id=AUTHORIZED_USER, text="🔄 Starting...")
    while os.path.exists(PROGRESS_FILE):
        data = json.load(open(PROGRESS_FILE))
        txt = f"📊 Progress: {data['copied']}/{data['total']}\nStatus: {data['status']}"
        ctx.bot.edit_message_text(chat_id=AUTHORIZED_USER, message_id=msg.message_id, text=txt)
        time.sleep(2)
    data = json.load(open(PROGRESS_FILE)) if os.path.exists(PROGRESS_FILE) else {"status":"Not started"}
    ctx.bot.edit_message_text(chat_id=AUTHORIZED_USER, message_id=msg.message_id, text=f"✅ Done. Status: {data['status']}")

@restricted
def status(update, ctx):
    if os.path.exists(PROGRESS_FILE):
        data = json.load(open(PROGRESS_FILE))
        update.message.reply_text(f"📊 {data['copied']}/{data['total']} — {data['status']}")
    else:
        update.message.reply_text("⚠️ No progress file found. Copier not running.")

@restricted
def stop(update, ctx):
    if os.path.exists(PID_FILE):
        pid = int(open(PID_FILE).read())
        try:
            os.kill(pid, 9)
            os.remove(PID_FILE)
            update.message.reply_text("🛑 Copier stopped.")
        except Exception as e:
            update.message.reply_text("❌ Stop failed: " + str(e))
    else:
        update.message.reply_text("⚠️ Copier not running.")

def main():
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("config", show_config))
    dp.add_handler(CommandHandler("copy", copy_cmd))
    dp.add_handler(CommandHandler("status", status))
    dp.add_handler(CommandHandler("stop", stop))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
