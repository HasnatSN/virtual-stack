# Code Quality

This project uses several tools to maintain code quality, enforce standards, and measure test coverage.

## Linting and Formatting (`ruff`)

We use [`ruff`](https://github.com/astral-sh/ruff) for extremely fast Python linting and code formatting. It replaces tools like Flake8, isort, pydocstyle, Black, and others.

**Configuration:**

`ruff` is configured in the `pyproject.toml` file under the `[tool.ruff]` section. Key configurations include:

-   `line-length`
-   `target-version` (Matches the project's Python version)
-   A wide selection of linting rules (`[tool.ruff.lint.select]`) covering style, errors, complexity, security (bandit), imports, docstrings, etc.
-   Specific rules to ignore (`[tool.ruff.lint.ignore]`)
-   Per-file ignores (`[tool.ruff.lint.per-file-ignores]`) to relax rules for specific files like tests (`__init__.py`, `conftest.py`) and generated Alembic migrations.
-   Formatting rules (`[tool.ruff.format]`)
-   Import sorting (isort) configuration (`[tool.ruff.lint.isort]`)
-   Docstring style convention (`[tool.ruff.lint.pydocstyle]`)

**Usage:**

-   **Check for issues:**
    ```bash
    python3 -m ruff check .
    ```
-   **Check and automatically fix fixable issues:**
    ```bash
    python3 -m ruff check . --fix
    ```
-   **Format code:**
    ```bash
    python3 -m ruff format .
    ```

## Type Checking (`mypy`)

We use [`mypy`](http://mypy-lang.org/) for static type checking.

**Configuration:**

`mypy` configuration is typically stored in `pyproject.toml` under `[tool.mypy]` or in a separate `mypy.ini` file. Key settings often include:

- `python_version`
- `ignore_missing_imports`
- `strict` (or specific strictness flags)

**Usage:**

```bash
python3 -m mypy src/
```

## Test Coverage (`pytest-cov`)

We use [`pytest-cov`](https://pytest-cov.readthedocs.io/) to measure the effectiveness of our tests by reporting code coverage.

**Configuration:**

Coverage is configured in `pytest.ini`:

-   `addopts`: Includes `--cov=src` to target the `src` directory and `--cov-report=term-missing` to show missing lines in the terminal report.
-   `[coverage:run]`: Specifies `source = src` and omits test files, Alembic migrations, and base database files (`omit = tests/*, alembic/*, src/virtualstack/db/base*.py`).
-   `[coverage:report]`: Sets `fail_under = 80` to enforce a minimum 80% coverage and `show_missing = True`.

**Usage:**

Coverage is automatically run and reported when running tests:

```bash
python3 -m pytest
```

The report will be displayed in the terminal, and the run will fail if coverage drops below 80%. 