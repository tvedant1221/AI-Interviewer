# interview_logic.py
"""
Session management, scoring, chunked video storage & merging, transcript saving.

- SESSIONS stores in-memory sessions (MVP).
- video chunks stored temporarily under recordings/<session_id>/chunks...
- merge_video_chunks(session_id) will use ffmpeg to concat them into one final file.
"""

import json
import uuid
import os
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

BASE = Path(__file__).resolve().parent
QUESTIONS_PATH = BASE / "questions.json"

# Directories
RECORDINGS_ROOT = Path(os.getenv("RECORDINGS_DIR", str(BASE / "recordings")))
TRANSCRIPTS_DIR = Path(os.getenv("TRANSCRIPTS_DIR", str(BASE / "transcripts")))

RECORDINGS_ROOT.mkdir(parents=True, exist_ok=True)
TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)

# Load questions
with open(QUESTIONS_PATH, "r", encoding="utf-8") as fh:
    QUESTIONS = json.load(fh)

# In-memory sessions
SESSIONS: Dict[str, Dict[str, Any]] = {}

def create_session() -> Dict[str, Any]:
    sid = str(uuid.uuid4())
    session = {
        "session_id": sid,
        "candidate": {"name": "", "intro": ""},
        "step": "INTRO",        # INTRO -> FOLLOWUP_DONE -> QUESTION -> SUMMARY
        "question_index": -1,
        "answers": [],         # each entry: q_id, q_text, transcript, score, evidence, answered_at
        "started_at": datetime.utcnow().isoformat(),
        "ended_at": None,
        "video_chunks": [],    # list of chunk file paths
        "final_video": None,
        "transcript_path": None,
        "final_score": None
    }
    SESSIONS[sid] = session
    # create folder for chunks
    (RECORDINGS_ROOT / sid).mkdir(parents=True, exist_ok=True)
    return session

def set_candidate_intro(session_id: str, name: str, intro_text: str) -> None:
    if session_id not in SESSIONS:
        raise KeyError("session not found")
    SESSIONS[session_id]["candidate"]["name"] = name or ""
    SESSIONS[session_id]["candidate"]["intro"] = intro_text or ""
    SESSIONS[session_id]["step"] = "INTRO"

def store_intro_followup(session_id: str, transcript_text: str) -> None:
    """
    Store the free-form intro follow-up answer (non-scored) into session answers.
    """
    if session_id not in SESSIONS:
        raise KeyError("session not found")
    entry = {
        "q_id": "intro_followup",
        "q_text": "Intro followup",
        "transcript": transcript_text,
        "score": 0.0,
        "evidence": {},
        "answered_at": datetime.utcnow().isoformat()
    }
    SESSIONS[session_id].setdefault("answers", []).append(entry)
    SESSIONS[session_id]["step"] = "FOLLOWUP_DONE"

def pop_next_question(session_id: str) -> Optional[Dict[str, Any]]:
    """Advance to the next question and return it, or None if done."""
    if session_id not in SESSIONS:
        raise KeyError("session not found")
    session = SESSIONS[session_id]
    idx = session.get("question_index", -1) + 1
    if idx >= len(QUESTIONS):
        session["step"] = "SUMMARY"
        session["question_index"] = len(QUESTIONS)
        return None
    session["question_index"] = idx
    session["step"] = "QUESTION"
    return QUESTIONS[idx]

def evaluate_answer(session_id: str, q_id: str, transcript_text: str) -> Dict[str, Any]:
    """
    Keyword-based scoring:
     - 1.0 if any keyword substring appears
     - 0.5 if partial token(s) match
     - 0.0 otherwise
    """
    if session_id not in SESSIONS:
        raise KeyError("session not found")
    q = next((x for x in QUESTIONS if x["id"] == q_id), None)
    if not q:
        raise KeyError("question not found")
    ans_text = (transcript_text or "").strip()
    lower = ans_text.lower()
    matched = []
    for kw in q.get("keywords", []):
        if kw.lower() in lower:
            matched.append(kw)
    score = 0.0
    if matched:
        score = 1.0
    else:
        for kw in q.get("keywords", []):
            parts = [p for p in kw.lower().split() if p]
            for p in parts:
                if p and p in lower:
                    score = max(score, 0.5)
    entry = {
        "q_id": q_id,
        "q_text": q.get("text", ""),
        "transcript": ans_text,
        "score": score,
        "evidence": {"matched": bool(matched), "matched_keywords": matched},
        "answered_at": datetime.utcnow().isoformat()
    }
    SESSIONS[session_id].setdefault("answers", []).append(entry)
    return entry

