"""Unit tests for attention indicator rules."""

from backend.app.services.attention import (
    ATTENTION_CHECK,
    ATTENTION_NORMAL,
    ATTENTION_RECOMMENDED,
    compute_attention_indicator,
)


def test_normal_happy():
    assert compute_attention_indicator("happy", 0.9) == ATTENTION_NORMAL


def test_attention_recommended_sad():
    assert compute_attention_indicator("sad", 0.6) == ATTENTION_RECOMMENDED


def test_caregiver_check_fear_high_conf():
    assert compute_attention_indicator("fear", 0.8) == ATTENTION_CHECK
