"""The desktop app: the manager's page in its own window.

    HUDManager.exe                 the built app
    HUDManager.exe --install-all   install (or update) every HUD, then quit (the installer runs this)
    python -m scchud.gui           the same, from source (needs: pip install pywebview)
"""

import argparse
import json
import os
import sys
import urllib.request
import webbrowser

from .app import ManagerApp, start, stop
from .config import DATA_DIR, PORT
from .log import log

TITLE = "SCC HUD Manager"


def message_box(text, title=TITLE, error=False):
    if sys.platform == "win32":
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, text, title, 0x10 if error else 0x40)
    else:
        print(f"{title}: {text}")


def already_running(port):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/state", timeout=2) as r:
            return "huds" in json.loads(r.read())
    except Exception:
        return False


def install_all(app):
    """Installs every released HUD that isn't installed or is out of date.
    Writes install-all.txt next to the app; True if all went well."""
    app.manager.check()
    lines, ok = [], True
    for hud in app.manager.huds.values():
        info = hud.info()
        if not info["released"]:
            lines.append(f"SKIP {info['name']}: no release yet" + (f" ({info['check_error']})" if info["check_error"] else ""))
            ok = ok and not info["check_error"]
            continue
        if info["installed"] and not info["update"]:
            lines.append(f"OK   {info['name']} {info['version']} (up to date)")
            continue
        try:
            app.manager.install(info["id"], close_running=True)
            lines.append(f"OK   {info['name']} {hud.version()} installed in {hud.folder}")
        except Exception as e:
            ok = False
            lines.append(f"FAIL {info['name']}: {e}")
    with open(os.path.join(DATA_DIR, "install-all.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines + ["PASSED" if ok else "FAILED"]) + "\n")
    return ok


def smoke_test(port):
    """Used by the build: the packaged app serves its page and can load its
    window library. Writes smoke-test.txt next to the app."""
    results, ok = [], True
    for path in ("/", "/api/state", "/update.js", "/fonts/Inter.ttf", "/assets/bg_loop.mp4",
                 "/assets/games/lol.svg", "/assets/games/valorant.svg", "/assets/games/cod.png", "/assets/games/rocketleague.png",
                 "/assets/games/smash.png", "/assets/games/overwatch.svg"):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=5) as r:
                results.append(f"OK   {path} ({len(r.read())} bytes)")
        except Exception as e:
            ok = False
            results.append(f"FAIL {path}: {e}")
    try:
        import webview  # noqa: F401
        if sys.platform == "win32":
            import webview.platforms.winforms  # noqa: F401
        results.append("OK   window library")
    except Exception as e:
        ok = False
        results.append(f"FAIL window library: {e!r}")
    with open(os.path.join(DATA_DIR, "smoke-test.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(results + ["PASSED" if ok else "FAILED"]) + "\n")
    return ok


def main():
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w")
    parser = argparse.ArgumentParser(description="SCC HUD Manager")
    parser.add_argument("--port", type=int, default=PORT)
    parser.add_argument("--debug", action="store_true", help="allow right-click > Inspect in the window")
    parser.add_argument("--install-all", action="store_true", help="install or update every HUD, then quit")
    parser.add_argument("--smoke-test", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()

    app = ManagerApp()
    if args.install_all:
        return 0 if install_all(app) else 1

    url = f"http://127.0.0.1:{args.port}/"
    own = True
    try:
        start(app, args.port)
    except OSError as e:
        if not already_running(args.port):
            message_box(f"Couldn't start on port {args.port}:\n{e}", error=True)
            return 1
        own = False   # another copy is running: open a window onto it

    if args.smoke_test:
        ok = smoke_test(args.port)
        stop(app)
        return 0 if ok else 1

    try:
        import webview
        window = webview.create_window(f"{TITLE} {app.updater.current}", url, width=1280, height=720,
                                       min_size=(900, 560), background_color="#08120c")
        app.updater.on_exit = window.destroy
        webview.start(debug=args.debug)
    except Exception as e:
        log(f"Couldn't open the app window ({e!r}); using the web browser instead", "warn")
        webbrowser.open(url)
        if own:
            message_box("SCC HUD Manager has opened in your web browser.\n\nIt keeps running until you close this box.")
    finally:
        if own:
            stop(app)
    return 0


if __name__ == "__main__":
    sys.exit(main())
