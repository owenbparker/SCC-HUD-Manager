"""Run the manager's page without a window:  python -m scchud  (then open http://127.0.0.1:8790/)."""

import time

from .app import ManagerApp, start, stop
from .config import PORT

if __name__ == "__main__":
    app = ManagerApp()
    start(app, PORT)
    print("  Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        stop(app)
