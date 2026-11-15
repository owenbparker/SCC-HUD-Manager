"""Every HUD the main client knows: where its releases are, what it's called
on disk, and where it's installed (each HUD's own installer folder, so a HUD
installed on its own is found, and its own self-update keeps working).

A new HUD is one more entry here (and its logo in web/assets/games).
"""

HUDS = [
    {"id": "lol", "name": "League of Legends HUD", "repo": "owenbparker/LeagueHUDSCC",
     "asset": "LeagueHUD-windows.zip", "exe": "LeagueHUD.exe", "folder": r"C:\SCC LoL HUD",
     "logo": "assets/games/lol.svg", "port": 8777},
    {"id": "val", "name": "VALORANT HUD", "repo": "owenbparker/VALHUDSCC",
     "asset": "ValorantHUD-windows.zip", "exe": "ValorantHUD.exe", "folder": r"C:\SCC VAL HUD",
     "logo": "assets/games/valorant.svg", "port": 8778},
    {"id": "cod", "name": "Call of Duty HUD", "repo": "owenbparker/COD_SCC_HUD",
     "asset": "CodHUD-windows.zip", "exe": "CodHUD.exe", "folder": r"C:\SCC CoD HUD",
     "logo": "assets/games/cod.png", "port": 8780},
    {"id": "rl", "name": "Rocket League HUD", "repo": "owenbparker/RLHUD_SCC",
     "asset": "RocketLeagueHUD-windows.zip", "exe": "RocketLeagueHUD.exe", "folder": r"C:\SCC RL HUD",
     "logo": "assets/games/rocketleague.png", "port": 8781},
    {"id": "smash", "name": "Smash Ultimate HUD", "repo": "owenbparker/SmashHUD_SCC",
     "asset": "SmashHUD-windows.zip", "exe": "SmashHUD.exe", "folder": r"C:\SCC Smash HUD",
     "logo": "assets/games/smash.png", "port": 8784},
    {"id": "ow", "name": "Overwatch HUD", "repo": "owenbparker/OWHUD_SCC",
     "asset": "OverwatchHUD-windows.zip", "exe": "OverwatchHUD.exe", "folder": r"C:\SCC Overwatch HUD",
     "logo": "assets/games/overwatch.png", "port": 8785},
    {"id": "gfx", "name": "GFX Engine", "repo": "owenbparker/GFX-Engine",
     "asset": "GFXEngine-windows.zip", "exe": "GFXEngine.exe", "folder": r"C:\SCC GFX Engine",
     "logo": "assets/games/gfx.png", "port": 8782},
]


def by_id(hud_id):
    for h in HUDS:
        if h["id"] == hud_id:
            return h
    raise ValueError(f"no HUD called {hud_id!r}")
