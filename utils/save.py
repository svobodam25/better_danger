import json
import os
import tempfile

SAVE_FILENAME = "savegame.json"
SAVE_VERSION = 1


def _save_path():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, SAVE_FILENAME)


def has_save():
    return os.path.isfile(_save_path())


def delete_save():
    path = _save_path()
    if os.path.isfile(path):
        try:
            os.remove(path)
        except OSError:
            pass


def save_game(player, known_planets):
    """Serialize player state + known planet grid coords to disk.
    Planets are regenerated deterministically from their grid (gx, gy) on load."""
    data = {
        "version": SAVE_VERSION,
        "player": {
            "x": player.x, "y": player.y,
            "vx": player.vx, "vy": player.vy,
            "angle": player.angle,
            "dock_cooldown": player.dock_cooldown,
            "fuel": player.fuel, "max_fuel": player.max_fuel,
            "hp": player.hp, "max_hp": player.max_hp,
            "max_cargo": player.max_cargo,
            "acceleration": player.acceleration,
            "turn_rate": player.turn_rate,
            "credits": player.credits,
            "total_earned": player.total_earned,
            "inventory": player.inventory,
            "upgrades": sorted(player.upgrades),
            "has_retro": player.has_retro,
            "has_hyperdrive": player.has_hyperdrive,
            "has_long_scanner": player.has_long_scanner,
            "has_mining_drill": player.has_mining_drill,
            "waypoint": list(player.waypoint) if player.waypoint else None,
            "mined_asteroids": sorted(player.mined_asteroids),
        },
        "known_planet_grid": [
            [int(p.x), int(p.y)] for p in known_planets
        ],
    }
    path = _save_path()
    # Atomic write: tmp file then replace, so a crash mid-write won't corrupt the save.
    tmp_fd, tmp_path = tempfile.mkstemp(
        prefix=".savegame-", suffix=".tmp",
        dir=os.path.dirname(path))
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp_path, path)
        return True
    except OSError:
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        return False


def load_game():
    """Read save from disk. Returns dict or None if missing/corrupt."""
    path = _save_path()
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    if data.get("version") != SAVE_VERSION:
        return None
    return data


def apply_to_player(player, data):
    """Restore saved player fields onto a fresh Player. Does NOT restore known planets —
    the caller is responsible for regenerating planets from known_planet_grid."""
    p = data["player"]
    player.x = p["x"]; player.y = p["y"]
    player.vx = p["vx"]; player.vy = p["vy"]
    player.angle = p["angle"]
    player.dock_cooldown = p.get("dock_cooldown", 0.0)
    player.fuel = p["fuel"]; player.max_fuel = p["max_fuel"]
    player.hp = p["hp"]; player.max_hp = p["max_hp"]
    player.max_cargo = p["max_cargo"]
    player.acceleration = p["acceleration"]
    player.turn_rate = p["turn_rate"]
    player.credits = p["credits"]
    player.total_earned = p["total_earned"]
    player.inventory = p["inventory"]
    player.upgrades = set(p["upgrades"])
    player.has_retro = p["has_retro"]
    player.has_hyperdrive = p["has_hyperdrive"]
    player.has_long_scanner = p["has_long_scanner"]
    player.has_mining_drill = p["has_mining_drill"]
    player.waypoint = tuple(p["waypoint"]) if p["waypoint"] else None
    player.mined_asteroids = set(p["mined_asteroids"])
