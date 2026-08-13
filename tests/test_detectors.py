import pytest
from src.detectors import luhn_check, regex_detectors


def test_luhn_valid():
    assert luhn_check('4111111111111111') is True


def test_luhn_invalid():
    assert luhn_check('4111111111111112') is False


def test_email_and_phone_regex():
    text = 'Email: john.doe@example.com Phone: +91 98765 43210'
    dets = regex_detectors(text)
    types = {d["type"] for d in dets}
    assert 'EMAIL' in types
    assert 'PHONE' in types
