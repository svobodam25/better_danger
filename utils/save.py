import json
import math
import os
import tempfile
import time

import settings as cfg

LEGACY_SAVE_FILENAME = "savegame.json"
SAVE_FILENAME_TEMPLATE = "savegame_{}.json"
SAVE_VERSION = 1
NUM_SAVE_SLOTS = 5


def _base_dir():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _save_path(slot):
    return os.path.join(_base_dir(), SAVE_FILENAME_TEMPLATE.format(int(slot)))


def _legacy_path():
    return os.path.join(_base_dir(), LEGACY_SAVE_FILENAME)


def _migrate_legacy():
    """One-shot: pre-slot saves used a single savegame.json. Move it into slot 1
    if no slot files exist yet, so existing players don't lose progress."""
    legacy = _legacy_path()
    if not os.path.isfile(legacy):
        return
    for s in range(1, NUM_SAVE_SLOTS + 1):
        if os.path.isfile(_save_path(s)):
            return  # at least one slot already exists, leave legacy alone
    try:
        os.rename(legacy, _save_path(1))
    except OSError:
        pass


def has_save(slot):
    _migrate_legacy()
    return os.path.isfile(_save_path(slot))


def has_any_save():
    _migrate_legacy()
    return any(os.path.isfile(_save_path(s)) for s in range(1, NUM_SAVE_SLOTS + 1))


def delete_save(slot):
    path = _save_path(slot)
    if os.path.isfile(path):
        try:
            os.remove(path)
        except OSError:
            pass


def save_game(player, known_planets, slot, docked_planet=None):
    """Serialize player state + known planet grid coords to disk in `slot`.
    Planets are regenerated deterministically from their grid (gx, gy) on load.

    If `docked_planet` is provided, the snapshot is rewritten so the player
    is placed safely outside that planet's dock proximity with velocity zeroed
    and a fresh dock cooldown — otherwise loading right back into dock range
    would auto-trigger docking again."""
    if docked_planet is not None:
        dx = player.x - docked_planet.x
        dy = player.y - docked_planet.y
        if dx == 0 and dy == 0:
            angle = 0.0  # east-by-default when player is exactly on the planet
        else:
            angle = math.atan2(dy, dx)
        safe_dist = cfg.DOCK_PROXIMITY + docked_planet.radius + 60
        save_x = docked_planet.x + math.cos(angle) * safe_dist
        save_y = docked_planet.y + math.sin(angle) * safe_dist
        save_vx = 0.0
        save_vy = 0.0
        save_dock_cd = 3.0
        dock_name = docked_planet.name
    else:
        save_x = player.x
        save_y = player.y
        save_vx = player.vx
        save_vy = player.vy
        save_dock_cd = player.dock_cooldown
        dock_name = None

    data = {
        "version": SAVE_VERSION,
        "saved_at": time.time(),
        "last_station": dock_name,
        "player": {
            "x": save_x, "y": save_y,
            "vx": save_vx, "vy": save_vy,
            "angle": player.angle,
            "dock_cooldown": save_dock_cd,
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
    path = _save_path(slot)
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


def load_game(slot):
    """Read save from `slot`. Returns dict or None if missing/corrupt."""
    _migrate_legacy()
    path = _save_path(slot)
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


def _rank_for(total_earned):
    name = "Spacer"
    for threshold, rname in cfg.RANKS:
        if total_earned >= threshold:
            name = rname
    return name


def list_saves():
    """Return [(slot, summary or None)] for every slot. summary is a dict of
    user-facing metadata for filled slots: credits, rank, planet count, last
    station, saved_at (epoch seconds)."""
    _migrate_legacy()
    results = []
    for s in range(1, NUM_SAVE_SLOTS + 1):
        data = load_game(s)
        if data is None:
            results.append((s, None))
            continue
        p = data.get("player", {})
        results.append((s, {
            "credits": int(p.get("credits", 0)),
            "rank": _rank_for(p.get("total_earned", 0)),
            "known_planets": len(data.get("known_planet_grid", [])),
            "last_station": data.get("last_station"),
            "saved_at": data.get("saved_at"),
            "hp": int(p.get("hp", 0)),
            "max_hp": int(p.get("max_hp", 0)),
        }))
    return results


def most_recent_slot():
    """Return slot number of the most recently saved game, or None."""
    best = None
    best_t = -1.0
    for slot, info in list_saves():
        if info is None:
            continue
        t = info.get("saved_at") or 0.0
        if t > best_t:
            best_t = t
            best = slot
    return best


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
