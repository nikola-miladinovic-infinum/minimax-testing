import os
import json
import asyncio
import ssl
import time
import requests
import streamlit as st
import websockets
import logging
from dotenv import load_dotenv
from langdetect import detect

# --- CONFIGURATION & LOGGING ---
load_dotenv()
API_KEY = os.getenv("MINIMAX_API_KEY")
VOICE_DIR, MUSIC_DIR, VIDEO_DIR = "voices", "music", "videos"
os.makedirs(VOICE_DIR, exist_ok=True)
os.makedirs(MUSIC_DIR, exist_ok=True)
os.makedirs(VIDEO_DIR, exist_ok=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TTS_URL = "wss://api.minimax.io/ws/v1/t2a_v2"
MUSIC_URL = "https://api.minimax.io/v1/music_generation"
VIDEO_URL = "https://api.minimax.io/v1/video_generation"
VIDEO_QUERY_URL = "https://api.minimax.io/v1/query/video_generation"
FILE_RETRIEVE_URL = "https://api.minimax.io/v1/files/retrieve"

VOICE_ALIASES = {
    "English Expressive Narrator": "English_expressive_narrator",
    "Wise Woman": "Wise_Woman",
    "Deep Voice Man": "Deep_Voice_Man",
    "English Radiant Girl": "English_radiant_girl",
    "Friendly Person": "Friendly_Person"
}

st.set_page_config(page_title="MiniMax Testing", layout="centered")

# --- CORE UTILITIES ---

def get_ssl_context():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx

# --- SPEECH & MUSIC (UNTOUCHED) ---

async def tts_request(text, voice_id):
    headers = {"Authorization": f"Bearer {API_KEY}"}
    audio_data = b""
    try:
        async with websockets.connect(TTS_URL, additional_headers=headers, ssl=get_ssl_context()) as ws:
            conn_resp = json.loads(await ws.recv())
            if conn_resp.get("event") != "connected_success":
                return None, f"Connection Error: {conn_resp}"

            await ws.send(json.dumps({
                "event": "task_start",
                "model": "speech-2.8-hd",
                "voice_setting": {"voice_id": voice_id, "speed": 1.0, "vol": 1.0, "pitch": 0},
                "audio_setting": {"sample_rate": 32000, "bitrate": 128000, "format": "mp3", "channel": 1}
            }))
            
            await ws.send(json.dumps({"event": "task_continue", "text": text}))

            while True:
                resp = json.loads(await ws.recv())
                if "data" in resp and "audio" in resp["data"]:
                    audio_data += bytes.fromhex(resp["data"]["audio"])
                if resp.get("is_final"): break
            
            await ws.send(json.dumps({"event": "task_finish"}))
            return audio_data, None
    except Exception as e:
        return None, str(e)

def generate_music_rest(prompt, lyrics, is_instrumental):
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "music-2.6",
        "prompt": prompt,
        "lyrics": "" if is_instrumental else lyrics,
        "is_instrumental": is_instrumental,
        "audio_setting": {"sample_rate": 44100, "bitrate": 256000, "format": "mp3"},
        "output_format": "url"
    }
    try:
        res = requests.post(MUSIC_URL, headers=headers, json=payload)
        res_json = res.json()
        if res.status_code == 200 and "data" in res_json:
            return res_json["data"].get("audio"), None
        return None, res_json.get("base_resp", {}).get("status_msg", res.text)
    except Exception as e:
        return None, str(e)

# --- VIDEO UTILITIES (UPDATED PER DOCUMENTATION) ---

def submit_video_task(prompt):
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    payload = {
        "prompt": prompt,
        "model": "MiniMax-Hailuo-2.3",
        "duration": 6,
        "resolution": "1080P",
    }
    res = requests.post(VIDEO_URL, headers=headers, json=payload)
    res.raise_for_status()
    return res.json().get("task_id")

def fetch_video_url(file_id):
    headers = {"Authorization": f"Bearer {API_KEY}"}
    params = {"file_id": file_id}
    res = requests.get(FILE_RETRIEVE_URL, headers=headers, params=params)
    res.raise_for_status()
    return res.json()["file"]["download_url"]

# --- UI INTERFACE ---

st.title("MiniMax Testing")

