import "vars.just"

# Show user id
@echo-i-user-id:
    echo {{ user_id }}

# Run the app without docker. Example.
app-i-run:
    @python main.py

# Cleanup after the app without docker. Example.
app-i-purge:
    @echo Goodbye
