"""
Facial expression recognition service.

Pipeline:
1. OpenCV detects the largest face.
2. The face is cropped.
3. A pretrained Hugging Face Vision Transformer classifies
   the observable facial expression.
4. A short history of predictions is averaged to reduce
   frame-to-frame prediction noise.

The system recognizes observable facial expressions only.
It does not diagnose mental or medical conditions.
"""

from __future__ import annotations

import base64
import os
from collections import defaultdict, deque
from datetime import datetime, timezone
from typing import Any

import numpy as np

EXPRESSIONS = [
    "angry",
    "disgust",
    "fear",
    "happy",
    "sad",
    "surprise",
    "neutral",
]

MODEL_NAME = "dima806/facial_emotions_image_detection"
MODEL_REVISION = "747cf16692eea925b54b7b543cf436848128b68d"


def _env_demo_mode() -> bool:
    return os.getenv("AI_DEMO_MODE", "false").lower() in (
        "1",
        "true",
        "yes",
    )


class ExpressionRecognizer:
    def __init__(self, demo_mode: bool | None = None) -> None:
        self.demo_mode = (
            _env_demo_mode()
            if demo_mode is None
            else demo_mode
        )

        self._cv2 = None
        self._face_cascade = None
        self._pipeline = None

        # Store the last 5 probability predictions per session.
        self._prediction_history = defaultdict(
            lambda: deque(maxlen=5)
        )

        self._init_opencv()

        if not self.demo_mode:
            self._try_load_model()

    # ---------------------------------------------------------
    # OpenCV
    # ---------------------------------------------------------

    def _init_opencv(self) -> None:
        try:
            import cv2

            self._cv2 = cv2

            cascade_path = (
                cv2.data.haarcascades
                + "haarcascade_frontalface_default.xml"
            )

            self._face_cascade = cv2.CascadeClassifier(
                cascade_path
            )

            if self._face_cascade.empty():
                raise RuntimeError(
                    "Could not load Haar face cascade."
                )

            print("[AI] OpenCV initialized successfully.")

        except Exception as exc:
            print(
                f"[AI] OpenCV initialization failed: {exc}"
            )

            self._cv2 = None
            self._face_cascade = None

    # ---------------------------------------------------------
    # AI model
    # ---------------------------------------------------------

    def _try_load_model(self) -> None:
        try:
            from transformers import pipeline

            print(
                f"[AI] Loading facial-expression model: "
                f"{MODEL_NAME}"
            )

            self._pipeline = pipeline(
                "image-classification",
                model=MODEL_NAME,
                revision=MODEL_REVISION,
                device=-1,  # CPU
            )

            print(
                "[AI] Real facial-expression model "
                "loaded successfully."
            )

        except Exception as exc:
            print(
                f"[AI] Could not load AI model: {exc}"
            )

            self._pipeline = None

    # ---------------------------------------------------------
    # Image decoding
    # ---------------------------------------------------------

    def decode_image(
        self,
        image_base64: str,
    ) -> np.ndarray | None:

        raw = image_base64

        if "," in raw:
            raw = raw.split(",", 1)[1]

        try:
            data = base64.b64decode(raw)
        except Exception:
            return None

        if self._cv2 is None:
            return None

        arr = np.frombuffer(
            data,
            dtype=np.uint8,
        )

        image = self._cv2.imdecode(
            arr,
            self._cv2.IMREAD_COLOR,
        )

        return image

    # ---------------------------------------------------------
    # Face detection
    # ---------------------------------------------------------

    def detect_faces(
        self,
        image_bgr: np.ndarray,
    ) -> list[tuple[int, int, int, int]]:

        if (
            self._cv2 is None
            or self._face_cascade is None
        ):
            return []

        gray = self._cv2.cvtColor(
            image_bgr,
            self._cv2.COLOR_BGR2GRAY,
        )

        faces = self._face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(60, 60),
        )

        return [
            (
                int(x),
                int(y),
                int(w),
                int(h),
            )
            for (x, y, w, h) in faces
        ]

    # ---------------------------------------------------------
    # Real AI prediction
    # ---------------------------------------------------------

    def _predict_real(
        self,
        face_roi: np.ndarray,
    ) -> tuple[str, float, dict[str, float]]:

        if self._pipeline is None:
            raise RuntimeError(
                "AI model is not loaded."
            )

        from PIL import Image

        # OpenCV = BGR
        # PIL     = RGB
        face_rgb = self._cv2.cvtColor(
            face_roi,
            self._cv2.COLOR_BGR2RGB,
        )

        image = Image.fromarray(face_rgb)

        # Get all seven emotion probabilities.
        results = self._pipeline(
            image,
            top_k=7,
        )

        if not results:
            raise RuntimeError(
                "AI model returned no predictions."
            )

        probabilities = {
            str(item["label"]).lower():
            float(item["score"])
            for item in results
        }

        expression = max(
            probabilities,
            key=probabilities.get,
        )

        confidence = probabilities[
            expression
        ]

        return (
            expression,
            confidence,
            probabilities,
        )

    # ---------------------------------------------------------
    # Temporal smoothing
    # ---------------------------------------------------------

    def _smooth_prediction(
        self,
        session_id: str,
        probabilities: dict[str, float],
    ) -> tuple[str, float]:

        history = self._prediction_history[
            session_id
        ]

        history.append(probabilities)

        averaged: dict[str, float] = {}

        for expression in EXPRESSIONS:
            values = [
                frame.get(expression, 0.0)
                for frame in history
            ]

            averaged[expression] = (
                sum(values) / len(values)
            )

        stable_expression = max(
            averaged,
            key=averaged.get,
        )

        stable_confidence = averaged[
            stable_expression
        ]

        return (
            stable_expression,
            stable_confidence,
        )

    def clear_session(self, session_id: str) -> None:
        """Release temporal state once a monitoring session has ended."""
        self._prediction_history.pop(session_id, None)

    # ---------------------------------------------------------
    # Main prediction function
    # ---------------------------------------------------------

    def predict(
        self,
        image_base64: str,
        session_id: str,
    ) -> dict[str, Any]:

        timestamp = (
            datetime.now(timezone.utc)
            .isoformat()
        )

        image = self.decode_image(
            image_base64
        )

        if image is None:
            return {
                "expression": "unknown",
                "confidence": 0.0,
                "timestamp": timestamp,
                "session_id": session_id,
                "face_detected": False,
                "demo_mode": self.demo_mode,
                "message": (
                    "Could not decode image frame."
                ),
            }

        faces = self.detect_faces(image)

        if not faces:
            return {
                "expression": "unknown",
                "confidence": 0.0,
                "timestamp": timestamp,
                "session_id": session_id,
                "face_detected": False,
                "demo_mode": self.demo_mode,
                "message": (
                    "No face detected. Position "
                    "your face clearly in front "
                    "of the webcam."
                ),
            }

        # Select the largest detected face.
        x, y, w, h = max(
            faces,
            key=lambda face:
            face[2] * face[3],
        )

        face_roi = image[
            y:y + h,
            x:x + w,
        ]

        # -----------------------------------------------------
        # REAL AI
        # -----------------------------------------------------

        if not self.demo_mode:
            if self._pipeline is None:
                return {
                    "expression": "unknown",
                    "confidence": 0.0,
                    "raw_expression": "unknown",
                    "raw_confidence": 0.0,
                    "smoothing_window": 0,
                    "timestamp": timestamp,
                    "session_id": session_id,
                    "face_detected": True,
                    "demo_mode": False,
                    "message": "AI model unavailable",
                }

            try:
                (
                    raw_expression,
                    raw_confidence,
                    probabilities,
                ) = self._predict_real(
                    face_roi
                )

                (
                    stable_expression,
                    stable_confidence,
                ) = self._smooth_prediction(
                    session_id,
                    probabilities,
                )

                history_size = len(
                    self._prediction_history[
                        session_id
                    ]
                )

                return {
                    # Stable result shown to the user
                    "expression": stable_expression,
                    "confidence": round(
                        stable_confidence,
                        3,
                    ),

                    # Raw AI result for research/debugging
                    "raw_expression": (
                        raw_expression
                    ),
                    "raw_confidence": round(
                        raw_confidence,
                        3,
                    ),

                    "timestamp": timestamp,
                    "session_id": session_id,
                    "face_detected": True,
                    "demo_mode": False,
                    "smoothing_window": (
                        history_size
                    ),
                    "message": (
                        "Observable facial expression "
                        "analyzed in real time "
                        "with temporal smoothing."
                    ),
                }

            except Exception as exc:
                print(
                    f"[AI] Prediction failed: {exc}"
                )

                return {
                    "expression": "unknown",
                    "confidence": 0.0,
                    "raw_expression": "unknown",
                    "raw_confidence": 0.0,
                    "smoothing_window": 0,
                    "timestamp": timestamp,
                    "session_id": session_id,
                    "face_detected": True,
                    "demo_mode": False,
                    "message": "AI prediction failed",
                }

        # -----------------------------------------------------
        # DEMO MODE FALLBACK
        # -----------------------------------------------------

        probabilities = {
            expression: 0.40 / (len(EXPRESSIONS) - 1)
            for expression in EXPRESSIONS
        }
        probabilities["neutral"] = 0.60
        stable_expression, stable_confidence = self._smooth_prediction(
            session_id,
            probabilities,
        )

        return {
            "expression": stable_expression,
            "confidence": round(stable_confidence, 3),
            "raw_expression": "neutral",
            "raw_confidence": 0.60,
            "smoothing_window": len(
                self._prediction_history[session_id]
            ),
            "timestamp": timestamp,
            "session_id": session_id,
            "face_detected": True,
            "demo_mode": True,
            "message": (
                "Live face detection active. Observing "
                "facial features in real time."
            ),
        }


