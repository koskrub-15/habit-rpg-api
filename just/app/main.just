import "vars.just"
import "configs.just"
import "docker.just"

# Make all actions needed for run the app from zero.
app-i-docker-i-run: init-i-configs d-up

# Make all actions needed for purge the app related data.
app-i-docker-i-purge: d-purge
