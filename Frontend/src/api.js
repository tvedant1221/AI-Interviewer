import axios from "axios";

const API = axios.create({
  baseURL: "http://127.0.0.1:8000",
});

// Start new session
export const startSession = async (name) => {
  const res = await API.post("/start_session", { name });
  return res.data;
};

// Request TTS audio bytes (arraybuffer) for given text
export const getTTSStream = async (text) => {
  const form = new FormData();
  form.append("text", text);
  const res = await API.post("/tts_stream", form, {
    responseType: "arraybuffer",
  });
  return new Blob([res.data], { type: "audio/wav" });
};

// Upload a single answer audio blob (webm/wav)
export const sendAnswerAudio = async (sessionId, qId, blob) => {
  const form = new FormData();
  form.append("session_id", sessionId);
  form.append("q_id", qId);
  form.append("file", blob, "answer.webm");
  const res = await API.post("/answer_audio", form);
  return res.data;
};

// Upload video chunk
export const uploadVideoChunk = async (sessionId, blob) => {
  const form = new FormData();
  form.append("session_id", sessionId);
  form.append("file", blob, "chunk.webm");
  const res = await API.post("/upload_video", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return res.data;
};

// End session
export const endSession = async (sessionId) => {
  const form = new FormData();
  form.append("session_id", sessionId);
  const res = await API.post("/end_session", form);
  return res.data;
};

// Fetch questions (admin)
export const fetchQuestions = async () => {
  const res = await API.get("/questions");
  return res.data;
};