def save_video_chunk(session_id: str, filename: str, data: bytes) -> str:
    """
    Save a video chunk for the session under recordings/<session_id>/chunks.
    Returns the saved chunk path.
    """
    if session_id not in SESSIONS:
        raise KeyError("session not found")
    session_folder = RECORDINGS_ROOT / session_id
    session_folder.mkdir(parents=True, exist_ok=True)
    # use incremental numbering plus uuid to avoid collisions
    count = len(SESSIONS[session_id].get("video_chunks", []))
    safe_name = f"{count:04d}_{uuid.uuid4().hex}_{Path(filename).name}"
    out_path = session_folder / safe_name
    with open(out_path, "wb") as fh:
        fh.write(data)
    SESSIONS[session_id].setdefault("video_chunks", []).append(str(out_path))
    return str(out_path)

def merge_video_chunks(session_id: str) -> Optional[str]:
    """
    Merge saved chunks into one final <session_id>_final.webm using ffmpeg concat.
    On success, removes chunk files and returns final file path; on failure returns None.
    """
    if session_id not in SESSIONS:
        raise KeyError("session not found")
    chunks: List[str] = SESSIONS[session_id].get("video_chunks", [])
    if not chunks:
        return None
    session_folder = RECORDINGS_ROOT / session_id
    list_txt = session_folder / f"{session_id}_concat_list.txt"
    # ffmpeg requires list with "file '<path>'" entries
    with open(list_txt, "w", encoding="utf-8") as fh:
        for p in chunks:
            # 1. Escape the single quotes first and store in a new variable.
            escaped_path = p.replace("'", "'\\''")
            
            # 2. Use the new, clean variable in the f-string.
            fh.write(f"file '{escaped_path}'\n")
    final_path = RECORDINGS_ROOT / f"{session_id}_final.webm"
    # run ffmpeg
    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_txt),
        "-c", "copy", str(final_path)
    ]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except Exception as e:
        # merging failed
        # optionally keep chunks for debugging
        return None
    # cleanup chunks and list file
    for p in chunks:
        try:
            os.remove(p)
        except Exception:
            pass
    try:
        os.remove(list_txt)
    except Exception:
        pass
    # update session
    SESSIONS[session_id]["video_chunks"] = []
    SESSIONS[session_id]["final_video"] = str(final_path)
    return str(final_path)

def finalize_and_save_transcript(session_id: str, private_report_text: str) -> str:
    """
    Compose transcript and private report and save to TRANSCRIPTS_DIR/<session_id>.txt
    """
    if session_id not in SESSIONS:
        raise KeyError("session not found")
    session = SESSIONS[session_id]
    lines: List[str] = []
    lines.append(f"=== AI Excel Interview — Session {session_id} ===")
    lines.append(f"Start: {session.get('started_at')}")
    lines.append(f"Candidate: {session['candidate'].get('name','')}")
    lines.append(f"Intro: {session['candidate'].get('intro','')}")
    lines.append("")
    total = 0.0
    answers = session.get("answers", [])
    for idx, a in enumerate(answers, start=1):
        lines.append(f"Q{idx}: {a.get('q_text','')}")
        lines.append(f"A{idx}: {a.get('transcript','')}")
        lines.append(f"Score: {a.get('score')}")
        lines.append(f"Evidence: matched={a['evidence'].get('matched')} matched_keywords={a['evidence'].get('matched_keywords')}")
        lines.append("")
        total += float(a.get("score", 0.0))
    max_score = len(answers)
    lines.append("--- PRIVATE FEEDBACK (authorized personnel only) ---")
    lines.append(private_report_text or "")
    lines.append("")
    lines.append(f"Final Score: {total}/{max_score}")
    lines.append(f"Final Video: {session.get('final_video')}")
    lines.append(f"Saved at: {datetime.utcnow().isoformat()}")
    out_text = "\n".join(lines)
    out_path = TRANSCRIPTS_DIR / f"{session_id}.txt"
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(out_text)
    session["transcript_path"] = str(out_path)
    session["final_score"] = total
    session["ended_at"] = datetime.utcnow().isoformat()
    return str(out_path)
