import { useCallback, useEffect, useRef, useState } from "react";
import {
  listElderly,
  listObservations,
  predictExpression,
  saveObservation,
  startSession,
  stopSession,
  getApiError,
} from "../services/api";
import { attentionBadgeClass, formatAttention } from "../utils/labels";

export default function LiveMonitoringPage() {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const streamRef = useRef(null);
  const timerRef = useRef(null);
  const sessionIdRef = useRef("");
  const webcamOnRef = useRef(false);
  const predictingRef = useRef(false);
  const captureGenerationRef = useRef(0);

  const [profiles, setProfiles] = useState([]);
  const [elderlyId, setElderlyId] = useState("");
  const [sessionId, setSessionId] = useState("");
  const [webcamOn, setWebcamOn] = useState(false);
  const [predicting, setPredicting] = useState(false);
  const [prediction, setPrediction] = useState(null);
  const [recent, setRecent] = useState([]);
  const [message, setMessage] = useState("Select a profile, start a session, then start the webcam.");
  const [error, setError] = useState("");
  const [profilesLoading, setProfilesLoading] = useState(true);
  const [consentGiven, setConsentGiven] = useState(() => localStorage.getItem("ewm_monitoring_consent") === "true");

  const refreshRecent = useCallback(async () => {
    const rows = await listObservations({ limit: 10 });
    setRecent(rows);
  }, []);

  useEffect(() => {
    listElderly()
      .then((rows) => {
        setProfiles(rows);
        if (rows[0]) setElderlyId(String(rows[0].id));
      })
      .catch((requestError) => setError(`Could not load profiles: ${getApiError(requestError)}`))
      .finally(() => setProfilesLoading(false));
    refreshRecent().catch(() => {});
    return () => {
      captureGenerationRef.current += 1;
      webcamOnRef.current = false;
      predictingRef.current = false;
      stopWebcamTracks();
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [refreshRecent]);

  function stopWebcamTracks() {
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    if (videoRef.current) videoRef.current.srcObject = null;
  }

  async function onStartSession() {
    setError("");
    if (!consentGiven) {
      setError("Please acknowledge the privacy and consent notice before starting monitoring.");
      return;
    }
    try {
      const sess = await startSession(Number(elderlyId));
      sessionIdRef.current = sess.session_id;
      setSessionId(sess.session_id);
      setMessage(`Session started: ${sess.session_id}`);
    } catch (requestError) {
      setError(`Failed to start session: ${getApiError(requestError)}`);
    }
  }

  async function onStopSession() {
    const activeSessionId = sessionIdRef.current;
    if (!activeSessionId) return;
    try {
      await stopSession(activeSessionId);
      await onStopWebcam();
      sessionIdRef.current = "";
      setSessionId("");
      setMessage(`Session ended: ${activeSessionId}`);
    } catch (requestError) {
      setError(`Failed to stop session: ${getApiError(requestError)}`);
    }
  }

  async function onStartWebcam() {
    setError("");
    if (!sessionIdRef.current) {
      setError("Start a monitoring session first.");
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "user", width: { ideal: 640 }, height: { ideal: 480 } },
        audio: false,
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }
      captureGenerationRef.current += 1;
      webcamOnRef.current = true;
      setWebcamOn(true);
      setMessage("Webcam active. Capturing frames for face detection and expression prediction.");
      if (timerRef.current) clearInterval(timerRef.current);
      timerRef.current = setInterval(() => {
        void captureAndPredict();
      }, 2500);
    } catch (requestError) {
      const name = requestError?.name;
      const webcamMessage = name === "NotAllowedError"
        ? "Webcam permission was denied. Allow camera access in the browser and try again."
        : name === "NotFoundError"
        ? "No webcam was found on this device."
        : "Webcam permission denied or unavailable.";
      setError(webcamMessage);
    }
  }

  async function onStopWebcam() {
    captureGenerationRef.current += 1;
    webcamOnRef.current = false;
    predictingRef.current = false;
    if (timerRef.current) clearInterval(timerRef.current);
    timerRef.current = null;
    stopWebcamTracks();
    setWebcamOn(false);
    setPredicting(false);
    setMessage("Webcam stopped. Frames are not stored continuously.");
  }

  function grabFrameBase64() {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas || video.readyState < 2) return null;
    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 480;
    const ctx = canvas.getContext("2d");
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    return canvas.toDataURL("image/jpeg", 0.8);
  }

  async function captureAndPredict() {
    const activeSessionId = sessionIdRef.current;
    if (!activeSessionId || !webcamOnRef.current || predictingRef.current) return;
    const image = grabFrameBase64();
    if (!image) return;
    const captureGeneration = captureGenerationRef.current;
    predictingRef.current = true;
    setPredicting(true);
    try {
      const result = await predictExpression(image, activeSessionId);
      if (
        webcamOnRef.current &&
        captureGeneration === captureGenerationRef.current &&
        sessionIdRef.current === activeSessionId
      ) {
        setPrediction(result);
        setMessage(result.message);
      }
    } catch (requestError) {
      if (webcamOnRef.current && captureGeneration === captureGenerationRef.current) {
        setError(`Prediction request failed: ${getApiError(requestError, "AI prediction unavailable")}`);
      }
    } finally {
      if (captureGeneration === captureGenerationRef.current) {
        predictingRef.current = false;
        if (webcamOnRef.current && sessionIdRef.current === activeSessionId) {
          setPredicting(false);
        }
      }
    }
  }

  async function onSaveObservation() {
    if (!prediction || !prediction.face_detected || !sessionId) {
      setError("Save requires a face-detected observation and active session.");
      return;
    }
    if (prediction.expression === "unknown" || prediction.confidence < 0.5 || prediction.smoothing_window < 2) {
      setError("Only stabilized, meaningful predictions can be saved.");
      return;
    }
    try {
      await saveObservation({
        session_id: sessionId,
        elderly_id: Number(elderlyId),
        expression: prediction.expression,
        confidence: prediction.confidence,
        observed_at: prediction.timestamp,
        notes: "Saved from live monitoring session",
      });
      setMessage("Observation saved (stabilized result only — no video stored).");
      await refreshRecent();
    } catch (requestError) {
      setError(`Could not save observation: ${getApiError(requestError)}`);
    }
  }

  return (
    <div>
      <h1 className="page-title">Live monitoring</h1>
      <p className="page-sub">
        Real-time webcam stream and facial expression analysis. High privacy standards: continuous video frames are not saved.
      </p>

      <div className="panel card">
        <label className="disclaimer" style={{ display: "flex", gap: "0.6rem", alignItems: "flex-start", marginBottom: "1rem" }}>
          <input
            type="checkbox"
            checked={consentGiven}
            onChange={(event) => {
              const checked = event.target.checked;
              setConsentGiven(checked);
              if (checked) localStorage.setItem("ewm_monitoring_consent", "true");
              else localStorage.removeItem("ewm_monitoring_consent");
            }}
          />
          <span>I acknowledge that monitoring requires informed consent. The system records derived observable facial-expression results only, does not store continuous webcam video, and is not a medical diagnostic tool.</span>
        </label>
        <div className="actions" style={{ marginBottom: "0.85rem" }}>
          <div className="form-row" style={{ minWidth: 220, marginBottom: 0 }}>
            <label>Elderly profile</label>
            <select value={elderlyId} onChange={(e) => setElderlyId(e.target.value)} disabled={profilesLoading || !!sessionId}>
              {profilesLoading && <option value="">Loading profiles...</option>}
              {profiles.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.elderly_code} — {p.full_name}
                </option>
              ))}
            </select>
          </div>
          {!sessionId ? (
            <button className="btn btn-primary" type="button" onClick={onStartSession} disabled={!elderlyId || !consentGiven}>
              Start session
            </button>
          ) : (
            <button className="btn btn-danger" type="button" onClick={onStopSession}>
              Stop session
            </button>
          )}
          {!webcamOn ? (
            <button className="btn btn-secondary" type="button" onClick={onStartWebcam}>
              Start webcam
            </button>
          ) : (
            <button className="btn btn-secondary" type="button" onClick={onStopWebcam}>
              Stop webcam
            </button>
          )}
          <button className="btn btn-secondary" type="button" onClick={captureAndPredict} disabled={!webcamOn || predicting}>
            Capture prediction
          </button>
          <button
            className="btn btn-primary"
            type="button"
            onClick={onSaveObservation}
            disabled={!prediction?.face_detected || !sessionId}
          >
            Save observation
          </button>
        </div>

        {message && <p className="muted" style={{ marginBottom: "0.85rem" }}>{message}</p>}
        {!profilesLoading && !profiles.length && !error && (
          <p className="muted" style={{ marginBottom: "0.85rem" }}>Create an elderly profile before starting a monitoring session.</p>
        )}
        {error && <p style={{ color: "var(--danger)", marginBottom: "0.85rem", fontWeight: 600 }}>{error}</p>}

        <div className="monitor-grid">
          <div className="video-wrap">
            <video
              ref={videoRef}
              autoPlay
              playsInline
              muted
              style={{ width: "100%", height: "100%", objectFit: "cover" }}
            />
            <canvas ref={canvasRef} style={{ display: "none" }} />
            {!webcamOn && (
              <div
                style={{
                  position: "absolute",
                  inset: 0,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  color: "rgba(255,255,255,0.7)",
                  fontSize: "0.95rem",
                  flexDirection: "column",
                  gap: "0.5rem"
                }}
              >
                <span>📷 Webcam is off</span>
                <span style={{ fontSize: "0.8rem", opacity: 0.8 }}>Start a session and click "Start webcam"</span>
              </div>
            )}
          </div>

          <div className="pred-list">
            {prediction ? (
              <div className="prediction-summary">
                <div className="pred-item">
                  <strong>STABLE EXPRESSION</strong>
                  <div className="pred-item-value">{prediction.expression || "unknown"}</div>
                </div>
                <div className="pred-item">
                  <strong>CONFIDENCE</strong>
                  <div className="pred-item-value">{((prediction.confidence || 0) * 100).toFixed(1)}%</div>
                  <div className="confidence-bar">
                    <div
                      className={`confidence-bar-fill ${
                        prediction.confidence < 0.6
                          ? "confidence-low"
                          : prediction.confidence < 0.85
                          ? "confidence-medium"
                          : "confidence-high"
                      }`}
                      style={{ width: `${(prediction.confidence || 0) * 100}%` }}
                    >
                      {prediction.confidence > 0.3 && (
                        <span className="confidence-text">{((prediction.confidence || 0) * 100).toFixed(0)}%</span>
                      )}
                    </div>
                  </div>
                </div>
                <div className="pred-item">
                  <strong>RAW AI PREDICTION</strong>
                  <div className="pred-item-value">
                    {(prediction.raw_expression || prediction.expression || "unknown")} ({((prediction.raw_confidence ?? prediction.confidence ?? 0) * 100).toFixed(1)}%)
                  </div>
                </div>
                <div className="pred-item">
                  <strong>FACE</strong>
                  <div className="pred-item-value">{prediction.face_detected ? "Detected" : "Not detected"}</div>
                </div>
                <div className="pred-item">
                  <strong>AI STATUS</strong>
                  <div className="pred-item-value">
                    {prediction.demo_mode
                      ? "Demo mode disabled for production"
                      : !prediction.face_detected
                      ? "No face detected"
                      : prediction.expression === "unknown"
                      ? "AI prediction unavailable"
                      : "Real model"}
                  </div>
                </div>
                <div className="pred-item">
                  <strong>SMOOTHING</strong>
                  <div className="pred-item-value">{prediction.smoothing_window ?? 0} frames</div>
                </div>
                <div className="pred-item">
                  <strong>Capture Time</strong>
                  <div className="pred-item-value">{new Date(prediction.timestamp).toLocaleString()}</div>
                </div>
                <div className="pred-item">
                  <strong>Attention Status</strong>
                  <div className="pred-item-value">
                    <span className={attentionBadgeClass(prediction.attention_indicator)}>
                      {formatAttention(prediction.attention_indicator)}
                    </span>
                  </div>
                </div>
                <div className="pred-item">
                  <strong>Session ID</strong>
                  <div className="pred-item-value" style={{ fontSize: "0.9rem", fontFamily: "monospace" }}>
                    {prediction.session_id.substring(0, 12)}...
                  </div>
                </div>
              </div>
            ) : (
              <div className="prediction-summary">
                <div className="pred-item">
                  <strong>Status</strong>
                  <div className="pred-item-value" style={{ color: "var(--muted)" }}>
                    🎥 No prediction yet.
                  </div>
                  <div style={{ fontSize: "0.85rem", color: "var(--muted)", marginTop: "0.5rem" }}>
                    Start webcam to begin capturing face expressions.
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="panel card">
        <h2>Recent observations</h2>
        <table className="table">
          <thead>
            <tr>
              <th>Date/Time</th>
              <th>Expression</th>
              <th>Confidence</th>
              <th>Attention</th>
              <th>Session</th>
            </tr>
          </thead>
          <tbody>
            {recent.map((o) => {
              const confPercent = o.confidence * 100;
              const confClass =
                o.confidence < 0.6
                  ? "confidence-low"
                  : o.confidence < 0.85
                  ? "confidence-medium"
                  : "confidence-high";
              return (
                <tr key={o.id}>
                  <td>{new Date(o.observed_at).toLocaleString()}</td>
                  <td>
                    <strong>{o.expression}</strong>
                  </td>
                  <td>
                    <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                      <div style={{ width: "60px", height: "18px" }}>
                        <div className="confidence-bar" style={{ height: "100%" }}>
                          <div
                            className={`confidence-bar-fill ${confClass}`}
                            style={{ width: `${confPercent}%` }}
                          />
                        </div>
                      </div>
                      <span style={{ minWidth: "45px", fontWeight: "600" }}>
                        {confPercent.toFixed(1)}%
                      </span>
                    </div>
                  </td>
                  <td>
                    <span className={attentionBadgeClass(o.attention_indicator)}>
                      {formatAttention(o.attention_indicator)}
                    </span>
                  </td>
                  <td style={{ fontSize: "0.85rem", fontFamily: "monospace" }}>
                    {o.session_id.substring(0, 12)}...
                  </td>
                </tr>
              );
            })}
            {!recent.length && (
              <tr>
                <td colSpan={5}>No saved observations yet.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
