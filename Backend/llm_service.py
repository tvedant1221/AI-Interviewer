import os
import tempfile
from typing import Optional, Dict, Any
from pathlib import Path


try:
    import google.generativeai as genai
except Exception:
    genai = None

try:
    from faster_whisper import WhisperModel
except Exception:
    WhisperModel = None

try:
    import pyttsx3
    import pythoncom 
except Exception:
    pyttsx3 = None
    pythoncom = None

BASE = Path(__file__).resolve().parent
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-1.5-flash-latest")

def _get_api_key_from_file() -> Optional[str]:
    try:
        env_path = BASE / ".env"
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and line.startswith("GOOGLE_API_KEY"):
                    key, value = line.split("=", 1)
                    return value.strip().strip("'\"")
    except Exception as e:
        print(f"🔴 Could not read GOOGLE_API_KEY from .env file: {e}")
    return None


_whisper_model = None
def _get_whisper_model():
    global _whisper_model
    if _whisper_model is None and WhisperModel is not None:
        _whisper_model = WhisperModel("tiny", device="cpu", compute_type="int8")
    return _whisper_model


def _call_gemini(prompt: str) -> Optional[str]:
    api_key = _get_api_key_from_file()
    if not genai or not api_key:
        print("🔴 Gemini library not found or API key could not be read from .env file.")
        return None
    
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(MODEL_NAME)
        resp = model.generate_content(prompt)

        if hasattr(resp, 'candidates') and resp.candidates and hasattr(resp.candidates[0], 'content') and resp.candidates[0].content.parts:
            return " ".join(p.text for p in resp.candidates[0].content.parts if p.text).strip()
        if hasattr(resp, 'text') and resp.text:
            return resp.text.strip()
            
        print(f"⚠️ Gemini response was empty or in an unexpected format. Full response: {resp}")
        return None
        
    except Exception as e:
        print(f"🔴 CRITICAL ERROR in _call_gemini: {e}")
        return None

def generate_interviewer_text(prompt: str) -> str:
    gem = _call_gemini(prompt)
    if gem:
        return gem
    print("⚠️ Using fallback text because Gemini returned an empty response.")
    return "Can you tell me more about how you use Excel in your work?"


def synthesize_tts_bytes(text: str) -> bytes:
    if pyttsx3 is None or pythoncom is None:
        return f"TTS not available. Text: {text[:500]}".encode("utf-8")
    
    
    pythoncom.CoInitialize()

    fd, tmp_path = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    try:
        engine = pyttsx3.init()
        engine.save_to_file(text, tmp_path)
        engine.runAndWait()
        with open(tmp_path, "rb") as fh:
            return fh.read()
    finally:
        try:
            os.remove(tmp_path)
        except Exception:
            pass


def transcribe_audio_bytes(audio_bytes: bytes, filename_hint: Optional[str] = None, language: str = "en") -> str:
    model = _get_whisper_model()
    if model is None:
        print("🔴 faster-whisper model is not available.")
        return ""
    
    suffix = ".wav"
    fd, tmp_path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    try:
        with open(tmp_path, "wb") as fh:
            fh.write(audio_bytes)

        segments, info = model.transcribe(tmp_path, language=language)
        result_text = " ".join(segment.text for segment in segments).strip()
        return result_text
        
    except Exception as e:
        print(f"Whisper error: {e}")
        return ""
    finally:
        try:
            os.remove(tmp_path)
        except Exception:
            pass


def make_greeting_text(candidate_name: str = "") -> str:
    prompt = ("You are a professional interviewer. Greet the candidate naturally "
              "and ask for their name and a brief description of their Excel experience. "
              "Keep it short and neutral. Do not reveal process or number of questions.")
    return generate_interviewer_text(prompt)

def make_followup_from_intro(intro: str) -> str:
    prompt = f"Candidate intro: \"{intro}\". Write one short neutral follow-up question about their Excel experience. Only return the question."
    return generate_interviewer_text(prompt)

def rephrase_question(question_text: str) -> str:
    prompt = f"Ask the following Excel interview question naturally in one sentence: \"{question_text}\""
    return generate_interviewer_text(prompt)

def make_private_report(session_obj: Dict[str, Any]) -> str:
    lines = []
    for a in session_obj.get("answers", []):
        lines.append(f"Q: {a.get('q_text')} | A: {a.get('transcript')} | Score: {a.get('score')}")
    prompt = "Create a concise private feedback report (2 strengths, 2 improvements) for the following answers:\n" + "\n".join(lines)
    return generate_interviewer_text(prompt)