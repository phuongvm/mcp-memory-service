# Task Completion Guide

Before marking a task as complete, ensure:

1.  **Tests Pass**: Run `pytest tests/` to verify no regressions.
2.  **Lint/Format**: Ensure code follows PEP 8 (Black style) and has type hints.
3.  **Documentation**: Update README or Wiki if new features were added.
4.  **Verification**:
    - If modifying server code, verify `uv run memory server` starts without errors.
    - If adding CLI commands, verify they work as expected.
5.  **Clean Up**: Remove any temporary files or debug prints.

**Checklist:**
- [ ] Tests passed (`pytest`)
- [ ] Code formatted & Typed
- [ ] Docstrings added/updated
- [ ] Manual verification (Server start / CLI run)
