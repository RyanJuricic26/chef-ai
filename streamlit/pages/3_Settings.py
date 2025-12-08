import os
import sys

import streamlit as st
from dotenv import load_dotenv

# --- Fix import path: add project root to Python path ---
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

# Add streamlit directory to path for tts_config import
STREAMLIT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if STREAMLIT_DIR not in sys.path:
    sys.path.insert(0, STREAMLIT_DIR)

# --- Load environment variables from the project root .env ---
load_dotenv(os.path.join(ROOT_DIR, ".env"))

from tts_config import (
    AVAILABLE_VOICES,
    get_tts_settings,
    save_tts_settings,
    get_voice_name_from_code
)

st.set_page_config(page_title="Settings", page_icon="⚙️", layout="wide")

st.title("⚙️ Settings")
st.write("Configure your Chef AI preferences")

# Load current settings
current_settings = get_tts_settings()

# TTS Settings Section
st.header("🔊 Text-to-Speech Settings")

with st.container(border=True):
    st.subheader("Voice Selection")
    st.write("Choose the voice for reading assistant responses aloud.")

    # Get current voice name
    current_voice_name = get_voice_name_from_code(current_settings["voice"])
    if not current_voice_name:
        current_voice_name = list(AVAILABLE_VOICES.keys())[0]

    # Voice dropdown
    selected_voice_name = st.selectbox(
        "Select Voice",
        options=list(AVAILABLE_VOICES.keys()),
        index=list(AVAILABLE_VOICES.keys()).index(current_voice_name) if current_voice_name in AVAILABLE_VOICES.keys() else 0,
        help="Choose from a variety of English voices with different accents and genders"
    )

    selected_voice_code = AVAILABLE_VOICES[selected_voice_name]

    # Autoplay toggle
    st.markdown("---")
    st.subheader("Auto-play Settings")

    autoplay_enabled = st.toggle(
        "🎵 Enable Auto-play",
        value=current_settings["autoplay"],
        help="When enabled, assistant responses will automatically be read aloud"
    )

    if autoplay_enabled:
        st.info("✅ Responses will automatically play when the assistant replies")
    else:
        st.info("ℹ️ You'll need to click the '🔊 Read aloud' button to hear responses")

    # Save button
    st.markdown("---")
    if st.button("💾 Save Settings", type="primary"):
        success = save_tts_settings(selected_voice_code, autoplay_enabled)

        if success:
            st.success("✅ Settings saved successfully!")
            st.balloons()
        else:
            st.error("❌ Failed to save settings. Please try again.")

# Preview Section
st.markdown("---")
st.header("🎧 Voice Preview")

with st.container(border=True):
    st.write("Test the selected voice with a sample message:")

    preview_text = st.text_area(
        "Preview Text",
        value="Hello! I'm Chef AI, your personal recipe assistant. I'm here to help you discover delicious recipes and answer all your cooking questions!",
        height=100
    )

    if st.button("🔊 Preview Voice", type="secondary"):
        if preview_text.strip():
            try:
                import tempfile
                import asyncio
                import uuid
                import edge_tts

                async def tts_to_file(text: str, voice: str, out_path: str):
                    """Use Edge TTS to synthesize text to an MP3 file."""
                    communicate = edge_tts.Communicate(text, voice)
                    await communicate.save(out_path)

                # Generate preview audio
                out_path = os.path.join(
                    tempfile.gettempdir(),
                    f"chefai_preview_{uuid.uuid4().hex}.mp3"
                )

                with st.spinner("Generating preview..."):
                    asyncio.run(tts_to_file(preview_text, selected_voice_code, out_path))

                # Play the audio
                with open(out_path, "rb") as audio_file:
                    audio_bytes = audio_file.read()
                st.audio(audio_bytes, format="audio/mp3", autoplay=True)

                # Clean up
                try:
                    os.unlink(out_path)
                except:
                    pass

            except Exception as e:
                st.error(f"❌ Error generating preview: {str(e)}")
        else:
            st.warning("⚠️ Please enter some text to preview")

# Information Section
st.markdown("---")
st.header("ℹ️ About Text-to-Speech")

with st.expander("📖 How does it work?"):
    st.markdown("""
    **Text-to-Speech (TTS)** allows Chef AI to read responses aloud using natural-sounding voices.

    **Features:**
    - 🗣️ Multiple voice options with different accents and genders
    - 🎵 Auto-play option for hands-free cooking assistance
    - 🔊 Manual play button available on all assistant messages
    - 🌐 Powered by Microsoft Edge TTS for high-quality audio

    **Tips:**
    - Enable auto-play when you're cooking and need hands-free assistance
    - Try different voices to find your favorite
    - Use the preview feature to test voices before saving
    """)

with st.expander("🎭 Available Voices"):
    st.markdown("""
    Our TTS system offers a variety of voices:

    **US English Voices:**
    - Aria, Jenny, Jane, Sara, Nancy (Female)
    - Guy, Davis, Jason, Tony (Male)

    **UK English Voices:**
    - Libby, Sonia (Female)
    - Ryan (Male)

    Each voice has its own unique tone and style. Try them all to find your preference!
    """)

# Footer
st.markdown("---")
st.caption("💡 Tip: Settings are saved automatically and will apply to all future chat sessions!")