# -------------------------------------------------------------
# Singleton
# -------------------------------------------------------------

_recognizer: ExpressionRecognizer | None = None
_configured_demo_mode: bool | None = None


def get_recognizer(
    demo_mode: bool | None = None,
) -> ExpressionRecognizer:

    global _recognizer
    global _configured_demo_mode

    if (
        _recognizer is None
        or (
            demo_mode is not None
            and demo_mode
            != _configured_demo_mode
        )
    ):
        _recognizer = ExpressionRecognizer(
            demo_mode=demo_mode
        )

        _configured_demo_mode = demo_mode

    return _recognizer


def clear_session_history(session_id: str) -> None:
    """Clear smoothing state without initializing the recognizer."""
    if _recognizer is not None:
        _recognizer.clear_session(session_id)


def get_recognizer_status(configured_demo_mode: bool) -> dict[str, Any]:
    """Report current AI state without triggering a model download or load."""
    configured_mode = "demo" if configured_demo_mode else "real"
    if _recognizer is None:
        return {
            "configured_mode": configured_mode,
            "state": "not_initialized",
            "ready": False,
            "face_detection_ready": False,
            "model_loaded": False,
            "model_name": MODEL_NAME,
            "model_revision": MODEL_REVISION,
        }

    face_detection_ready = (
        _recognizer._cv2 is not None
        and _recognizer._face_cascade is not None
    )
    if _recognizer.demo_mode:
        state = "demo_ready" if face_detection_ready else "unavailable"
        return {
            "configured_mode": configured_mode,
            "state": state,
            "ready": face_detection_ready,
            "face_detection_ready": face_detection_ready,
            "model_loaded": False,
            "model_name": MODEL_NAME,
            "model_revision": MODEL_REVISION,
        }

    model_loaded = _recognizer._pipeline is not None
    ready = face_detection_ready and model_loaded
    return {
        "configured_mode": configured_mode,
        "state": "ready" if ready else "unavailable",
        "ready": ready,
        "face_detection_ready": face_detection_ready,
        "model_loaded": model_loaded,
        "model_name": MODEL_NAME,
        "model_revision": MODEL_REVISION,
    }
