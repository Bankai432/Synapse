# ──────────────────────────────────────────────────────────────
# Nanonautics ALS — Transcription Agent (Groq Whisper)
# ──────────────────────────────────────────────────────────────

import base64
import io
import logging
import os
import tempfile
from groq import AsyncGroq
from config import GROQ_WHISPER_MODEL

log = logging.getLogger(__name__)

_client: AsyncGroq | None = None

def _get_client() -> AsyncGroq:
    global _client
    if _client is None:
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY is not set.")
        _client = AsyncGroq(api_key=api_key)
    return _client

async def transcribe_audio(base64_audio: str) -> str:
    """Transcribe base64 encoded audio using Groq Whisper.
    
    Expects a data URL or raw base64 string.
    """
    try:
        if "," in base64_audio:
            base64_audio = base64_audio.split(",")[1]
            
        audio_bytes = base64.b64decode(base64_audio)
        
        # Whisper requires a filename/extension to hint the format.
        # We'll use .webm as it's common for MediaRecorder.
        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name
            
        try:
            client = _get_client()
            with open(tmp_path, "rb") as file:
                transcription = await client.audio.transcriptions.create(
                    file=(tmp_path, file.read()),
                    model=GROQ_WHISPER_MODEL,
                    response_format="text",
                )
            return transcription.strip()
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
                
    except Exception as e:
        log.error(f"Transcription failed: {e}")
        return ""
