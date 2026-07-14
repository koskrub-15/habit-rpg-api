import "vars.just"

# Show user id
@echo-i-user-id:
    echo {{ user_id }}

# Run the app without docker.
app-i-run:
    uv run uvicorn apps.main:app --reload

# Cleanup after the app without docker. Example.
app-i-purge:
    @echo Goodbye