if not API_KEY:
    st.error("Missing MINIMAX_API_KEY in .env file.")
    st.stop()

tab_tts, tab_music, tab_video = st.tabs(["TTS", "MUSIC", "VIDEO"])

# --- TTS TAB ---
with tab_tts:
    voice_alias = st.selectbox("Voice Selection", list(VOICE_ALIASES.keys()))
    user_text = st.text_area("Input Text", height=150, placeholder="Type text here...", key="tts_input")

    if st.button("Generate Audio", type="primary"):
        if not user_text:
            st.warning("Please enter text.")
        else:
            try:
                lang = detect(user_text)
                logger.info(f"Synthesizing {len(user_text)} chars. Detected lang: {lang}")
                st.caption(f"Language Detected: **{lang.upper()}**")
            except:
                logger.warning("Could not detect language.")

            with st.status("Generating Speech...") as status:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                audio_bytes, error = loop.run_until_complete(
                    tts_request(user_text, VOICE_ALIASES[voice_alias])
                )
                
                if audio_bytes:
                    status.update(label="Complete!", state="complete")
                    st.audio(audio_bytes, format="audio/mp3")
                    path = f"{VOICE_DIR}/{int(time.time())}.mp3"
                    with open(path, "wb") as f: f.write(audio_bytes)
                    st.success(f"Saved to: {path}")
                else:
                    status.update(label="Error", state="error")
                    st.error(error)

# --- MUSIC TAB ---
with tab_music:
    st.subheader("AI Composer")
    m_prompt = st.text_input("Style Prompt", value="Lo-fi, Chill, Mediterranean, Acoustic Guitar")
    is_inst = st.checkbox("Instrumental Only", value=True)
    
    m_lyrics = ""
    if not is_inst:
        m_lyrics = st.text_area("Lyrics", height=150, placeholder="[Intro]\n[Verse]\n[Chorus]")

    if st.button("Generate Music", type="primary"):
        with st.status("Composing...") as status:
            audio_url, error = generate_music_rest(m_prompt, m_lyrics, is_inst)
            
            if audio_url:
                status.update(label="Music Ready!", state="complete")
                st.audio(audio_url)
                path = f"{MUSIC_DIR}/{int(time.time())}.mp3"
                r = requests.get(audio_url)
                with open(path, "wb") as f: f.write(r.content)
                st.success(f"Track saved to: {path}")
            else:
                status.update(label="Failed", state="error")
                st.error(f"Music API Error: {error}")

# --- VIDEO TAB (FIXED PER DOCS) ---
with tab_video:
    st.subheader("AI Video Generation")
    v_prompt = st.text_area("Video Prompt", height=150, placeholder="Describe the scene...", key="video_prompt")

    if st.button("Generate Video", type="primary"):
        if not v_prompt:
            st.warning("Please enter a prompt.")
        else:
            with st.status("Initializing video task...") as status:
                try:
                    # Step 1: Submit
                    task_id = submit_video_task(v_prompt)
                    status.update(label=f"Task {task_id} submitted. Polling status...")
                    
                    # Step 2: Poll status
                    file_id = None
                    headers = {"Authorization": f"Bearer {API_KEY}"}
                    while True:
                        time.sleep(10)
                        res = requests.get(VIDEO_QUERY_URL, headers=headers, params={"task_id": task_id})
                        res.raise_for_status()
                        res_data = res.json()
                        current_status = res_data.get("status")
                        status.update(label=f"Current Status: {current_status}")
                        
                        if current_status == "Success":
                            file_id = res_data.get("file_id")
                            break
                        elif current_status == "Fail":
                            st.error(f"Failed: {res_data.get('error_message', 'Unknown error')}")
                            break
                    
                    if file_id:
                        # Step 3: Fetch download URL
                        status.update(label="Retrieving video file...")
                        download_url = fetch_video_url(file_id)
                        
                        status.update(label="Generation Complete!", state="complete")
                        st.video(download_url)
                        
                        # Save Locally
                        path = f"{VIDEO_DIR}/{int(time.time())}.mp4"
                        r = requests.get(download_url)
                        with open(path, "wb") as f: f.write(r.content)
                        st.success(f"Video saved to: {path}")
                        
                except Exception as e:
                    st.error(f"Video Error: {str(e)}")