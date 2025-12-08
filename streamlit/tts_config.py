"""TTS (Text-to-Speech) configuration and utilities for Chef AI"""
import sqlite3
import os
from typing import Optional

# Database path for settings
SETTINGS_DB = os.path.join(os.path.dirname(__file__), "..", "database", "app.db")

# Available Edge TTS voices
AVAILABLE_VOICES = {
    "Aria (Female, US)": "en-US-AriaNeural",
    "Jenny (Female, US)": "en-US-JennyNeural",
    "Guy (Male, US)": "en-US-GuyNeural",
    "Davis (Male, US)": "en-US-DavisNeural",
    "Jane (Female, US)": "en-US-JaneNeural",
    "Jason (Male, US)": "en-US-JasonNeural",
    "Sara (Female, US)": "en-US-SaraNeural",
    "Tony (Male, US)": "en-US-TonyNeural",
    "Nancy (Female, US)": "en-US-NancyNeural",
    "Libby (Female, UK)": "en-GB-LibbyNeural",
    "Ryan (Male, UK)": "en-GB-RyanNeural",
    "Sonia (Female, UK)": "en-GB-SoniaNeural",
}

DEFAULT_VOICE = "en-US-AriaNeural"
DEFAULT_AUTOPLAY = True


def init_settings_table():
    """Initialize the settings table in the database"""
    conn = sqlite3.connect(SETTINGS_DB)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            tts_voice TEXT NOT NULL DEFAULT 'en-US-AriaNeural',
            tts_autoplay INTEGER NOT NULL DEFAULT 1,
            user_id INTEGER DEFAULT 1
        )
    """)

    # Insert default settings if not exists
    cur.execute("""
        INSERT OR IGNORE INTO settings (id, tts_voice, tts_autoplay, user_id)
        VALUES (1, ?, ?, 1)
    """, (DEFAULT_VOICE, 1 if DEFAULT_AUTOPLAY else 0))

    conn.commit()
    conn.close()


def get_tts_settings() -> dict:
    """Get current TTS settings from database"""
    try:
        conn = sqlite3.connect(SETTINGS_DB)
        cur = conn.cursor()

        cur.execute("""
            SELECT tts_voice, tts_autoplay
            FROM settings
            WHERE id = 1
        """)

        result = cur.fetchone()
        conn.close()

        if result:
            return {
                "voice": result[0],
                "autoplay": bool(result[1])
            }
        else:
            # Return defaults if not found
            return {
                "voice": DEFAULT_VOICE,
                "autoplay": DEFAULT_AUTOPLAY
            }
    except Exception as e:
        print(f"Error loading TTS settings: {e}")
        return {
            "voice": DEFAULT_VOICE,
            "autoplay": DEFAULT_AUTOPLAY
        }


def save_tts_settings(voice: str, autoplay: bool) -> bool:
    """Save TTS settings to database"""
    try:
        conn = sqlite3.connect(SETTINGS_DB)
        cur = conn.cursor()

        cur.execute("""
            UPDATE settings
            SET tts_voice = ?, tts_autoplay = ?
            WHERE id = 1
        """, (voice, 1 if autoplay else 0))

        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error saving TTS settings: {e}")
        return False


def get_voice_name_from_code(voice_code: str) -> Optional[str]:
    """Get the friendly voice name from the voice code"""
    for name, code in AVAILABLE_VOICES.items():
        if code == voice_code:
            return name
    return None


# Initialize settings table on import
init_settings_table()
