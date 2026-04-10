# WhatsApp Audio Transcriber Skill

This skill is designed as an autonomous background script that hooks into a WhatsApp CLI (`wacli`) to fetch new incoming audio messages, transcribes them via **Google Vertex AI** (`gemini-3-flash-preview`), and automatically replies in the WhatsApp chat with the transcribed text.

## Features
- **Asynchronous WhatsApp Sync**: Communicates natively with WhatsApp via the standard bridge `wacli`.
- **Intelligent Speech-to-Text**: Utilizes the Google Vertex AI SDK to send the raw binary audio (`.ogg`) and receive a highly accurate, word-for-word transcript.
- **Auto-Localization**: Gemini detects the language spoken in the audio and automatically adjusts the metadata header of the transcript (e.g. `🔊 Audio from...` or `🔊 Аудио от...`) to match the context.
- **Duplication Safe**: Keeps internal memory of completed tasks (`monitor_v5_state.json`) so it doesn't process the same message twice, even after restarts.

## Prerequisites
- **wacli**: Requires `~/go/bin/wacli` correctly authenticated with an active WhatsApp instance.
- **Google Cloud Auth**: The script relies on Vertex AI, which requires a valid Service Account JSON credential injected via the `GOOGLE_APPLICATION_CREDENTIALS` environment variable, targeting a valid project (e.g., `gen-lang-client-...`).
- **Python 3.11**: Requires the standard SDK `google-genai` installed on the system.

## Configuration & Usage
This tool is deployed as a native macOS daemon (`launchd`). It is designed to run automatically on system boot and restart upon failure.

The daemon configuration is stored in `~/Library/LaunchAgents/com.openclaw.whatsapp-transcriber.plist`.

**To load and start the daemon:**
```bash
launchctl load -w ~/Library/LaunchAgents/com.openclaw.whatsapp-transcriber.plist
```

**Custom Start Time:**
By default, the script starts processing messages from 00:00 (midnight) of the current day. It skips already processed messages using `monitor_v5_state.json`. 
If you want to forcibly transcribe from a specific time today (or skip older ones), you can manually run the script passing the `start-time` flag:
```bash
/opt/homebrew/bin/python3.11 whatsapp_audio_transcriber.py --start-time 11:14
```
*(Optionally, you can add `<string>--start-time</string>` and `<string>11:14</string>` to the `ProgramArguments` in your `launchd` `.plist` file).*
