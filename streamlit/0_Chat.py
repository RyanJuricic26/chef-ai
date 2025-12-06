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
st.write("Ask me anything about recipes, ingredients, or cooking!")

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

# Initialize session state for chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

if "awaiting_voice_input" not in st.session_state:
    st.session_state.awaiting_voice_input = False

if "last_audio_bytes" not in st.session_state:
    st.session_state.last_audio_bytes = None

# --- Display chat history ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

        # Add TTS button for assistant messages
        if message["role"] == "assistant" and message.get("content"):
            # Use unique key for each TTS button
            button_key = f"tts_{message.get('id', hash(message['content']))}"
            if st.button("🔊 Read aloud", key=button_key):
                try:
                    audio_path = generate_tts_file(message["content"])
                    if audio_path:
                        with open(audio_path, "rb") as audio_file:
                            audio_bytes = audio_file.read()
                        st.audio(audio_bytes, format="audio/mp3")
                except Exception as e:
                    st.error("❌ Error generating audio.")

# --- Voice input section (collapsible) ---
with st.expander("🎤 Voice Input (optional)", expanded=st.session_state.awaiting_voice_input):
    audio_input = st.audio_input("Record your message")

    if audio_input is not None:
        # Get current audio bytes
        current_audio_bytes = audio_input.getvalue()

        # Only process if this is new audio (different from last time)
        if current_audio_bytes != st.session_state.last_audio_bytes:
            st.session_state.last_audio_bytes = current_audio_bytes

            try:
                st.info("Transcribing your speech...")

                # Save audio to temporary file
                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
                    tmp_file.write(current_audio_bytes)
                    tmp_path = tmp_file.name

                # Transcribe using Whisper
                with open(tmp_path, "rb") as f:
                    transcription = client.audio.transcriptions.create(
                        model="whisper-1",
                        file=f
                    )

                transcribed_text = transcription.text
                st.success(f"✅ Transcribed: {transcribed_text}")

                # Clean up temp file
                os.unlink(tmp_path)

                # Process the transcribed message
                st.session_state.messages.append({"role": "user", "content": transcribed_text})

                with st.spinner("Chef AI is thinking..."):
                    try:
                        # Invoke the orchestrator graph
                        result = orchestrator_graph.invoke({"user_input": transcribed_text})

                        # Get the response
                        response = result.get("response", "Sorry, I couldn't process that request.")

                        # Add assistant response to chat history
                        message_id = str(uuid.uuid4())
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": response,
                            "id": message_id
                        })

                        # Rerun to display new messages
                        st.rerun()

                    except Exception as e:
                        error_msg = f"❌ Error: {str(e)}"
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": error_msg
                        })
                        st.rerun()

            except Exception as e:
                st.error("❌ Error transcribing audio.")
                st.exception(e)

# --- Chat input ---
if prompt := st.chat_input("Ask me about recipes, ingredients, or cooking..."):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Display user message immediately
    with st.chat_message("user"):
        st.markdown(prompt)

    # Get assistant response
    with st.chat_message("assistant"):
        with st.spinner("Chef AI is thinking..."):
            try:
                # Invoke the orchestrator graph
                result = orchestrator_graph.invoke({"user_input": prompt})

                # Get the response
                response = result.get("response", "Sorry, I couldn't process that request.")

                # Display response
                st.markdown(response)

                # Add assistant response to chat history
                message_id = str(uuid.uuid4())
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": response,
                    "id": message_id
                })

            except Exception as e:
                error_msg = f"❌ Error running Chef AI: {str(e)}"
                st.error(error_msg)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error_msg
                })

# --- Sidebar with controls ---
with st.sidebar:
    st.header("Chat Controls")

    if st.button("🗑️ Clear Chat History"):
        st.session_state.messages = []
        st.rerun()

    st.markdown("---")
    st.markdown("### 💡 Try asking:")
    st.markdown("""
    - "I have chicken and garlic, what can I make?"
    - "Show me easy Italian recipes"
    - "How many recipes are in the database?"
    - "What's the average cook time for my recipes?"
    - "Add this recipe: [paste URL]"
    """)

    st.markdown("---")
    st.caption(f"💬 Messages: {len(st.session_state.messages)}")
