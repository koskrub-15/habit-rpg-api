# Recipes for running tests

# Install pytest and coverage tools
@test-i-install:
    uv add --dev pytest pytest-cov &&\
    uv run pytest --version

# Run all tests with coverage
@test-i-run:
    COVERAGE_CORE=sysmon uv run pytest --cov=apps --cov-report=term-missing tests

# Run tests for specific path or file: just test-i-file tests/test_users.py
@test-i-file path:
    COVERAGE_CORE=sysmon uv run pytest --cov=apps --cov-report=term-missing {{ path }}

# Run tests matching a keyword: just test-i-keyword "test_create_user"
@test-i-keyword keyword:
    COVERAGE_CORE=sysmon uv run pytest --cov=apps --cov-report=term-missing -k "{{ keyword }}" tests

# Run tests with a specific marker: just test-i-marker "unit"
@test-i-marker marker:
    COVERAGE_CORE=sysmon uv run pytest --cov=apps --cov-report=term-missing -m "{{ marker }}" tests

# Run tests, stop on first failure
@test-i-fail-fast:
    COVERAGE_CORE=sysmon uv run pytest --cov=apps --cov-report=term-missing -x tests

# Run tests without coverage (faster for quick checks)
@test-i-fast:
    uv run pytest tests
