import math
import settings as cfg

def apply_thrust(player, dt, reverse=False, boost_multiplier=1.0):
    """Apply newtonian thrust in the direction the ship is facing.
    Retro (reverse) thrust is weaker than forward thrust."""
    if player.fuel <= 0:
        return

    rad = math.radians(player.angle)
    
    if reverse:
        accel = -player.acceleration * cfg.RETRO_THRUST_MULT * boost_multiplier
        fuel_mult = cfg.RETRO_THRUST_MULT
    else:
        accel = player.acceleration * boost_multiplier
        fuel_mult = 1.1

    player.vx += math.cos(rad) * accel * dt
    player.vy += math.sin(rad) * accel * dt

    # Fuel consumption — boost burns extra fuel for the extra thrust.
    # Acceleration gets a 1.5x kick but the tank pays double for it.
    boost_fuel_mult = 2.0 if boost_multiplier > 1.0 else 1.0
    fuel_use = cfg.FUEL_CONSUMPTION * fuel_mult * dt * boost_fuel_mult
    player.fuel = max(0, player.fuel - fuel_use)

    player.thrusting = True


def apply_drag(player, speed_limit_multiplier=1.0):
    """No drag in space - velocity is preserved indefinitely. Cap max speed."""
    speed = math.hypot(player.vx, player.vy)
    max_s = cfg.MAX_SPEED * speed_limit_multiplier
    if speed > max_s:
        scale = max_s / speed
        player.vx *= scale
        player.vy *= scale


def rotate_player(player, direction, dt):
    """Rotate the player: direction = 1 (right) or -1 (left)."""
    player.angle += player.turn_rate * direction * dt
    player.angle %= 360


def update_position(player, dt):
    """Integrate position from velocity."""
    player.x += player.vx * dt
    player.y += player.vy * dt


def update_trail(player):
    """Add current position to exhaust trail, prune old entries."""
    if player.thrusting:
        player.trail.append((player.x, player.y))
    if len(player.trail) > cfg.EXHAUST_TRAIL_LENGTH:
        player.trail.pop(0)


def distance_to_planet(player, planet):
    """Calculate distance from player to planet center."""
    return math.hypot(player.x - planet.x, player.y - planet.y)


def check_planet_collision(player, planet):
    """Check if player is close enough to dock."""
    return distance_to_planet(player, planet) < planet.radius + cfg.DOCK_PROXIMITY


def warp_jump(player, target_x, target_y):
    """Execute a hyperdrive jump if enough fuel."""
    if player.fuel < cfg.WARP_FUEL_COST:
        return False
    player.fuel -= cfg.WARP_FUEL_COST
    player.x = target_x
    player.y = target_y
    player.vx = 0
    player.vy = 0
    player.trail.clear()
    return True
