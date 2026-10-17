"""Tests for ``python_llm_template.services.greeting``."""

import pytest

from python_llm_template.services.greeting import GreetingService


def test_greet_title_cases_the_name() -> None:
    assert GreetingService().greet("ada lovelace") == "Hello, Ada Lovelace!"


def test_greet_ignores_surrounding_whitespace() -> None:
    assert GreetingService().greet("  ada  ") == "Hello, Ada!"


def test_greet_rejects_blank_names() -> None:
    with pytest.raises(ValueError, match=r"^name must not be blank$"):
        GreetingService().greet("   ")
