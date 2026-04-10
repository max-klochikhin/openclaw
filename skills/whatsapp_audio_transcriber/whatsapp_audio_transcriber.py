#!/opt/homebrew/bin/python3.11
"""
Alfred v6.1 — WhatsApp audio transcriber (Vertex AI) + Localized Headers + Sender Name
Monitors incoming WhatsApp voice messages, transcribes via Gemini on Vertex AI, sends reply.
"""
import os
import json
import asyncio
from datetime import datetime, timezone, timedelta

# ──────────────────── CONFIG ───────────────────────────────────────────────

os.environ["GOOGLE_CLOUD_PROJECT"] = "gen-lang-client-0431347096"
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/Users/max/kleinanzeigen_bot/tools/telegram_llm_bot/config/gcloud_credentials.json"

WACLI      = os.path.expanduser("~/go/bin/wacli")
TMP_DIR    = os.path.expanduser("~/.openclaw/workspace/downloads/monitor_v5")
STATE_FILE = os.path.expanduser("~/.openclaw/workspace/monitor_v6_state.json")
LOG_FILE   = os.path.expanduser("~/.openclaw/workspace/wa_monitor_v5.log")
POLL_SEC   = 45
SYNC_TIMEOUT = 50

NAME_CACHE = {} # Cache for JID -> Name

os.makedirs(TMP_DIR, exist_ok=True)

def log(msg: str):
    line = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE) as f:
                data = json.load(f)
            if isinstance(data, list):
                return {"processed": data}
            return data
        except Exception:
            pass
    return {"processed": []}

def save_state(state: dict):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

async def run(cmd: str, timeout: int = 60):
    try:
        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            log(f"⏱️  Timeout ({timeout}s) - KILLED: {cmd[:70]}")
            return None, "", "timeout"
        
        return proc.returncode, stdout.decode("utf-8", errors="replace"), stderr.decode("utf-8", errors="replace")
    except Exception as e:
        log(f"❌ CMD error: {e}")
        return None, "", str(e)

async def transcribe(file_path: str) -> dict | None:
    try:
        from google import genai
        from google.genai import types as gt

        client = genai.Client(
            vertexai=True,
            project="gen-lang-client-0431347096",
            location="global"
        )
        with open(file_path, "rb") as f:
            audio_bytes = f.read()

        response = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: client.models.generate_content(
                model="gemini-3-flash-preview",
                contents=[
                    gt.Part.from_bytes(data=audio_bytes, mime_type="audio/ogg"),
                    "Transcribe the following WhatsApp audio message word-for-word exactly as spoken. "
                    "Detect the primary language spoken. "
                    "Return ONLY valid JSON with two fields: 'language' (the 2-letter ISO 639-1 language code, e.g. 'ru', 'de', 'en') and 'text' (the transcription).",
                ],
                config=gt.GenerateContentConfig(
                    response_mime_type="application/json",
                )
            ),
        )
        return json.loads(response.text.strip())
    except Exception as e:
        log(f"❌ Transcription error (Vertex AI): {e}")
        return None

async def get_sender_name(sender_id: str, chat_name: str, group: bool, from_me: bool) -> str:
    if sender_id in NAME_CACHE:
        return NAME_CACHE[sender_id]

    # Try search for everyone including me
    rc, stdout, _ = await run(f"{WACLI} contacts search '{sender_id}' --json", timeout=10)
    if rc == 0:
        try:
            data = json.loads(stdout)
            contacts = data.get("data", [])
            if contacts:
                name = contacts[0].get("Name") or contacts[0].get("Alias")
                if name:
                    NAME_CACHE[sender_id] = name
                    return name
        except:
            pass
    
    if from_me:
        return "Max Klochikhin"
    
    if not group and chat_name:
        return chat_name
    
    return sender_id.split("@")[0]

