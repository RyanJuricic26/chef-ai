import os
import sys
import tempfile
import asyncio
import uuid

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

# --- Try importing orchestrator workflow ---
try:
    from agents.orchestrator.graph import graph as orchestrator_graph
except Exception as e:
    st.error("❌ Error importing agents.orchestrator.graph")
    st.exception(e)
    st.stop()

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

# Initialize session state
if "query_text" not in st.session_state:
    st.session_state["query_text"] = ""

# Store results across reruns
if "recommendations" not in st.session_state:
    st.session_state["recommendations"] = ""
if "has_results" not in st.session_state:
    st.session_state["has_results"] = False

# Audio input widget
audio_input = st.audio_input("Record your recipe request")

if audio_input is not None:
    try:
        st.info("Transcribing your speech with Whisper…")

        # Save audio to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
            tmp_file.write(audio_input.getvalue())
            tmp_path = tmp_file.name

        # Transcribe using Whisper
        with open(tmp_path, "rb") as f:
            transcription = client.audio.transcriptions.create(
                model="whisper-1",
                file=f
            )

        # Update session state with transcription
        st.session_state["query_text"] = transcription.text
        st.success(f"✅ Transcribed: {transcription.text}")

        # Clean up temp file
        os.unlink(tmp_path)

    except Exception as e:
        st.error("❌ Error transcribing audio.")
        st.exception(e)

# --- Main user input section ---
query = st.text_area(
    "Enter your ingredients or recipe request:",
    key="query_text",
    placeholder="Example: I have chicken, rice, lemons. What can I cook?"
)

if st.button("Submit"):
    query = st.session_state.get("query_text", "")
    if not query.strip():
        st.warning("Please enter something first.")
    else:
        with st.spinner("Processing your request..."):
            try:
                # Invoke the orchestrator graph
                result = orchestrator_graph.invoke({"user_input": query})
            except Exception as e:
                st.error("❌ Error running the Chef AI agent.")
                st.exception(e)
                st.stop()

        # Check intent and handle results
        intent = result.get("intent")

        if intent == "catalog_recipe":
            # Show catalog result
            if result.get("success"):
                st.success(result.get("response"))
                st.session_state["has_results"] = False  # Don't show recipe cards
            else:
                st.error(result.get("response"))
                st.session_state["has_results"] = False

        else:  # fetch_recipes intent
            # Save results into session_state so they persist on rerun
            st.session_state["recommendations"] = result.get("response", "")
            st.session_state["has_results"] = True

# --- Show results if we have any saved ---
if st.session_state.get("has_results"):
    recommendations = st.session_state.get("recommendations", "")

    # Display response
    st.subheader("🍽️ Chef AI Response")
    st.write(recommendations)

    # Text-to-speech button
    if recommendations and recommendations.strip():
        if st.button("🔊 Read response aloud"):
            try:
                audio_path = generate_tts_file(recommendations)
                if audio_path:
                    with open(audio_path, "rb") as audio_file:
                        audio_bytes = audio_file.read()
                    st.audio(audio_bytes, format="audio/mp3")
            except Exception as e:
                st.error("❌ Error generating or playing audio.")
                st.exception(e)
