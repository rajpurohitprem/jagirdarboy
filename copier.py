import os, json, asyncio, argparse
from telethon import TelegramClient
from telethon.tl.functions.messages import UpdatePinnedMessageRequest
from telethon.tl.types import MessageService
from tqdm import tqdm

CONFIG_FILE = "config.json"
SESSION_FILE = "anon"
SENT_LOG = "sent_ids.txt"
PROGRESS_FILE = "progress.json"
PID_FILE = "copier_pid.txt"

def write_progress(copied, total, status):
    with open(PROGRESS_FILE, "w") as f:
        json.dump({"copied": copied, "total": total, "status": status}, f)

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--auto", action="store_true")
    args = parser.parse_args()
    cfg = json.load(open(CONFIG_FILE))

    client = TelegramClient(SESSION_FILE, cfg["api_id"], cfg["api_hash"])
    await client.start(phone=cfg["phone"])
    open(PID_FILE, "w").write(str(os.getpid()))

    src = await client.get_entity(int(cfg["source_channel_id"]))
    tgt = await client.get_entity(int(cfg["target_channel_id"]))
    msgs = await client.get_messages(src, limit=None)
    msgs = list(reversed(msgs))

    sent = set(open(SENT_LOG).read().split()) if os.path.exists(SENT_LOG) else set()
    total = len(msgs)
    copied = 0
    write_progress(copied, total, "Running")

    for msg in tqdm(msgs):
        copied += 1
        write_progress(copied, total, "Running")
        if msg.id in sent or isinstance(msg, MessageService): continue
        try:
            if msg.media:
                file = await client.download_media(msg)
                await client.send_file(tgt, file, caption=msg.text or "")
                os.remove(file)
            else:
                if msg.text:
                    await client.send_message(tgt, msg.text)
            if msg.pinned:
                last = (await client.get_messages(tgt,1))[0]
                await client(UpdatePinnedMessageRequest(peer=tgt, id=last.id, silent=True))
            open(SENT_LOG, "a").write(str(msg.id)+"\n")
        except:
            pass
        await asyncio.sleep(1)

    write_progress(copied, total, "Completed")
    os.remove(PID_FILE)
    await client.disconnect()

if __name__=="__main__":
    asyncio.run(main())
