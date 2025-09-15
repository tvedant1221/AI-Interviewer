// App.js
import React, { useEffect, useState, useRef } from "react";
import {
  startSession,
  getTTSStream,
  sendAnswerAudio,
  uploadVideoChunk,
  endSession,
  fetchQuestions,
} from "./api";
import Interviewer from "./components/interviewer";
import Recorder from "./components/recorder";
import ProgressBar from "./components/progressbar";
import "./index.css";

function App() {
  const [sessionId, setSessionId] = useState(null);

  const [questionText, setQuestionText] = useState("");
  const [audioBlob, setAudioBlob] = useState(null);

  const [qId, setQId] = useState(null);
  const [progress, setProgress] = useState({ current: 0, total: 0 });
  const [isProcessing, setIsProcessing] = useState(false);
  const [isFinished, setIsFinished] = useState(false);

  const videoRecorderRef = useRef(null);
  const videoStreamRef = useRef(null);

  // Fetch question count on mount for progress bar
  useEffect(() => {
    const loadQuestions = async () => {
      try {
        const res = await fetchQuestions();
        const questions = res.questions || [];
        setProgress((p) => ({ ...p, total: questions.length }));
      } catch (e) {
        console.error("Failed to fetch questions", e);
      }
    };
    loadQuestions();
  }, []);

  // Start session on mount
  useEffect(() => {
    const init = async () => {
      try {
        // Start without candidate intro (intro will be spoken later)
        const data = await startSession("Candidate");
        setSessionId(data.session_id);
        setQuestionText(data.greeting_text || "");

        // Play greeting via TTS
        if (data.greeting_text) {
          const ttsGreeting = await getTTSStream(data.greeting_text);
          setAudioBlob(ttsGreeting);
        }

        // Start video recording
        startChunkedVideoUpload(data.session_id);
      } catch (e) {
        console.error("Failed to start session", e);
      }
    };
    init();

    return () => stopChunkedVideoUpload();
  }, []);

  // Video chunk recording and upload
  const startChunkedVideoUpload = async (sid) => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: true,
        audio: false,
      });
      videoStreamRef.current = stream;
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: "video/webm; codecs=vp8",
      });
      videoRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = async (event) => {
        if (event.data && event.data.size > 0) {
          try {
            await uploadVideoChunk(sid, event.data);
          } catch (e) {
            console.error("Upload chunk failed", e);
          }
        }
      };

      mediaRecorder.start(5000); // emit a chunk every 5s
    } catch (e) {
      console.warn("Could not start video recording:", e);
    }
  };

  const stopChunkedVideoUpload = () => {
    try {
      if (
        videoRecorderRef.current &&
        videoRecorderRef.current.state !== "inactive"
      ) {
        videoRecorderRef.current.stop();
      }
      if (videoStreamRef.current) {
        videoStreamRef.current.getTracks().forEach((t) => t.stop());
      }
    } catch (e) {
      console.error("Stopping video failed", e);
    }
  };

  // Answer handler from Recorder
  const handleAnswer = async (blob) => {
    if (!sessionId || isProcessing) return;

    try {
      setIsProcessing(true); // Disable buttons
      const res = await sendAnswerAudio(sessionId, qId || "intro", blob);

      if (res.done) {
        setQuestionText("✅ Thank you for completing the interview.");
        setAudioBlob(null); // Stop any playing audio
        await handleFinish();
        return;
      }

      if (res.next_question_text) {
        setQuestionText(res.next_question_text);
        const tts = await getTTSStream(res.next_question_text);
        setAudioBlob(tts);
      }

      if (res.q_id) {
        setQId(res.q_id);
      }

      if (res.q_id && res.q_id.startsWith("q")) {
        setProgress((p) => ({
          current: Math.min(p.current + 1, p.total),
          total: p.total,
        }));
      }
    } catch (e) {
      console.error("Answer error", e);
      setQuestionText("Sorry, an error occurred. Please refresh the page."); // User-friendly error
    } finally {
      setIsProcessing(false); // Re-enable buttons
    }
  };

  const handleFinish = async () => {
    try {
      setIsFinished(true); // Mark the interview as over
      stopChunkedVideoUpload();
      if (sessionId) {
        const res = await endSession(sessionId);
        console.log("Interview finalized:", res);
      }
    } catch (e) {
      console.error("Finish error", e);
    }
  };

  return (
    <div className="app">
      <h1>AI Interview</h1>
      <Interviewer text={questionText} audioBlob={audioBlob} />
      
      {/* Show a processing message */}
      {isProcessing && <p className="interviewer-text"><i>Processing...</i></p>}

      {/* Conditionally render the recorder or a final message */}
      {!isFinished ? (
        <Recorder
          onStop={handleAnswer}
          disabled={!sessionId || isProcessing}
        />
      ) : (
        <p className="interviewer-text">This interview has ended.</p>
      )}

      <ProgressBar current={progress.current} total={progress.total} />
    </div>
  );
}

export default App;
