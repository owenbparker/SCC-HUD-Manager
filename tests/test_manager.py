import hashlib
import json
import os
import tempfile
import time
import unittest
import urllib.request
import zipfile

from scchud import catalog
from scchud.manager import Manager, copy_app


def make_release(folder, entry, tag, files):
    """A release zip for entry (as the HUD's build makes it), and GitHub's JSON for it."""
    path = os.path.join(folder, f"{entry['id']}-{tag}.zip")
    with zipfile.ZipFile(path, "w") as z:
        for name, data in files.items():
            z.writestr(name, data)
    with open(path, "rb") as f:
        digest = hashlib.sha256(f.read()).hexdigest()
    return {"tag_name": tag, "body": "Notes", "assets": [{
        "name": entry["asset"], "size": os.path.getsize(path), "digest": "sha256:" + digest,
        "browser_download_url": "file:///" + path.replace("\\", "/").lstrip("/")}]}


class ManagerTests(unittest.TestCase):
    def test_install_update_and_keep_settings(self):
        lol = catalog.by_id("lol")
        with tempfile.TemporaryDirectory() as tmp:
            releases = {lol["repo"]: make_release(tmp, lol, "v1.0.5", {
                "LeagueHUD.exe": "exe 5", "_internal/web/a.txt": "a5", "_internal/old.txt": "x", "version.txt": "v1.0.5"})}
            m = Manager(root=os.path.join(tmp, "C"), latest=lambda repo: releases.get(repo))
            m.check()
            info = {h["id"]: h for h in m.info()}
            self.assertFalse(info["lol"]["installed"])
            self.assertTrue(info["lol"]["released"])
            self.assertFalse(info["val"]["released"])
            m.install("lol")
            hud = m.huds["lol"]
            self.assertEqual(hud.version(), "v1.0.5")
            self.assertTrue(hud.installed())
            # The HUD's own files (settings, logos) stay through an update.
            with open(os.path.join(hud.folder, "config.json"), "w") as f:
                f.write("{}")
            releases[lol["repo"]] = make_release(tmp, lol, "v1.0.6", {
                "LeagueHUD.exe": "exe 6", "_internal/web/a.txt": "a6"})
            m.check()
            self.assertTrue(m.huds["lol"].info()["update"])
            m.install("lol")
            self.assertEqual(hud.version(), "v1.0.6")   # written by the manager (no version.txt in that zip)
            self.assertFalse(hud.info()["update"])
            with open(os.path.join(hud.folder, "_internal", "web", "a.txt")) as f:
                self.assertEqual(f.read(), "a6")
            self.assertFalse(os.path.exists(os.path.join(hud.folder, "_internal", "old.txt")))
            self.assertTrue(os.path.exists(os.path.join(hud.folder, "config.json")))

    def test_bad_downloads_are_refused(self):
        lol = catalog.by_id("lol")
        with tempfile.TemporaryDirectory() as tmp:
            rel = make_release(tmp, lol, "v1.0.7", {"LeagueHUD.exe": "exe"})
            rel["assets"][0]["digest"] = "sha256:" + "0" * 64
            m = Manager(root=os.path.join(tmp, "C"), latest=lambda repo: rel if repo == lol["repo"] else None)
            m.check()
            with self.assertRaises(RuntimeError):
                m.install("lol")
            self.assertFalse(m.huds["lol"].installed())
            rel = make_release(tmp, lol, "v1.0.8", {"README.md": "no exe"})
            m = Manager(root=os.path.join(tmp, "C"), latest=lambda repo: rel if repo == lol["repo"] else None)
            m.check()
            with self.assertRaises(RuntimeError):
                m.install("lol")

    def test_unknown_version_offers_the_update(self):
        lol = catalog.by_id("lol")
        with tempfile.TemporaryDirectory() as tmp:
            rel = make_release(tmp, lol, "v1.0.9", {"LeagueHUD.exe": "exe"})
            m = Manager(root=tmp, latest=lambda repo: rel if repo == lol["repo"] else None)
            os.makedirs(m.huds["lol"].folder)
            open(m.huds["lol"].exe_path, "w").close()   # installed by its own installer, before version.txt
            m.check()
            self.assertTrue(m.huds["lol"].info()["update"])

    def test_update_all(self):
        lol, val = catalog.by_id("lol"), catalog.by_id("val")
        with tempfile.TemporaryDirectory() as tmp:
            releases = {e["repo"]: make_release(tmp, e, "v1.0.2", {e["exe"]: "new"}) for e in (lol, val)}
            m = Manager(root=os.path.join(tmp, "C"), latest=lambda repo: releases.get(repo))
            for e in (lol, val):   # both installed at v1.0.1
                h = m.huds[e["id"]]
                os.makedirs(h.folder)
                open(h.exe_path, "w").close()
                with open(os.path.join(h.folder, "version.txt"), "w") as f:
                    f.write("v1.0.1")
            m.check()
            done = []
            m.update_all_in_background(then=lambda: done.append(True))
            for _ in range(100):
                if done:
                    break
                time.sleep(0.05)
            self.assertEqual(done, [True])
            self.assertFalse(m.updating_all)
            for e in (lol, val):
                self.assertEqual(m.huds[e["id"]].version(), "v1.0.2")
                self.assertFalse(m.huds[e["id"]].info()["update"])
            self.assertFalse(m.huds["cod"].installed())   # not installed: left alone
            with self.assertRaises(ValueError):
                m.update_all_in_background()

    def test_copy_app(self):
        with tempfile.TemporaryDirectory() as tmp:
            new, dest = os.path.join(tmp, "new"), os.path.join(tmp, "dest")
            os.makedirs(os.path.join(new, "_internal"))
            open(os.path.join(new, "App.exe"), "w").close()
            copy_app(new, dest)
            self.assertTrue(os.path.isfile(os.path.join(dest, "App.exe")))


class ServerTests(unittest.TestCase):
    def test_page_and_state(self):
        from scchud.app import ManagerApp, start, stop
        with tempfile.TemporaryDirectory() as tmp:
            app = ManagerApp(Manager(root=tmp, latest=lambda repo: None))
            app.updater.check_in_background = lambda: None
            start(app, 8798)
            try:
                base = "http://127.0.0.1:8798"
                for path in ("/", "/update.js", "/assets/bg_loop.mp4", "/assets/games/cod.png", "/assets/app_icon.png"):
                    with urllib.request.urlopen(base + path, timeout=5) as r:
                        self.assertEqual(r.status, 200, path)
                        r.read()
                time.sleep(0.2)
                state = json.loads(urllib.request.urlopen(base + "/api/state", timeout=5).read())
                self.assertEqual([h["id"] for h in state["huds"]], ["lol", "val", "cod", "rl", "smash", "gfx"])
                req = urllib.request.Request(base + "/api/launch", b'{"id": "lol"}', {"Content-Type": "application/json"})
                with self.assertRaises(urllib.error.HTTPError):   # not installed
                    urllib.request.urlopen(req, timeout=5)
            finally:
                stop(app)


if __name__ == "__main__":
    unittest.main()
