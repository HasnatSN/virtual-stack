# Backend Testing Guide

This guide provides instructions on how to set up the environment and run the backend tests for the VirtualStack project.

## Testing Stack

Our backend testing relies on the following tools:

*   **[pytest](https://docs.pytest.org/):** The core testing framework used for writing and running tests.
*   **[pytest-asyncio](https://pytest-asyncio.readthedocs.io/):** A pytest plugin to handle testing `asyncio` code used throughout the FastAPI application.
*   **[httpx](https://www.python-httpx.org/):** Used within tests to make HTTP requests to the FastAPI application, simulating real client interactions. Fixtures in `conftest.py` provide pre-configured authenticated and unauthenticated clients.
*   **[Coverage.py](https://coverage.readthedocs.io/):** Used via the `pytest-cov` plugin to measure code coverage during test runs.
*   **[Poetry](https://python-poetry.org/):** While not a direct testing tool, Poetry manages project dependencies and the virtual environment necessary to run the tests consistently.
*   **[Pydantic](https://docs.pydantic.dev/):** Used extensively within the FastAPI application for data validation and serialization. While not a testing tool itself, tests implicitly verify Pydantic model behavior during API interactions.
*   **[Docker & Docker Compose](https://www.docker.com/):** Used to manage external dependencies like the PostgreSQL databases required for testing.

## Environment Setup

Before running tests, ensure your environment is set up correctly:

1.  **Install Dependencies:** Make sure you have Poetry installed. Then, navigate to the project root directory (`virtualstack/backend`) and run:
    ```bash
    poetry install
    ```
    This installs all project dependencies, including those required for testing, into a virtual environment managed by Poetry.

2.  **Start External Services:** The tests require external services, primarily a dedicated test database, defined in `docker-compose.yml`. Start these services in detached mode:
    ```bash
    docker-compose up -d
    ```
    This command will start the main development database (`postgres`), Redis (`redis`), the Celery worker (`celery`), and crucially, the **test database** (`db_test`) which listens on `localhost:5434`. The tests are configured (via `.env` and `core/config.py`) to connect to this specific database instance. Ensure the `virtualstack_db_test` container is running (`docker ps`).

## Running Tests

All tests are located within the `tests/` directory, primarily under `tests/functional/`.

*   **Run All Tests:** Execute the following command from the project root:
    ```bash
    poetry run pytest tests/
    ```
    This will discover and run all tests within the `tests/` directory using the Poetry-managed environment.

*   **Run Specific File/Test:** You can target specific files or tests:
    ```bash
    # Run all tests in a specific file
    poetry run pytest tests/functional/test_tenants.py

    # Run a specific test function
    poetry run pytest tests/functional/test_tenants.py::test_create_tenant_success
    ```

## Measuring Code Coverage

To check how much of the application code is exercised by the tests:

1.  **Run Tests with Coverage:**
    ```bash
    poetry run pytest --cov=src/virtualstack tests/
    ```
    The `--cov=src/virtualstack` flag tells `pytest-cov` to measure coverage for the code within the `src/virtualstack` directory.

2.  **Generate HTML Report (Optional):** For a more detailed view:
    ```bash
    poetry run pytest --cov=src/virtualstack --cov-report=html tests/
    ```
    This will generate an `htmlcov/` directory containing an interactive HTML report. Open `htmlcov/index.html` in your browser.

Our target code coverage is **80%**.

## Current Test Status (As of 2025-04-16)

*   **Pytest Execution:** Stopped after error in `scripts/test_api_basic.py`.
*   **Passed Tests:** 1 (`test_health_check`).
*   **Error:** 1 (`test_login`) - fixture 'client' not found.
*   **Coverage:** Not calculated (test suite did not complete).

**Next Steps:**

*   Fix fixture error or adjust test discovery to exclude scripts directory.
*   Re-run full test suite in `tests/` directory to calculate coverage.

## Test Structure

*   **Functional Tests:** Located in `tests/functional/`, these tests interact with the application via HTTP requests, testing end-to-end behavior of API endpoints.
*   **Unit Tests:** (Currently minimal/none) Would be located in `tests/unit/` for testing isolated components like utility functions or specific service logic in isolation (using mocking).
*   **Fixtures:** Core test setup, like database initialization and authenticated HTTP clients, are defined as fixtures in `tests/conftest.py` to be reused across multiple tests.