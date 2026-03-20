# Recipes for running tests

@test:
    uv run pytest --cov=apps --cov-report=term-missing tests
