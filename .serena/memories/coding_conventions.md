# Coding Conventions

## Style Guidelines
- **Standard**: PEP 8 modified (Line length 88 chars - Black style).
- **Strings**: Double quotes preferred.
- **Type Hints**: Mandatory for all function signatures.
- **Docstrings**: Google style mandatory for all public APIs.

## Code Organization
- **Imports**: Sorted: Standard Lib -> Third Party -> Local.
- **Async**: Heavy use of `async/await` for I/O bound operations.
- **Error Handling**: Use specific exception types, never silent failures.

## Version Control
- **Commits**: Semantic Commit Messages (`feat:`, `fix:`, `docs:`, `test:`).
- **Branches**: `feature/`, `fix/`, `docs/` prefixes.
- **PRs**: Require tests, documentation updates, and clear descriptions.

## Testing
- **Coverage**: Aim for >80%.
- **Location**: `tests/` directory with `test_` prefix.
- **Mode**: `asyncio_mode=auto`.
