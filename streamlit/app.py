import os
import sys
import tempfile
import asyncio
import uuid

import numpy as np
import sounddevice as sd
import soundfile as sf
import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv
import edge_tts

# --- Fix import path: add project root to Python path ---
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

# --- Load environment variables from the project root .env ---
load_dotenv(os.path.join(ROOT_DIR, ".env"))

# Now the env has OPENAI_API_KEY, so this will work
client = OpenAI()  # uses OPENAI_API_KEY from your .env

st.set_page_config(page_title="Chef AI", page_icon="🍳", layout="centered")

st.title("🍳 Chef AI – Your Personal Recipe Assistant")
st.write("Tell me what ingredients you have or what type of recipe you're looking for.")

# --- Debug indicator ---
st.write("App loaded ✅")

# --- Try importing LangGraph workflow ---
try:
    from agents.fetch_recipes.graph import graph, AgentState
except Exception as e:
    st.error("❌ Error importing agents.fetch_recipes.graph")
    st.exception(e)
    st.stop()

def record_audio(duration: int = 5, samplerate: int = 16000):
    """Record audio from the microphone and return a temp .wav file path."""
    st.info(f"Recording for {duration} seconds... Speak now 🎤")
    audio = sd.rec(int(duration * samplerate), samplerate=samplerate, channels=1, dtype="float32")
    sd.wait()

    # Save to a temporary WAV file
    tmp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    sf.write(tmp_file.name, audio, samplerate)
    return tmp_file.name

async def tts_to_file(text: str, out_path: str):
    """Use Edge TTS to synthesize text to an MP3 file."""
    communicate = edge_tts.Communicate(text, "en-US-AriaNeural")
    await communicate.save(out_path)

def generate_tts_file(text: str) -> str | None:
    """Synchronous wrapper for Streamlit. Returns path to MP3."""
    if not text or not text.strip():
        return None
    out_path = os.path.join(
        tempfile.gettempdir(),
        f"chefai_tts_{uuid.uuid4().hex}.mp3"
    )
    asyncio.run(tts_to_file(text, out_path))
    return out_path

# --- Voice input section ---
st.markdown("### 🎤 Voice input (optional)")
col1, col2 = st.columns(2)

with col1:
    record = st.button("Record 5 seconds")

with col2:
    st.write("Or just type below ↓")

# This will hold the text (typed or transcribed) across reruns
if "query_text" not in st.session_state:
    st.session_state["query_text"] = ""

# Store results across reruns
if "recommendations" not in st.session_state:
    st.session_state["recommendations"] = ""
if "recipes" not in st.session_state:
    st.session_state["recipes"] = []
if "has_results" not in st.session_state:
    st.session_state["has_results"] = False

if record:
    try:
        audio_path = record_audio(duration=5)
        with open(audio_path, "rb") as f:
            st.info("Transcribing your speech with Whisper…")
            transcription = client.audio.transcriptions.create(
                model="whisper-1",
                file=f
            )
        st.session_state["query_text"] = transcription.text
        st.success("Transcription complete! You can edit it below if needed.")
    except Exception as e:
        st.error("❌ Error recording or transcribing audio.")
        st.exception(e)

# --- Main user input section ---
query = st.text_area(
    "Enter your ingredients or recipe request:",
    key="query_text",
    placeholder="Example: I have chicken, rice, lemons. What can I cook?"
)

if st.button("Find Recipes"):
    query = st.session_state.get("query_text", "")
    if not query.strip():
        st.warning("Please enter something first.")
    else:
        with st.spinner("Searching your recipe catalog..."):
            try:
                state = AgentState(user_query=query)
                final = graph.invoke(state)   # final is a dict-like state
            except Exception as e:
                st.error("❌ Error running the recipe agent.")
                st.exception(e)
                st.stop()

        # Save results into session_state so they persist on rerun
        st.session_state["recommendations"] = final.get("recommendations", "")
        st.session_state["recipes"] = final.get("filtered_recipes", [])
        st.session_state["has_results"] = True

# --- Show results if we have any saved ---
if st.session_state.get("has_results"):
    recommendations = st.session_state.get("recommendations", "")
    recipes = st.session_state.get("recipes", [])

    # Recommendations text
    st.subheader("🍽️ Recommendations")
    st.write(recommendations)

    # Text-to-speech button
    if recommendations and recommendations.strip():
        if st.button("🔊 Read recommendations aloud"):
            try:
                audio_path = generate_tts_file(recommendations)
                if audio_path:
                    with open(audio_path, "rb") as audio_file:
                        audio_bytes = audio_file.read()
                    st.audio(audio_bytes, format="audio/mp3")
            except Exception as e:
                st.error("❌ Error generating or playing audio.")
                st.exception(e)

    # Recipe list
    st.subheader("📚 Matching Recipes")
    if not recipes:
        st.info("No recipes matched your request.")
    else:
        for recipe in recipes:
            with st.expander(recipe["name"]):

                st.write(f"**Description:** {recipe.get('description', 'No description available')}")
                total_time = (recipe.get("prep_time") or 0) + (recipe.get("cook_time") or 0)
                st.write(
                    f"**Difficulty:** {recipe.get('difficulty', 'N/A')} · "
                    f"**Total Time:** {total_time} min · "
                    f"**Servings:** {recipe.get('servings', 'N/A')}"
                )

                st.write("### 🧂 Ingredients")
                for ing in recipe.get("ingredients", []):
                    qty = ing.get("quantity") or ""
                    unit = ing.get("unit") or ""
                    name = ing.get("ingredient_name") or ""
                    st.write(f"- {qty} {unit} {name}".strip())

                st.write("### 👩‍🍳 Instructions")
                st.write(recipe.get("instructions", "No instructions available."))
