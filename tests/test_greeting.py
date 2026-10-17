"""Tests for ``python_llm_template.core.greeting``."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from python_llm_template.core.greeting import MAX_NAME_LENGTH, build_greeting


def test_build_greeting_formats_name() -> None:
    assert build_greeting("Ada") == "Hello, Ada!"


def test_build_greeting_ignores_surrounding_whitespace() -> None:
    assert build_greeting("  Ada  ") == "Hello, Ada!"


@pytest.mark.parametrize("blank", ["", "   ", "\t\n"])
def test_build_greeting_rejects_blank_names(blank: str) -> None:
    with pytest.raises(ValueError, match=r"^name must not be blank$"):
        build_greeting(blank)


def test_build_greeting_rejects_overlong_names() -> None:
    with pytest.raises(ValueError, match=r"^name must be at most 50 characters$"):
        build_greeting("a" * (MAX_NAME_LENGTH + 1))


def test_build_greeting_accepts_a_name_of_exactly_the_max_length() -> None:
    longest = "a" * MAX_NAME_LENGTH

    assert build_greeting(longest) == f"Hello, {longest}!"


@given(st.text(min_size=1, max_size=MAX_NAME_LENGTH).filter(lambda text: text.strip()))
def test_build_greeting_property_echoes_the_cleaned_name(name: str) -> None:
    assert build_greeting(name) == f"Hello, {name.strip()}!"
