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
      let w = video.videoWidth || 640;
      let h = video.videoHeight || 480;
      // Downscale to speed up upload and server processing (max width 640)
      const maxW = 640;
      if (w > maxW) {
        const scale = maxW / w;
        w = Math.round(w * scale);
        h = Math.round(h * scale);
      }
      const canvas = document.createElement("canvas");
      canvas.width = w; canvas.height = h;
      const ctx = canvas.getContext("2d");
      ctx.drawImage(video, 0, 0, w, h);
      const blob = await new Promise((resolve) => canvas.toBlob(resolve, "image/jpeg", 0.8));
      const dataUrl = canvas.toDataURL("image/jpeg", 0.8);
      onCapture && onCapture(blob, dataUrl);
    } catch (e) {
      setError("Capture failed. Try again or use sample image.");
    }
  };

  return (
    <div className="camera_box">
      <div className="video_wrap" style={{ position: 'relative', overflow: 'hidden' }}>
        <video ref={videoRef} playsInline muted autoPlay className="video" style={{ width: '100%', height: '100%' }} />
        {!ready && (
          <div style={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'white',
            fontSize: '1.2rem',
            fontWeight: '600'
          }}>
            <div className="text-center">
              <div className="text-4xl mb-2">📸</div>
              <div>Initializing Camera...</div>
            </div>
          </div>
        )}
        {ready && (
          <div style={{
            position: 'absolute',
            top: '12px',
            right: '12px',
            background: 'rgba(0, 0, 0, 0.7)',
            color: 'white',
            padding: '6px 12px',
            borderRadius: '20px',
            fontSize: '12px',
            fontWeight: '500'
          }}>
            🔴 LIVE
          </div>
        )}
      </div>
      <div className="camera_actions">
        <button 
          type="button" 
          className="btn_secondary" 
          onClick={onToggleFacing}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            padding: '10px 16px',
            borderRadius: '12px',
            border: '2px solid #e5e7eb',
            background: 'white',
            transition: 'all 0.2s ease'
          }}
        >
          🔄 Switch to {facingMode === "user" ? "📷 Back" : "🤳 Front"} Camera
        </button>
        <button 
          type="button" 
          className={ready ? "btn_primary" : "btn_secondary"} 
          onClick={doCapture} 
          disabled={!ready}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            padding: '12px 24px',
            borderRadius: '12px',
            fontWeight: '600',
            fontSize: '16px',
            minWidth: '160px',
            justifyContent: 'center',
            opacity: ready ? 1 : 0.6,
            transform: ready ? 'scale(1)' : 'scale(0.95)',
            transition: 'all 0.2s ease'
          }}
        >
          {ready ? captureLabel : "⏳ Preparing..."}
        </button>
      </div>
      {error && (
        <div className="error_text" style={{ 
          marginTop: '12px',
          padding: '12px 16px',
          background: '#fef2f2',
          border: '1px solid #fecaca',
          borderRadius: '12px',
          color: '#dc2626',
          fontSize: '14px',
          fontWeight: '500',
          textAlign: 'center'
        }}>
          ⚠️ {error}
        </div>
      )}
    </div>
  );
}