import os
import json
import asyncio
import argparse
from telethon import TelegramClient
from telethon.tl.functions.messages import UpdatePinnedMessageRequest
from telethon.tl.types import MessageService
from tqdm import tqdm

CONFIG_FILE = "config.json"
SESSION_FILE = "anon"
SENT_LOG = "sent_ids.txt"
ERROR_LOG = "errors.txt"
PROGRESS_FILE = "progress.json"
PID_FILE = "copier_pid.txt"

def read_config():
    return json.load(open(CONFIG_FILE))

def write_progress(data):
    with open(PROGRESS_FILE, "w") as f:
        json.dump(data, f)

async def clone(auto=False):
    cfg = read_config()
    client = TelegramClient(SESSION_FILE, cfg["api_id"], cfg["api_hash"])
    await client.start(phone=cfg["phone"])

    # PID tracking
    open(PID_FILE, "w").write(str(os.getpid()))

    src = await client.get_entity(int(cfg["source_channel_id"]))
    tgt = await client.get_entity(int(cfg["target_channel_id"]))

    msgs = await client.get_messages(src, limit=None)
    msgs = list(reversed(msgs))
    sent = set(open(SENT_LOG).read().split()) if os.path.exists(SENT_LOG) else set()

    total = len(msgs)
    progress = {"copied": 0, "total": total, "status": "Running"}
    write_progress(progress)

    for msg in tqdm(msgs, desc="Copying messages"):
        if msg.id in sent or isinstance(msg, MessageService):
            progress["copied"] += 1
            write_progress(progress)
            continue

        try:
            if msg.media:
                file = await client.download_media(msg)
                await client.send_file(tgt, file, caption=msg.text or "")
                os.remove(file)
            else:
                if msg.text:
                    await client.send_message(tgt, msg.text)

            if msg.pinned:
                last = (await client.get_messages(tgt, 1))[0]
                await client(UpdatePinnedMessageRequest(peer=tgt, id=last.id, silent=True))

            sent.add(str(msg.id))
            open(SENT_LOG, "a").write(str(msg.id) + "\n")
        except Exception as e:
            open(ERROR_LOG, "a").write(f"{msg.id}: {str(e)}\n")

        progress["copied"] += 1
        write_progress(progress)
        await asyncio.sleep(1)

    progress["status"] = "Completed"
    write_progress(progress)
    os.remove(PID_FILE)
    await client.disconnect()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--auto", action="store_true")
    args = parser.parse_args()
    asyncio.run(clone(auto=args.auto))
