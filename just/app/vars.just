# Get user id for macOS and Linux

user_id := if shell("uname") == "Darwin" { shell("id -u") } else { shell("id --user") }
