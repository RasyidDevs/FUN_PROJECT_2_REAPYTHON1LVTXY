import streamlit as st
import requests
import json
from streamlit_lottie import st_lottie
import re
import os
import tempfile
import whisper
import subprocess

import google.generativeai as genai
import edge_tts
import tempfile
import base64
import os
import asyncio
from langdetect import detect

genai.configure(api_key=st.secrets["GENAI_API_KEY"])
OPENROUTER_API_KEY = st.secrets["OPENROUTER_API_KEY"] 

MODEL = "deepseek/deepseek-chat-v3-0324"
HEADERS = {
    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    "HTTP-Referer": "http://localhost:8501",
    "X-Title": "AI Chatbot",
}
API_URL = "https://openrouter.ai/api/v1/chat/completions"

base_prompt = """You are Youtube video summarizer. You will be taking the transcript text and summarizing the 
entire video and providing the important summary in points within 250 words. Your task is to provide a 
succinct summary of the transcript text extracted from a YouTube video.

**Instructions:**
1. Carefully read through the transcript text to understand the main ideas and topics discussed in the video.
2. Summarize the content by highlighting the most significant points, key takeaways, and noteworthy information.
3. Focus on clarity, conciseness, and relevance in your summary. Ensure that your summary captures the essence of the video content.
4. Aim for a well-structured summary that is easy to follow and provides value to the reader.
5. Language you are using should match the language of the transcript text.
6. Do not include any personal opinions or interpretations; stick to the facts presented in the transcript.
7. Don't say anything besides the summary, do not say "Here is the summary" or "Summary of the video is" or anything like that.
**Summary:**"""



# Cetak hasil mapping


def load_lottie_file(filepath: str):
    with open(filepath, "r") as f:
        return json.load(f)
    
def get_video_id(youtube_url):
    patterns = [
        r"(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([^&]+)",      # watch?v=VIDEO_ID
        r"(?:https?://)?youtu\.be/([^?&]+)",                           # youtu.be/VIDEO_ID
        r"(?:https?://)?(?:www\.)?youtube\.com/embed/([^?&]+)",       # embed/VIDEO_ID
        r"(?:https?://)?(?:www\.)?youtube\.com/v/([^?&]+)",           # /v/VIDEO_ID
        r"(?:https?://)?(?:www\.)?youtube\.com/shorts/([^?&]+)",      # /shorts/VIDEO_ID
        r"(?:https?://)?(?:www\.)?youtube\.com/live/([^?&]+)",        # /live/VIDEO_ID
        r"(?:https?://)?(?:www\.)?youtube\.com/attribution_link\?.*v%3D([^%&]+)"  # attribution_link
    ]
    for pattern in patterns:
        match = re.search(pattern, youtube_url)
        if match:
            return match.group(1)
    return None

def extract_transcript_details(video_id): 
    try:    
        with tempfile.TemporaryDirectory() as tmpdir:
            audio_path = os.path.join(tmpdir, f"{video_id}.mp3")
            ytdlp_cmd = [
                "yt-dlp",
                "-f", "bestaudio",
                "--extract-audio",
                "--audio-format", "mp3",
                f"https://www.youtube.com/watch?v={video_id}",
                "-o", audio_path
            ]
            print(f"[INFO] Menjalankan yt-dlp: {' '.join(ytdlp_cmd)}")
            subprocess.run(ytdlp_cmd, check=True)

            print("[INFO] Memulai transkripsi Whisper...")
            model = whisper.load_model("base") 
            result = model.transcribe(audio_path, fp16=False)
            print("[INFO] Transkripsi selesai.")
            return result["text"]

    except Exception as whisper_error:
        print(f"❌ Gagal mengambil transkrip dengan Whisper: {str(whisper_error)}")
        return None

def generate_gemini_summary(transcript_text):
    model = genai.GenerativeModel("gemini-2.0-flash")
    response = model.generate_content(f"{base_prompt}\n\n{transcript_text}")
    return response.text
#END FUNGSI UNTUK SUMMARIZE YOUTUBE VIDEO

