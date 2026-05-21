import math
import settings as cfg


def apply_thrust(player, dt, reverse=False, boost_multiplier=1.0):
    """Apply newtonian thrust in the direction the ship is facing.
    Retro (reverse) thrust is weaker than forward thrust."""
    if player.fuel <= 0:
        return

<<<<<<< Updated upstream
    rad = math.radians(player.angle)
<<<<<<< Updated upstream
<<<<<<< HEAD
    direction = -1 if reverse else 1
    accel = player.acceleration * direction * boost_multiplier
=======
=======
>>>>>>> Stashed changes
    if reverse:
        accel = player.acceleration * cfg.RETRO_THRUST_MULT
        speed = math.hypot(player.vx, player.vy)
        if speed > 0:
            rad = math.atan2(player.vy, player.vx)
            dv = accel * dt
            if dv > speed:
                player.vx = 0.0
                player.vy = 0.0
            else:
                player.vx -= math.cos(rad) * dv
                player.vy -= math.sin(rad) * dv
        fuel_mult = cfg.RETRO_THRUST_MULT
    else:
        rad = math.radians(player.angle)
        accel = player.acceleration
<<<<<<< Updated upstream
>>>>>>> origin/main
=======
    
    if reverse:
        accel = -player.acceleration * cfg.RETRO_THRUST_MULT * boost_multiplier
        fuel_mult = cfg.RETRO_THRUST_MULT
    else:
        accel = player.acceleration * boost_multiplier
        fuel_mult = 1.0
>>>>>>> Stashed changes

    player.vx += math.cos(rad) * accel * dt
    player.vy += math.sin(rad) * accel * dt

<<<<<<< Updated upstream
<<<<<<< HEAD
    # Fuel consumption (zvyšuje se při boostu)
    fuel_use = cfg.FUEL_CONSUMPTION * dt * boost_multiplier
=======
    # Fuel consumption (retro uses less since it's weaker)
    fuel_mult = cfg.RETRO_THRUST_MULT if reverse else 1.0
=======
        player.vx += math.cos(rad) * accel * dt
        player.vy += math.sin(rad) * accel * dt
        fuel_mult = 1.0

    # Fuel consumption
>>>>>>> Stashed changes
    fuel_use = cfg.FUEL_CONSUMPTION * fuel_mult * dt
>>>>>>> origin/main
=======
    # Fuel consumption
    fuel_use = cfg.FUEL_CONSUMPTION * fuel_mult * dt * boost_multiplier
>>>>>>> Stashed changes
    player.fuel = max(0, player.fuel - fuel_use)

    player.thrusting = True


def apply_drag(player, speed_limit_multiplier=1.0):
    """No drag in space — velocity is preserved indefinitely. Cap max speed."""
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
    player.thrusting = False


def distance_to_planet(player, planet):
    """Euclidean distance from player to planet center."""
    return math.hypot(player.x - planet.x, player.y - planet.y)


def angle_to_planet(player, planet):
    """Angle from player to planet in degrees (0 = right, 90 = down)."""
    dx = planet.x - player.x
    dy = planet.y - player.y
    return math.degrees(math.atan2(dy, dx)) % 360


def warp_jump(player, target_x, target_y):
    """Execute a hyperdrive jump."""
    if not player.has_hyperdrive:
        return False
    if player.fuel < cfg.WARP_FUEL_COST:
        return False
    player.fuel -= cfg.WARP_FUEL_COST
    player.x = target_x
    player.y = target_y
    player.vx = 0
    player.vy = 0
    player.trail.clear()
    return True


def check_planet_collision(player, planet):
    """Check if player is close enough to dock."""
    dist = distance_to_planet(player, planet)
    return dist < cfg.DOCK_PROXIMITY + planet.radius
