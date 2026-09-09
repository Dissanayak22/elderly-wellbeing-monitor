"""Attention indicator rules — caregiver support only, not medical diagnosis."""

EXPRESSIONS = ("happy", "sad", "neutral", "angry", "fear", "surprise", "disgust")

ATTENTION_NORMAL = "normal_observation"
ATTENTION_RECOMMENDED = "attention_recommended"
ATTENTION_CHECK = "caregiver_check_recommended"


def compute_attention_indicator(expression: str, confidence: float) -> str:
    """Map observable expression + confidence to a non-clinical attention label."""
    expression = expression.lower().strip()
    if expression in ("sad", "fear", "angry", "disgust") and confidence >= 0.75:
        return ATTENTION_CHECK
    if expression in ("sad", "fear", "angry", "disgust") and confidence >= 0.55:
        return ATTENTION_RECOMMENDED
    if expression == "surprise" and confidence >= 0.8:
        return ATTENTION_RECOMMENDED
    return ATTENTION_NORMAL
