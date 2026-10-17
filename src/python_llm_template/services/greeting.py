"""Application services (the ``services`` layer).

Services orchestrate policy: they may import ``core``, but never ``cli``.
Anything that coordinates multiple steps, applies user-facing policy, or
talks to the outside world belongs here.
"""

from python_llm_template.core.greeting import build_greeting


class GreetingService:
    """Turns raw user input into a greeting message."""

    def greet(self, name: str) -> str:
        """Greet ``name``, normalizing its capitalization.

        Args:
            name: The raw, user-provided name.

        Returns:
            The greeting message.

        Raises:
            ValueError: If ``name`` is blank or too long (see ``build_greeting``).
        """
        return build_greeting(name.strip().title())