#START FUNGSI UNTUK VOICE RESPONSE
async def generate_speech(text, voice):
    communicate = edge_tts.Communicate(text, voice)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_file:
        await communicate.save(temp_file.name)
        temp_file_path = temp_file.name
    return temp_file_path

def get_audio_player(file_path):
    with open(file_path, "rb") as f:
        data = f.read()
        b64 = base64.b64encode(data).decode()
        return f'<audio autoplay="true" src="data:audio/mp3;base64,{b64}">'
    
def generate_voice(text, voice):
    text_to_speak = (text).translate(str.maketrans('', '', '#-*_😊👋😄😁🥳👍🤩😂😎')) 
    with st.spinner("Generating voice response..."):
        temp_file_path = asyncio.run(generate_speech(text_to_speak, voice)) 
        audio_player_html = get_audio_player(temp_file_path) 
        st.markdown(audio_player_html, unsafe_allow_html=True)
        os.unlink(temp_file_path)
language_voice_map = {}
def load_voice_data():
    global language_voice_map
    with open("language_voice_map.json", "r", encoding="utf-8") as f:
         language_voice_map = json.load(f)
# Load voice data from the file




#END FUNGSI UNTUK VOICE RESPONSE

with st.sidebar:
    st.title("🤖Robora AI")
 
    columns = st.columns(2)
        # animation
    with columns[0]:
        lottie_animation = load_lottie_file("assets/animation.json")
        if lottie_animation:
            st_lottie(lottie_animation, height=100, width=100, quality="high", key="lottie_anim")

    with columns[1]:
         voice_response = st.toggle("Voice Response")
         load_voice_data()
    llm_type = st.radio(label="Select the LLM type:", options=["Chatbot", "Youtube Summarizer"], horizontal=True)
    if llm_type == "Youtube Summarizer":
        url = st.text_input("Enter YT video or Webpage URL:", key="url_to_summarize",
                            help="Only Youtube videos having captions can be summarized.")
        
        summarize_button = st.button("Summarize", type="primary", use_container_width=True, key="summarize")
        video_id = get_video_id(url)        

 
if llm_type == "Youtube Summarizer":
    st.title("🤖Youtube Summarizer")
    st.markdown("This AI is powered by Gemini 2.0")

    if summarize_button:
        if not video_id:
            st.error("❌ URL tidak valid. Silakan masukkan URL YouTube yang valid.")
            st.stop()
        print(f"Video ID: {video_id}")
        with st.spinner("Mengambil detail video..."):
                transcript_snippets = extract_transcript_details(video_id)
        if not transcript_snippets:
            st.stop()
        print(f"Transcript Snippets: {transcript_snippets[:100]}...")  # Print first 100 characters for debugging
        st.image("https://img.youtube.com/vi/" + video_id + "/maxresdefault.jpg", caption="Video Thumbnail", use_container_width=True)
        summary = generate_gemini_summary(transcript_snippets)
        if voice_response:
            detected_lang = detect(summary)
            generate_voice(summary, voice=language_voice_map.get(detected_lang, "en-US-AriaNeural"))            
        st.markdown("### **Summary:**")
        st.markdown(summary)     
        
                
if llm_type == "Chatbot":
  
    st.title("🤖Chatbot")
    st.markdown(f"this ai is powered by {MODEL} via OpenRouter API")
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    
    for chat in st.session_state.chat_history:
        with st.chat_message(chat["role"]):
            st.markdown(chat["content"])


    user_input = st.chat_input("Ketik pesan di sini...")


    if user_input:
        st.chat_message("user").markdown(user_input)
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        with st.spinner("Mengetik..."):
            payload = {
                "model": MODEL,
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": user_input}
                ]
            }
            response = requests.post(API_URL, headers=HEADERS, json=payload)

            if response.status_code == 200:
                bot_reply = response.json()['choices'][0]['message']['content']
            else:
                bot_reply = f"Terjadi kesalahan: {response.status_code} - {response.text}"
            if voice_response:
                detected_lang = detect(bot_reply)
                generate_voice(bot_reply, voice=language_voice_map.get(detected_lang, "en-US-AriaNeural"))
            st.chat_message("assistant").markdown(bot_reply)
            st.session_state.chat_history.append({"role": "assistant", "content": bot_reply})    

   

 