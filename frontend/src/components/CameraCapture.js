import React, { useEffect, useRef, useState } from "react";

/**
 * Reusable camera capture component with front/back toggle.
 * - facingMode: "user" | "environment"
 * - onToggleFacing: () => void
 * - onCapture: (blob: Blob, dataUrl: string) => void
 * - captureLabel: string
 */
export default function CameraCapture({ facingMode = "user", onToggleFacing, onCapture, captureLabel = "Capture" }) {
  const videoRef = useRef(null);
  const [stream, setStream] = useState(null);
  const [error, setError] = useState("");
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let currentStream = null;
    async function start() {
      setError("");
      try {
        const constraints = { video: { facingMode }, audio: false };
        const s = await navigator.mediaDevices.getUserMedia(constraints);
        currentStream = s;
        setStream(s);
        if (videoRef.current) {
          videoRef.current.srcObject = s;
          await videoRef.current.play();
        }
        setReady(true);
      } catch (e) {
        setError("Camera access failed. Please allow camera permissions or use sample image.");
        setReady(false);
      }
    }
    start();
    return () => {
      if (currentStream) {
        currentStream.getTracks().forEach((t) => t.stop());
      }
    };
  }, [facingMode]);

  const doCapture = async () => {
    try {
      const video = videoRef.current;
      if (!video) return;
      const w = video.videoWidth || 640;
      const h = video.videoHeight || 480;
      const canvas = document.createElement("canvas");
      canvas.width = w; canvas.height = h;
      const ctx = canvas.getContext("2d");
      ctx.drawImage(video, 0, 0, w, h);
      const blob = await new Promise((resolve) => canvas.toBlob(resolve, "image/jpeg", 0.9));
      const dataUrl = canvas.toDataURL("image/jpeg", 0.9);
      onCapture && onCapture(blob, dataUrl);
    } catch (e) {
      setError("Capture failed. Try again or use sample image.");
    }
  };

  return (
    <div className="camera_box">
      <div className="video_wrap">
        <video ref={videoRef} playsInline muted autoPlay className="video" />
      </div>
      <div className="camera_actions">
        <button type="button" className="btn_secondary" onClick={onToggleFacing}>Switch to {facingMode === "user" ? "Back" : "Front"} Camera</button>
        <button type="button" className="btn_primary" onClick={doCapture} disabled={!ready}>{captureLabel}</button>
      </div>
      {error && <div className="error_text" style={{ marginTop: 8 }}>{error}</div>}
    </div>
  );
}