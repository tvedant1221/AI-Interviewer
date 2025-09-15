import React, { useEffect, useRef, useState } from "react";

const Interviewer = ({ text, audioBlob }) => {
  const audioRef = useRef(null);
  const [speaking, setSpeaking] = useState(false);
  const [audioSrc, setAudioSrc] = useState(null);

  useEffect(() => {
    let objectUrl = null;
    if (audioBlob) {
      objectUrl = URL.createObjectURL(audioBlob);
      setAudioSrc(objectUrl);
    }

    return () => {
      if (objectUrl) {
        URL.revokeObjectURL(objectUrl);
      }
    };
  }, [audioBlob]);

  const handleCanPlay = () => {
    // Attempt to play when the audio is ready
    if (audioRef.current) {
      audioRef.current.play()
        .catch(error => console.warn("Audio autoplay was prevented by browser.", error));
    }
  };

  return (
    <div className="interviewer">
      <div className={`logo-wrapper ${speaking ? "speaking" : ""}`}>
        <img src="/logo.png" alt="AI Logo" className="logo" />
        <div className="ring"></div>
      </div>
      <p className="interviewer-text">{text}</p>
      <audio
        ref={audioRef}
        src={audioSrc}
        onPlay={() => setSpeaking(true)}
        onEnded={() => setSpeaking(false)}
        onCanPlay={handleCanPlay} // Use this event to trigger play
        controls={false} // Keep controls hidden
      />
    </div>
  );
};

export default Interviewer;