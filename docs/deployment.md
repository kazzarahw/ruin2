# Deployment

## Prime Agent skill

1. Copy the repository into `.prime/agent/skills/ruin/`.
2. Start Prime Agent in that project directory.
3. Verify with `import ruin; help(ruin.run)`.
4. Run `await ruin.run("research", mechanism="m", summary="s")`.

## Requirements

- Python 3.11+
- Foundry and Slither for execution-heavy operations