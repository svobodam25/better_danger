# Universal Unique ID generator for procedural planets
import hashlib
import random


def planet_id(x, y):
    """Generate a deterministic seed-based ID for a planet at coordinates."""
    return hashlib.md5(f"{x},{y}".encode()).hexdigest()[:8]


def planet_name(seed_x, seed_y):
    """Generate a deterministic planet name from coordinates."""
    prefixes = ["Nova", "Old", "New", "Alpha", "Beta", "Gamma", "Delta",
                "Red", "Blue", "Dark", "White", "Iron", "Star", "Neo",
                "Port", "Fort", "Gold", "Silver", "Sand", "Ice", "Fire",
                "Deep", "High", "Lost", "Free", "Grand", "Crystal", "Shadow"]
    suffixes = ["Prime", "Haven", "Core", "Station", "Point", "Reach",
                "Landing", "Base", "World", "Colony", "Outpost", "Hub",
                "Port", "City", "Gate", "Hold", "Rest", "End", "Dawn",
                "Falls", "Peak", "Forge", "Bay", "Home"]
    rng = random.Random(f"{seed_x},{seed_y}")
    return f"{rng.choice(prefixes)} {rng.choice(suffixes)}"


def snap_to_grid(value, spacing):
    """Snap a coordinate to the nearest grid point."""
    return round(value / spacing) * spacing