async def main():
    log(f"🚀 Alfred v6.1 (Vertex AI mode with Sender Identity) | Project: gen-lang-client-0431347096")

    state = load_state()
    log(f"📋 Already processed: {len(state['processed'])} message(s)")

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-time", type=str, help="Start time in HH:MM format (Berlin time)")
    args = parser.parse_args()

    berlin = timezone(timedelta(hours=2))
    now_berlin = datetime.now(berlin)
    
    if args.start_time:
        try:
            h, m = map(int, args.start_time.split(":"))
            today_start_berlin = now_berlin.replace(hour=h, minute=m, second=0, microsecond=0)
        except Exception:
            log("❌ Invalid --start-time format. Use HH:MM. Falling back to 00:00.")
            today_start_berlin = now_berlin.replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        # Default start from midnight today
        today_start_berlin = now_berlin.replace(hour=0, minute=0, second=0, microsecond=0)

    today_start_utc = today_start_berlin.astimezone(timezone.utc)
    log(f"⏰ Filter: messages after {today_start_berlin.strftime('%H:%M')} Berlin ({today_start_utc.strftime('%H:%M')} UTC)")

    while True:
        try:
            log("─── Sync ───")
            await run(f"{WACLI} sync --timeout 40s", timeout=60)

            rc, stdout, _ = await run(
                f'{WACLI} messages search "audio" --limit 30 --json', timeout=30
            )
            if rc != 0 or not stdout.strip():
                log("⚠️  Search failed or empty — skipping cycle")
                await asyncio.sleep(POLL_SEC)
                continue

            data = json.loads(stdout)
            messages = data.get("data", {}).get("messages", []) or []
            log(f"🔍 {len(messages)} audio messages found")

            new_found = 0
            for msg in reversed(messages):
                m_id = msg.get("MsgID", "")
                chat = msg.get("ChatJID", "")
                ts_raw = msg.get("Timestamp", "")
                from_me = msg.get("FromMe", False)
                sender_id = msg.get("SenderJID") or chat

                if not m_id or m_id in state["processed"]:
                    continue

                try:
                    m_ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
                    if m_ts < today_start_utc:
                        continue
                except Exception:
                    pass

                new_found += 1
                log(f"🔔 NEW: {m_id[:20]}... | chat: {chat[:30]}...")

                audio_path = os.path.join(TMP_DIR, f"{m_id}.ogg")
                dl_rc, _, dl_err = await run(
                    f'{WACLI} media download --chat "{chat}" --id "{m_id}" --output "{audio_path}"',
                    timeout=60,
                )
                if dl_rc != 0 or not os.path.exists(audio_path):
                    log(f"❌ Download failed: {dl_err[:80]}")
                    state["processed"].append(m_id)
                    save_state(state)
                    continue

                log(f"🎙️  Transcribing using Vertex AI...")
                transcript_data = await transcribe(audio_path)

                if not transcript_data or not isinstance(transcript_data, dict):
                    log(f"❌ Transcription empty or invalid format, will retry next cycle")
                    continue

                text = transcript_data.get("text", "")
                lang = transcript_data.get("language", "ru").lower()

                if not text:
                    log(f"❌ Transcription returned no text.")
                    continue

                date_str = m_ts.astimezone(berlin).strftime("%d.%m.%Y")
                time_str = m_ts.astimezone(berlin).strftime("%H:%M")
                
                # Fetch Name
                name = await get_sender_name(sender_id, msg.get("ChatName", ""), chat.endswith("@g.us"), from_me)

                headers = {
                    "ru": f"🔊 Аудио от {name} ({date_str} в {time_str}):",
                    "en": f"🔊 Audio from {name} ({date_str} at {time_str}):",
                    "de": f"🔊 Audio von {name} ({date_str} um {time_str}):",
                    "es": f"🔊 Audio de {name} ({date_str} a las {time_str}):",
                    "fr": f"🔊 Audio de {name} ({date_str} à {time_str}):",
                    "uk": f"🔊 Аудіо від {name} ({date_str} о {time_str}):",
                    "tr": f"🔊 {name} tarafından {date_str} saat {time_str} ses kaydı:"
                }

                header = headers.get(lang.split('-')[0], headers["ru"])
                reply = f"{header}\n\n{text}"

                send_rc, _, send_err = await run(
                    f'{WACLI} send text --to "{chat}" --message "{reply}"',
                    timeout=30,
                )
                if send_rc == 0:
                    log(f"✅ Sent transcription ({lang}) to {chat[:30]}...")
                    state["processed"].append(m_id)
                    save_state(state)
                else:
                    log(f"❌ Send failed: {send_err[:80]}")

            if new_found == 0:
                log("💤 No new messages")

        except json.JSONDecodeError as e:
            log(f"⚠️  JSON parse error: {e}")
        except Exception as e:
            log(f"⚠️  Loop error: {e}")

        await asyncio.sleep(POLL_SEC)

if __name__ == "__main__":
    asyncio.run(main())
