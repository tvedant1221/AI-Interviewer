# main.py
"""
FastAPI backend: voice-only interview flow with chunked video upload + merging.
"""

import os
import uvicorn



from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Response, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import llm_service
import interview_logic

app = FastAPI(title="AI Interviewer - Voice Only")

# allow local frontend during development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class StartReq(BaseModel):
    name: str


@app.post("/start_session")
def start_session(payload: StartReq):
    """
    Create session and return only greeting.
    Candidate must then record intro before follow-up is generated.
    """
    session = interview_logic.create_session()
    sid = session["session_id"]
    interview_logic.set_candidate_intro(sid, payload.name, "")
    session["state"] = "awaiting_intro"

    greeting = llm_service.make_greeting_text(payload.name)

    return {"session_id": sid, "greeting_text": greeting, "followup_text": ""}


@app.post("/tts_stream")
def tts_stream(text: str = Form(...)):
    """Return WAV bytes for interviewer text (in-memory)."""
    wav_bytes = llm_service.synthesize_tts_bytes(text)
    return Response(content=wav_bytes, media_type="audio/wav")


@app.post("/answer_audio")
async def answer_audio(session_id: str = Form(...), q_id: str = Form(...), file: UploadFile = File(...)):
    """Process candidate audio answer and return next question or end."""
    if session_id not in interview_logic.SESSIONS:
        raise HTTPException(status_code=404, detail="session not found")

    session = interview_logic.SESSIONS[session_id]
    audio_bytes = await file.read()
    transcript = llm_service.transcribe_audio_bytes(audio_bytes, filename_hint=file.filename)
    if not transcript:
        transcript = "[Unintelligible / empty]"

    # Phase 1: Candidate intro
    if session.get("state") == "awaiting_intro":
        session["intro"] = transcript
        session["state"] = "asking_followup"
        followup = llm_service.make_followup_from_intro(transcript)
        session["current_q"] = "intro_followup"
        return {
            "done": False,
            "q_id": "intro_followup",
            "next_question_text": followup,
            "transcript": transcript,
        }

    # Phase 2: Follow-up response
    if session.get("state") == "asking_followup" and q_id == "intro_followup":
        interview_logic.store_intro_followup(session_id, transcript)
        session["state"] = "asking_questions"
        next_q = interview_logic.pop_next_question(session_id)
        if not next_q:
            return {"done": True, "transcript": transcript}
        natural_text = llm_service.rephrase_question(next_q["text"])
        session["current_q"] = next_q["id"]
        return {
            "done": False,
            "q_id": next_q["id"],
            "next_question_text": natural_text,
            "transcript": transcript,
        }

    # Phase 3: Regular hardcoded questions
    entry = interview_logic.evaluate_answer(session_id, q_id, transcript)
    next_q = interview_logic.pop_next_question(session_id)
    if not next_q:
        session["state"] = "finished"
        return {"done": True, "entry": entry, "transcript": transcript}
    natural_text = llm_service.rephrase_question(next_q["text"])
    session["current_q"] = next_q["id"]
    return {
        "done": False,
        "entry": entry,
        "transcript": transcript,
        "next_question_text": natural_text,
        "q_id": next_q["id"],
    }


@app.post("/upload_video")
async def upload_video(session_id: str = Form(...), file: UploadFile = File(...)):
    """Accept a single video chunk and save it."""
    if session_id not in interview_logic.SESSIONS:
        raise HTTPException(status_code=404, detail="session not found")
    data = await file.read()
    chunk_path = interview_logic.save_video_chunk(session_id, file.filename, data)
    return {
        "status": "chunk_saved",
        "path": chunk_path,
        "chunks_count": len(interview_logic.SESSIONS[session_id].get("video_chunks", [])),
    }


@app.post("/end_session")
def end_session(session_id: str = Form(...)):
    """Merge video chunks and generate private report."""
    if session_id not in interview_logic.SESSIONS:
        raise HTTPException(status_code=404, detail="session not found")
    final_video = interview_logic.merge_video_chunks(session_id)
    private_report = llm_service.make_private_report(interview_logic.SESSIONS[session_id])
    transcript_path = interview_logic.finalize_and_save_transcript(session_id, private_report)
    return {"status": "saved", "transcript_path": transcript_path, "video_path": final_video}


@app.get("/questions")
def list_questions():
    """Return admin list of questions."""
    return {"questions": interview_logic.QUESTIONS}


if __name__ == "__main__":
    uvicorn.run("main:app", port=8000, host="127.0.0.1", reload=True)
