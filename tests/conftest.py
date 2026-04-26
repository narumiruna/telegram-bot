import os

# Callback tests exercise logfire spans without booting the full app.
os.environ.setdefault("LOGFIRE_IGNORE_NO_CONFIG", "1")
