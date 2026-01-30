---
type: "always_apply"
---

# Development Tools

## Python

- For both environment and project management, use `uv`. Never refer to any other tooling and never use any commands that start with `uv pip`.
  - Do: use `uv add` to add a new dependency.
  - Do not: use `uv pip install` or `pip install`.
- Only use `uvx ruff` for linting and formatting. The configuration is in `ruff.toml`.
- DO NOT edit any `.toml` files directly unless explicitly instructed to do so.



## Typing and Linting

- Follow all rules that are in `ruff.toml`.
- DO NOT use `typing.Any` on its own.
- If you do use `typing.Any` you MUST explain why by using a comment with `FIXME`.
- DO NOT fix errors associated with `FIXME` comments.


## Testing Framework

- Only use `pytest` for all tests.
- DO NOT use any mocking techniques unless explicitly directed to do so.
- Use fixtures in `conftest.py` to set up the test environment.
- **ALWAYS check for existing fixtures before creating new ones**:

  - First check the current test file's directory for `conftest.py`
  - Then check parent directories for `conftest.py` files
  - Only create new fixtures if the required functionality doesn't already exist
  - Reuse existing fixtures whenever possible to maintain consistency

- Use mimesis for fake data generation

### Unit Tests vs Integration Tests

Unit tests check each function in isolation.

- They do not have access to a seeded database or any external dependencies or services.
