"""Acceptance tests. The task brief deliberately omits the 50-character rule to exercise correction."""
import pytest

from slugify import slugify


@pytest.mark.parametrize("text, expected", [
    ("Hello World", "hello-world"),
    ("  Crème Brûlée!  ", "creme-brulee"),
    ("a -- b__c", "a-b-c"),
    ("Ünïcödé 123", "unicode-123"),
    ("", ""),
])
def test_basic(text, expected):
    assert slugify(text) == expected


def test_max_50_chars_cut_at_word_boundary():
    assert slugify("word " * 30) == "-".join(["word"] * 10)  # 49 chars, never a trailing hyphen or half word
