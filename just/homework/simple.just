import "vars.just"

# Show user id
@echo-i-user-id:
    echo {{ user_id }}

# Run homework without docker. Example.
homework-i-run:
    @python main.py

# Cleanup after homework without docker. Example.
homework-i-purge:
    @echo Goodbye
