# SCC HUD Manager

Every St. Clair Saints broadcast HUD in one app. Each game's logo opens its
HUD; under it are the installed version and, when there's a newer release,
an **Update** button (or **Install** for one that isn't on the PC yet).

| Game | HUD | Installed in |
| --- | --- | --- |
| League of Legends | [LeagueHUDSCC](https://github.com/owenbparker/LeagueHUDSCC) | `C:\SCC LoL HUD` |
| VALORANT | [VALHUDSCC](https://github.com/owenbparker/VALHUDSCC) | `C:\SCC VAL HUD` |
| Call of Duty | [COD_SCC_HUD](https://github.com/owenbparker/COD_SCC_HUD) | `C:\SCC CoD HUD` |
| Rocket League | [RLHUD_SCC](https://github.com/owenbparker/RLHUD_SCC) | `C:\SCC RL HUD` |
| Super Smash Bros. Ultimate | [SmashHUD_SCC](https://github.com/owenbparker/SmashHUD_SCC) | `C:\SCC Smash HUD` |

## Install

Download **SCC-HUD-Manager-Setup.exe** from the
[latest release](https://github.com/owenbparker/SCC-HUD-Manager/releases/latest)
and run it. It installs the manager to `C:\SCC HUD Manager` with a desktop
shortcut, then installs every HUD (from each HUD's own latest release) in
its usual folder. HUDs already installed there are updated and keep their
settings. The manager updates itself, and each HUD still can on its own.

Updating a HUD that's running closes it first (after asking).

## Adding a HUD

Add it to `scchud/catalog.py` (its repo, release zip, exe and folder) and its
logo to `web/assets/games/`. Its build should put a `version.txt` (the release
tag) in the zip, as the other HUDs' builds do.

## From source

```
pip install -r requirements-windows.txt
python -m scchud.gui                 # the desktop app
python -m scchud.gui --install-all   # install or update every HUD
python -m unittest discover -s tests
```
