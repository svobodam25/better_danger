import math
import settings as cfg


def apply_thrust(player, dt, reverse=False, boost_multiplier=1.0):
    """Apply newtonian thrust.
    Forward thrust pushes in the direction the ship is facing.
    Retro (reverse) thrust pushes opposite to current velocity at RETRO_THRUST_MULT power
    — actual braking, harder than accelerating. Boost (Shift) scales thrust and fuel."""
    if player.fuel <= 0:
        return

    if reverse:
        # Retro brake — push against velocity vector at reduced power
        accel = player.acceleration * cfg.RETRO_THRUST_MULT * boost_multiplier
        speed = math.hypot(player.vx, player.vy)
        if speed > 0:
            vel_angle = math.atan2(player.vy, player.vx)
            dv = accel * dt
            if dv >= speed:
                # Don't overshoot zero
                player.vx = 0.0
                player.vy = 0.0
            else:
                player.vx -= math.cos(vel_angle) * dv
                player.vy -= math.sin(vel_angle) * dv
        fuel_mult = cfg.RETRO_THRUST_MULT * boost_multiplier
    else:
        rad = math.radians(player.angle)
        accel = player.acceleration * boost_multiplier
        player.vx += math.cos(rad) * accel * dt
        player.vy += math.sin(rad) * accel * dt
        fuel_mult = boost_multiplier

    fuel_use = cfg.FUEL_CONSUMPTION * fuel_mult * dt
    player.fuel = max(0, player.fuel - fuel_use)

    player.thrusting = True


def apply_drag(player, speed_limit_multiplier=1.0):
    """No drag in space — newtonian. MAX_SPEED is effectively uncapped (1M),
    so this is a no-op in practice but supports a future hard cap if desired."""
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
