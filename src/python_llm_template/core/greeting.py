"""Pure domain logic (the ``core`` layer).

Modules in this layer:

- contain the rules of the domain (validation, calculations, decisions);
- must not import from ``services`` or ``cli`` (enforced by import-linter);
- should avoid I/O entirely, which keeps them trivially testable.
"""

MAX_NAME_LENGTH = 50


def build_greeting(name: str) -> str:
    """Build a greeting for ``name``.

    Args:
        name: The name to greet. Surrounding whitespace is ignored.

    Returns:
        A greeting message such as ``"Hello, Ada!"``.

    Raises:
        ValueError: If ``name`` is blank or longer than ``MAX_NAME_LENGTH``.
    """
    cleaned = name.strip()
    if not cleaned:
        raise ValueError("name must not be blank")
    if len(cleaned) > MAX_NAME_LENGTH:
        raise ValueError(f"name must be at most {MAX_NAME_LENGTH} characters")
    return f"Hello, {cleaned}!"
