"""Installing, updating and starting the HUDs.

Each HUD's latest release is asked of GitHub; the installed version is the
version.txt in its folder (the HUD's builds ship one, and this app writes it
after installing). Installing or updating downloads the release zip
(checking its SHA-256 when GitHub gives one), unpacks it and copies the app
in, leaving the HUD's settings, logos and other files alone.
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import zipfile

from . import catalog
from .config import DATA_DIR
from .log import log
from .updater import is_newer, parse_version


def github_latest(repo):
    """The latest release of repo (GitHub's JSON), or None if it has none."""
    req = urllib.request.Request(f"https://api.github.com/repos/{repo}/releases/latest",
                                 headers={"Accept": "application/vnd.github+json", "User-Agent": "SCC-HUD"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


def download(url, path, size=0, progress=None):
    req = urllib.request.Request(url, headers={"User-Agent": "SCC-HUD"})
    digest = hashlib.sha256()
    done = 0
    with urllib.request.urlopen(req, timeout=30) as r, open(path, "wb") as f:
        while True:
            chunk = r.read(256 * 1024)
            if not chunk:
                break
            f.write(chunk)
            digest.update(chunk)
            done += len(chunk)
            if progress and size:
                progress(min(99, int(done * 100 / size)))
    return digest.hexdigest()


def running(exe):
    """Is a program called exe running on this PC?"""
    if sys.platform != "win32":
        return False
    try:
        out = subprocess.run(["tasklist", "/FI", f"IMAGENAME eq {exe}", "/NH"], capture_output=True, text=True,
                             creationflags=0x08000000, timeout=10).stdout
    except Exception:
        return False
    return exe.lower() in out.lower()


def close(exe):
    if sys.platform == "win32":
        subprocess.run(["taskkill", "/IM", exe, "/F"], capture_output=True, creationflags=0x08000000, timeout=15)
        for _ in range(20):
            if not running(exe):
                return
            time.sleep(0.25)


class Hud:
    """One HUD: what's installed, what's out, and what's happening to it."""

    def __init__(self, entry, folder):
        self.entry = entry
        self.folder = folder
        self.latest = None        # GitHub's latest release
        self.check_error = None
        self.status = "idle"      # idle, downloading, installing, error
        self.progress = 0
        self.error = None
        self.lock = threading.Lock()

    @property
    def exe_path(self):
        return os.path.join(self.folder, self.entry["exe"])

    def installed(self):
        return os.path.isfile(self.exe_path)

    def version(self):
        try:
            with open(os.path.join(self.folder, "version.txt"), encoding="utf-8-sig") as f:
                return f.read().strip() or None
        except OSError:
            return None

    def asset(self):
        if not self.latest:
            return None
        return next((a for a in self.latest.get("assets", []) if a.get("name") == self.entry["asset"]), None)

    def info(self):
        installed, version = self.installed(), self.version()
        latest = self.latest.get("tag_name") if self.latest and self.asset() else None
        update = bool(installed and latest and (version is None or is_newer(latest, version)))
        return {"id": self.entry["id"], "name": self.entry["name"], "logo": self.entry["logo"], "folder": self.folder,
                "installed": installed, "version": version, "latest": latest, "update": update,
                "released": latest is not None, "notes": (self.latest or {}).get("body", "").strip()[:800],
                "status": self.status, "progress": self.progress, "error": self.error, "check_error": self.check_error,
                "running": running(self.entry["exe"]) if installed else False}


class Manager:
    def __init__(self, root=None, latest=github_latest):
        """root: put every HUD under this folder instead of its usual one (tests)."""
        self.huds = {}
        for e in catalog.HUDS:
            folder = os.path.join(root, os.path.basename(e["folder"])) if root else e["folder"]
            self.huds[e["id"]] = Hud(e, folder)
        self._latest = latest
        self.work_dir = os.path.join(DATA_DIR, "_downloads")

    def info(self):
        return [h.info() for h in self.huds.values()]

    def check(self):
        """Asks GitHub for every HUD's latest release."""
        for h in self.huds.values():
            try:
                h.latest, h.check_error = self._latest(h.entry["repo"]), None
            except Exception as e:
                h.check_error = str(getattr(e, "reason", e))
                log(f"Couldn't check {h.entry['name']} for updates ({h.check_error})", "warn")
        out = [f"{h.entry['name']} {h.version() or '-'}" + (f" (update: {i['latest']})" if i["update"] else "")
               for h, i in ((h, h.info()) for h in self.huds.values()) if h.installed()]
        if out:
            log("Installed: " + ", ".join(out))

    def check_in_background(self):
        threading.Thread(target=self.check, daemon=True).start()

    def launch(self, hud_id):
        h = self.huds[catalog.by_id(hud_id)["id"]]
        if not h.installed():
            raise ValueError(f"{h.entry['name']} isn't installed yet")
        flags = 0x00000008 | 0x00000200 if sys.platform == "win32" else 0   # detached, own process group
        subprocess.Popen([h.exe_path], cwd=h.folder, close_fds=True, creationflags=flags)
        log(f"Started {h.entry['name']}")

    def install_in_background(self, hud_id, close_running=False):
        h = self.huds[catalog.by_id(hud_id)["id"]]
        with h.lock:
            if h.status in ("downloading", "installing"):
                return
            if not h.asset():
                raise ValueError(f"{h.entry['name']} has no release to install yet")
            if running(h.entry["exe"]) and not close_running:
                raise ValueError(f"{h.entry['name']} is running: close it first")
            h.status, h.progress, h.error = "downloading", 0, None
        threading.Thread(target=self._install, args=(h, close_running), daemon=True).start()

    def install(self, hud_id, close_running=False):
        """The same, waiting for it (the installer's first run, tests)."""
        h = self.huds[catalog.by_id(hud_id)["id"]]
        h.status, h.progress, h.error = "downloading", 0, None
        self._install(h, close_running)
        if h.status == "error":
            raise RuntimeError(h.error)

    def _install(self, h, close_running):
        name, asset, tag = h.entry["name"], h.asset(), h.latest["tag_name"]
        work = os.path.join(self.work_dir, f"{h.entry['id']}-{int(time.time())}")
        try:
            os.makedirs(work, exist_ok=True)
            zip_path = os.path.join(work, asset["name"])
            got = download(asset["browser_download_url"], zip_path, asset.get("size") or 0,
                           lambda p: setattr(h, "progress", p))
            expected = (asset.get("digest") or "").removeprefix("sha256:")
            if expected and got != expected:
                raise ValueError("the download didn't match GitHub's checksum; try again")
            h.status, h.progress = "installing", 100
            new = os.path.join(work, "new")
            with zipfile.ZipFile(zip_path) as z:
                for member in z.namelist():   # refuse paths that climb out of the folder
                    target = os.path.normpath(os.path.join(new, member))
                    if not target.startswith(os.path.normpath(new) + os.sep):
                        raise ValueError(f"unexpected file in the download: {member}")
                z.extractall(new)
            if not os.path.isfile(os.path.join(new, h.entry["exe"])):
                raise ValueError(f"the download doesn't contain {h.entry['exe']}")
            if running(h.entry["exe"]):
                if not close_running:
                    raise ValueError(f"{name} is running: close it first")
                close(h.entry["exe"])
            copy_app(new, h.folder)
            with open(os.path.join(h.folder, "version.txt"), "w", encoding="utf-8") as f:
                f.write(tag)
            h.status = "idle"
            log(f"Installed {name} {tag} in {h.folder}")
        except Exception as e:
            h.status, h.error = "error", f"{e}"
            log(f"Couldn't install {name}: {e}", "error")
        finally:
            shutil.rmtree(work, ignore_errors=True)


def copy_app(new, folder):
    """Copies a HUD's new files into its folder: its _internal folder is
    replaced, its other files overwritten; anything else there (settings,
    logos, output) stays."""
    os.makedirs(folder, exist_ok=True)
    internal = os.path.join(new, "_internal")
    if os.path.isdir(internal):
        old = os.path.join(folder, "_internal")
        if os.path.isdir(old):
            shutil.rmtree(old)
        shutil.copytree(internal, old)
    for name in os.listdir(new):
        src = os.path.join(new, name)
        if name == "_internal":
            continue
        dst = os.path.join(folder, name)
        if os.path.isdir(src):
            shutil.copytree(src, dst, dirs_exist_ok=True)
        else:
            shutil.copyfile(src, dst)


__all__ = ["Manager", "copy_app", "parse_version"]
