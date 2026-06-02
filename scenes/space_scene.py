import math
import os
import random
import pygame
import settings as cfg
from entities.planet import Planet
from entities.player import Player
from entities.asteroid import Asteroid
from ui.hud import HUD
from ui.map_screen import MapScreen
from ui.menu import MessageBox
from utils.physics import (
    apply_thrust, apply_drag, rotate_player, update_position,
    update_trail, distance_to_planet, check_planet_collision, warp_jump,
)
from utils.helpers import snap_to_grid


class SpaceScene:
    """Scene 1: Top-down space flight with newtonian physics."""

    def __init__(self, player, font_small, font_medium, font_large):
        self.player = player
        self.font_small = font_small
        self.font_medium = font_medium
        self.font_large = font_large
        self.hud = HUD(font_small, font_medium)
        self.map_screen = MapScreen(font_small, font_medium, font_large)
        self.message = None

        # Procedural planet cache
        self.generated_planets = {}  # (gx, gy) -> Planet
        self.generated_asteroids = {}  # (gx, gy) -> Asteroid

        # Background stars (parallax layers)
        self.stars = self._generate_stars()

        # Start planet
        start_planet = self._get_or_generate_planet(0, 0)
        self.player.know_planet(start_planet)

        self.elapsed_time = 0.0
        self.next_scene = None
        self.target_planet = None
        self.target_asteroid = None    # set by F key when an asteroid is in engage range
        self._pending_mine = False

        # Load player sprite
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        img_path = os.path.join(base_dir, "obrazky elite", "pixil-frame-0 (20).png")
        try:
            self.ship_img = pygame.image.load(img_path).convert_alpha()
            # Změna velikosti lodě pokud by byla moc velká
            # self.ship_img = pygame.transform.scale(self.ship_img, (32, 32))
        except (pygame.error, FileNotFoundError) as e:
            print(f"Nepodařilo se načíst obrázek: {e}")
            self.ship_img = None

    def _generate_stars(self):
        """Generate 3 layers of background stars for parallax."""
        stars = []
        for layer, count in [(0, 80), (1, 60), (2, 40)]:
            layer_stars = []
            for _ in range(count):
                layer_stars.append({
                    "x": random.uniform(0, cfg.SCREEN_WIDTH * 2),
                    "y": random.uniform(0, cfg.SCREEN_HEIGHT * 2),
                    "r": 1 if layer == 0 else (1.5 if layer == 1 else 2),
                })
            stars.append((layer * 0.05 + 0.02, layer_stars))  # parallax factor, stars list
        return stars

    def _planet_exists_at(self, gx, gy):
        """Deterministic check whether a planet exists at this grid point.
        Origin always has one (starting planet); elsewhere PLANET_DENSITY fraction of cells."""
        if gx == 0 and gy == 0:
            return True
        rng = random.Random(f"exists:{gx}:{gy}")
        return rng.random() < cfg.PLANET_DENSITY

    def _get_or_generate_planet(self, x, y):
        """Get existing planet at grid position or generate new one."""
        gx = snap_to_grid(x, cfg.PLANET_SPACING)
        gy = snap_to_grid(y, cfg.PLANET_SPACING)
        key = (gx, gy)
        if key not in self.generated_planets:
            self.generated_planets[key] = Planet(gx, gy)
        return self.generated_planets[key]

    def _generate_nearby_planets(self):
        """Generate undiscovered planets near the player (sparse — not every grid cell)."""
        radius = cfg.GENERATION_RADIUS
        step = cfg.PLANET_SPACING
        cx = snap_to_grid(self.player.x, step)
        cy = snap_to_grid(self.player.y, step)
        for dx in range(-radius, radius + step, step):
            for dy in range(-radius, radius + step, step):
                gx = int(cx + dx)
                gy = int(cy + dy)
                key = (gx, gy)
                if key not in self.generated_planets and self._planet_exists_at(gx, gy):
                    self.generated_planets[key] = Planet(gx, gy)

    def _generate_planets_in_rect(self, min_x, min_y, max_x, max_y, max_cells=4000):
        """Lazily instantiate planets in the given world rectangle.
        Used to feed the map view so the universe looks infinite when panning."""
        step = cfg.PLANET_SPACING
        nx = int((max_x - min_x) / step) + 2
        ny = int((max_y - min_y) / step) + 2
        if nx * ny > max_cells:
            return  # zoomed out too far — skip to avoid lag
        gx_start = (int(min_x) // step) * step
        gy_start = (int(min_y) // step) * step
        gx = gx_start
        while gx <= max_x + step:
            gy = gy_start
            while gy <= max_y + step:
                key = (gx, gy)
                if key not in self.generated_planets and self._planet_exists_at(gx, gy):
                    self.generated_planets[key] = Planet(gx, gy)
                gy += step
            gx += step

    def _asteroid_exists_at(self, gx, gy):
        """Deterministic check whether an asteroid exists at this grid point."""
        rng = random.Random(f"ast-exists:{gx}:{gy}")
        return rng.random() < cfg.ASTEROID_DENSITY

    def _generate_nearby_asteroids(self):
        """Generate undiscovered asteroids near the player on a denser grid than planets."""
        radius = cfg.ASTEROID_GENERATION_RADIUS
        step = cfg.ASTEROID_SPACING
        cx = snap_to_grid(self.player.x, step)
        cy = snap_to_grid(self.player.y, step)
        for dx in range(-radius, radius + step, step):
            for dy in range(-radius, radius + step, step):
                gx = int(cx + dx)
                gy = int(cy + dy)
                key = (gx, gy)
                if key not in self.generated_asteroids and self._asteroid_exists_at(gx, gy):
                    self.generated_asteroids[key] = Asteroid(gx, gy)

    def _nearest_mineable_asteroid(self):
        """Find the closest unmined asteroid within engage range (for the F key)."""
        best = None
        best_dist = float("inf")
        for ast in self.generated_asteroids.values():
            if ast.aid in self.player.mined_asteroids:
                continue
            d = math.hypot(self.player.x - ast.x, self.player.y - ast.y)
            if d > ast.radius + cfg.MINE_ENGAGE_RANGE:
                continue
            if d < best_dist:
                best_dist = d
                best = ast
        return best

    def handle_input(self, event):
        """Handle keyboard/mouse events for space scene."""
        # Map screen takes priority
        if self.map_screen.visible:
            self.map_screen.handle_input(event, self.player)
            return None

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_m:
                self.map_screen.toggle()
            elif event.key == pygame.K_j and self.player.has_hyperdrive:
                if self.player.warp_cooldown <= 0 and self.player.fuel >= cfg.WARP_FUEL_COST:
                    angle = random.uniform(0, 2 * math.pi)
                    dist = random.uniform(cfg.WARP_MIN_DIST, cfg.WARP_MAX_DIST)
                    tx = self.player.x + math.cos(angle) * dist
                    ty = self.player.y + math.sin(angle) * dist
                    if warp_jump(self.player, tx, ty):
                        self.player.warp_cooldown = cfg.WARP_COOLDOWN
                        self.message = MessageBox("WARP JUMP!", self.font_large, -40)
            elif event.key == pygame.K_f:
                ast = self._nearest_mineable_asteroid()
                if ast:
                    self.target_asteroid = ast
                    self._pending_mine = True
                else:
                    self.message = MessageBox("No asteroid in range", self.font_small, -100)
            elif event.key == pygame.K_TAB:
                self._cycle_waypoint()
            elif event.key == pygame.K_BACKSPACE:
                if self.player.waypoint:
                    self.player.waypoint = None
                    self.message = MessageBox("Waypoint cleared", self.font_small, -120)
            elif event.key == pygame.K_ESCAPE:
                return "pause"

        return None

    def _cycle_waypoint(self):
        """Cycle through known planets, setting each as the active waypoint."""
        planets = sorted(self.player.known_planets.values(),
                         key=lambda p: math.hypot(p.x - self.player.x, p.y - self.player.y))
        if not planets:
            return
        cur_idx = -1
        if self.player.waypoint:
            for i, p in enumerate(planets):
                if (abs(p.x - self.player.waypoint[0]) < 1 and
                        abs(p.y - self.player.waypoint[1]) < 1):
                    cur_idx = i
                    break
        next_idx = (cur_idx + 1) % len(planets)
        target = planets[next_idx]
        self.player.waypoint = (target.x, target.y)
        self.message = MessageBox(f"WAYPOINT: {target.name}", self.font_small, -120)

    def update(self, dt, keys):
        """Update space scene logic."""
        if self.map_screen.visible:
            # Map screen active, but do not pause the ship logic.
            pass

        self.elapsed_time += dt

        if getattr(self.player, 'dock_cooldown', 0) > 0:
            self.player.dock_cooldown -= dt

        # Update warp cooldown
        if self.player.warp_cooldown > 0:
            self.player.warp_cooldown = max(0, self.player.warp_cooldown - dt)

        # Boost multiplier
        is_boosting = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
        boost_mult = 1.5 if is_boosting else 1.0

        # Rotation
        if keys[pygame.K_a]:
            rotate_player(self.player, -1, dt)
        if keys[pygame.K_d]:
            rotate_player(self.player, 1, dt)

        # Thrust
        if keys[pygame.K_w]:
            apply_thrust(self.player, dt, boost_multiplier=boost_mult)
        elif keys[pygame.K_s] and self.player.has_retro:
            apply_thrust(self.player, dt, reverse=True, boost_multiplier=boost_mult)

        # Apply drag (speed cap only, no friction)
        apply_drag(self.player, speed_limit_multiplier=boost_mult)

        # Update position
        update_position(self.player, dt)
        update_trail(self.player)

        # Generate nearby planets and asteroids
        self._generate_nearby_planets()
        self._generate_nearby_asteroids()

        # If the player pressed F over an asteroid, trigger the mining minigame
        if self._pending_mine and self.target_asteroid:
            self._pending_mine = False
            return "mine"

        # Check for planet proximity (docking trigger)
        for key, planet in self.generated_planets.items():
            if check_planet_collision(self.player, planet):
                if getattr(self.player, 'dock_cooldown', 0) <= 0:
                    self.target_planet = planet
                    self.player.know_planet(planet)
                    return "dock"

        # Update message
        if self.message:
            if self.message.update(dt):
                self.message = None

        return None

    def draw(self, screen):
        """Render the space scene."""
        screen.fill(cfg.BLACK)

        # Camera offset (player centered)
        cx = cfg.SCREEN_WIDTH // 2 - self.player.x
        cy = cfg.SCREEN_HEIGHT // 2 - self.player.y

        # Draw background stars with parallax
        for parallax_factor, stars in self.stars:
            for star in stars:
                sx = (star["x"] + cx * parallax_factor) % (cfg.SCREEN_WIDTH * 2)
                sy = (star["y"] + cy * parallax_factor) % (cfg.SCREEN_HEIGHT * 2)
                if sx > cfg.SCREEN_WIDTH:
                    sx -= cfg.SCREEN_WIDTH * 2
                if sy > cfg.SCREEN_HEIGHT:
                    sy -= cfg.SCREEN_HEIGHT * 2
                if 0 <= sx <= cfg.SCREEN_WIDTH and 0 <= sy <= cfg.SCREEN_HEIGHT:
                    pygame.draw.circle(screen, cfg.WHITE, (int(sx), int(sy)), int(star["r"]))

        # Draw asteroids as small diamond outlines (skip mined ones)
        for key, ast in self.generated_asteroids.items():
            if ast.aid in self.player.mined_asteroids:
                continue
            sx = cx + ast.x
            sy = cy + ast.y
            if -30 < sx < cfg.SCREEN_WIDTH + 30 and -30 < sy < cfg.SCREEN_HEIGHT + 30:
                r = int(ast.radius)
                pts = [(sx, sy - r), (sx + r, sy), (sx, sy + r), (sx - r, sy)]
                pygame.draw.polygon(screen, cfg.WHITE, pts, 1)

        # Draw all visible planets — known are filled with name, unknown are outlines only
        for key, planet in self.generated_planets.items():
            sx = cx + planet.x
            sy = cy + planet.y
            if -100 < sx < cfg.SCREEN_WIDTH + 100 and -100 < sy < cfg.SCREEN_HEIGHT + 100:
                if self.player.knows_planet(planet.pid):
                    pygame.draw.circle(screen, cfg.WHITE, (int(sx), int(sy)), int(planet.radius), 0)
                    name_surf = self.font_small.render(planet.name, True, cfg.WHITE)
                    screen.blit(name_surf, (sx - name_surf.get_width() // 2, sy + planet.radius + 4))
                else:
                    pygame.draw.circle(screen, cfg.WHITE, (int(sx), int(sy)), int(planet.radius), 1)

        # Draw exhaust trail
        for i, (tx, ty) in enumerate(self.player.trail):
            alpha = (i + 1) / len(self.player.trail) if self.player.trail else 0
            sx = cx + tx
            sy = cy + ty
            if 0 <= sx <= cfg.SCREEN_WIDTH and 0 <= sy <= cfg.SCREEN_HEIGHT:
                # Simulate fade with smaller dots for older trail
                size = max(1, int(alpha * 2))
                color = cfg.WHITE
                pygame.draw.circle(screen, color, (int(sx), int(sy)), size)

        # Draw player ship
        px = cfg.SCREEN_WIDTH // 2
        py = cfg.SCREEN_HEIGHT // 2
        
        if self.ship_img:
            # Rotate image counter-clockwise (since player angle is clockwise).
            # Subtract 90 degrees if the original image points UP, 
            # or just -self.player.angle if it points RIGHT. 
            # Most pixel art points UP, so doing: -self.player.angle - 90
            rotated_img = pygame.transform.rotate(self.ship_img, -self.player.angle - 90)
            rect = rotated_img.get_rect(center=(px, py))
            screen.blit(rotated_img, rect.topleft)
        else:
            # Fallback (triangle)
            rad = math.radians(self.player.angle)
            size = 14
            tip = (px + math.cos(rad) * size, py + math.sin(rad) * size)
            left = (px + math.cos(rad + 2.4) * size * 0.6,
                    py + math.sin(rad + 2.4) * size * 0.6)
            right = (px + math.cos(rad - 2.4) * size * 0.6,
                     py + math.sin(rad - 2.4) * size * 0.6)
            pygame.draw.polygon(screen, cfg.WHITE, [tip, left, right], 0)

        # Arrows for the 3 nearest known planets — current waypoint drawn larger/filled.
        # When a planet is on-screen we skip the arrow (the planet itself is the marker);
        # the waypoint also gets a crosshair overlay even when on-screen.
        margin = 50
        nearest = sorted(self.player.known_planets.values(),
                         key=lambda p: math.hypot(p.x - self.player.x, p.y - self.player.y))[:3]
        # Ensure the active waypoint planet always gets its arrow, even when far away.
        if self.player.waypoint:
            wx, wy = self.player.waypoint
            for planet in self.player.known_planets.values():
                if abs(planet.x - wx) < 1 and abs(planet.y - wy) < 1:
                    if planet not in nearest:
                        nearest.append(planet)
                    break
        for planet in nearest:
            sx = cx + planet.x
            sy = cy + planet.y
            is_wp = (self.player.waypoint and
                     abs(planet.x - self.player.waypoint[0]) < 1 and
                     abs(planet.y - self.player.waypoint[1]) < 1)
            on_screen = (margin < sx < cfg.SCREEN_WIDTH - margin and
                         margin < sy < cfg.SCREEN_HEIGHT - margin)
            dist = math.hypot(planet.x - self.player.x, planet.y - self.player.y)

            if on_screen:
                if is_wp:
                    pygame.draw.circle(screen, cfg.WHITE, (int(sx), int(sy)), 26, 2)
                    pygame.draw.line(screen, cfg.WHITE,
                                     (int(sx) - 16, int(sy)), (int(sx) + 16, int(sy)), 1)
                    pygame.draw.line(screen, cfg.WHITE,
                                     (int(sx), int(sy) - 16), (int(sx), int(sy) + 16), 1)
                continue

            # Off-screen: arrow on the edge box pointing toward the planet
            angle = math.atan2(planet.y - self.player.y, planet.x - self.player.x)
            cos_a = math.cos(angle)
            sin_a = math.sin(angle)
            half_w = cfg.SCREEN_WIDTH / 2 - margin
            half_h = cfg.SCREEN_HEIGHT / 2 - margin
            if cos_a != 0 and sin_a != 0:
                t = min(half_w / abs(cos_a), half_h / abs(sin_a))
            elif cos_a != 0:
                t = half_w / abs(cos_a)
            else:
                t = half_h / abs(sin_a)
            ax = cfg.SCREEN_WIDTH // 2 + cos_a * t
            ay = cfg.SCREEN_HEIGHT // 2 + sin_a * t

            arrow_size = 16 if is_wp else 10
            tip = (ax + cos_a * arrow_size * 0.4, ay + sin_a * arrow_size * 0.4)
            a1 = (ax - math.cos(angle - 2.4) * arrow_size,
                  ay - math.sin(angle - 2.4) * arrow_size)
            a2 = (ax - math.cos(angle + 2.4) * arrow_size,
                  ay - math.sin(angle + 2.4) * arrow_size)
            pygame.draw.polygon(screen, cfg.WHITE, [tip, a1, a2], 0 if is_wp else 1)

            lbl_text = f"{planet.name}  {int(dist)}px" if is_wp else planet.name
            name_surf = self.font_small.render(lbl_text, True, cfg.WHITE)
            lx = ax - cos_a * (arrow_size + 10) - name_surf.get_width() // 2
            ly = ay - sin_a * (arrow_size + 14) - name_surf.get_height() // 2
            lx = max(2, min(cfg.SCREEN_WIDTH - name_surf.get_width() - 2, lx))
            ly = max(2, min(cfg.SCREEN_HEIGHT - name_surf.get_height() - 2, ly))
            screen.blit(name_surf, (int(lx), int(ly)))

        # Top-center waypoint distance readout
        if self.player.waypoint:
            wx, wy = self.player.waypoint
            wp_dist = math.hypot(wx - self.player.x, wy - self.player.y)
            wp_text = self.font_small.render(f"WAYPOINT: {int(wp_dist)} px", True, cfg.WHITE)
            screen.blit(wp_text,
                        (cfg.SCREEN_WIDTH // 2 - wp_text.get_width() // 2, 70))

        # "[F] MINE" hint when an asteroid is in engage range
        nearest_ast = self._nearest_mineable_asteroid()
        if nearest_ast:
            hint = self.font_medium.render("[F] MINE ASTEROID", True, cfg.WHITE)
            screen.blit(hint,
                        (cfg.SCREEN_WIDTH // 2 - hint.get_width() // 2, 100))

        # Draw HUD
        self.hud.draw(screen, self.player, self.elapsed_time)

        # Draw radar (bottom-right) so the player can find asteroids/planets
        self._draw_radar(screen)

        # Draw map overlay — first ensure planets exist in the map's visible area
        if self.map_screen.visible:
            min_x, min_y, max_x, max_y = self.map_screen.visible_world_rect(self.player)
            self._generate_planets_in_rect(min_x, min_y, max_x, max_y)
        self.map_screen.draw(screen, self.player, self.generated_planets)

        # Draw message
        if self.message:
            self.message.draw(screen)

    def _draw_radar(self, screen):
        """Circular radar in the bottom-right corner. Shows nearby asteroids and planets
        relative to the player, including planet name & distance for the closest one."""
        color = cfg.WHITE
        radar_size = 150
        radar_radius = radar_size // 2
        cx_r = cfg.SCREEN_WIDTH - radar_radius - 10
        cy_r = cfg.SCREEN_HEIGHT - radar_radius - 40
        range_world = cfg.RADAR_RANGE * (2 if self.player.has_long_scanner else 1)

        # Black backdrop so radar is readable over background stars
        pygame.draw.rect(screen, cfg.BLACK,
                         (cx_r - radar_radius - 2, cy_r - radar_radius - 2,
                          radar_size + 4, radar_size + 4))
        # Outer + half-range rings, crosshair
        pygame.draw.circle(screen, color, (cx_r, cy_r), radar_radius, 1)
        pygame.draw.circle(screen, color, (cx_r, cy_r), radar_radius // 2, 1)
        pygame.draw.line(screen, color,
                         (cx_r - radar_radius, cy_r),
                         (cx_r + radar_radius, cy_r), 1)
        pygame.draw.line(screen, color,
                         (cx_r, cy_r - radar_radius),
                         (cx_r, cy_r + radar_radius), 1)

        # Player at center + facing direction
        rad = math.radians(self.player.angle)
        pygame.draw.line(screen, color,
                         (cx_r, cy_r),
                         (int(cx_r + math.cos(rad) * 10),
                          int(cy_r + math.sin(rad) * 10)), 2)
        pygame.draw.circle(screen, color, (cx_r, cy_r), 2, 0)

        # Asteroid blips (tiny diamonds)
        for ast in self.generated_asteroids.values():
            if ast.aid in self.player.mined_asteroids:
                continue
            dx = ast.x - self.player.x
            dy = ast.y - self.player.y
            d = math.hypot(dx, dy)
            if d > range_world or d < 1:
                continue
            rx = cx_r + dx / range_world * radar_radius
            ry = cy_r + dy / range_world * radar_radius
            pygame.draw.polygon(screen, color, [
                (rx, ry - 2), (rx + 2, ry), (rx, ry + 2), (rx - 2, ry)
            ], 1)

        # Planet blips — known are filled, unknown are outlined
        for planet in self.generated_planets.values():
            dx = planet.x - self.player.x
            dy = planet.y - self.player.y
            d = math.hypot(dx, dy)
            if d > range_world:
                continue
            rx = cx_r + dx / range_world * radar_radius
            ry = cy_r + dy / range_world * radar_radius
            known = self.player.knows_planet(planet.pid)
            pygame.draw.circle(screen, color, (int(rx), int(ry)), 4, 0 if known else 1)

        # Waypoint blip — bright cross if within range, edge marker if beyond
        if self.player.waypoint:
            wx, wy = self.player.waypoint
            dx = wx - self.player.x
            dy = wy - self.player.y
            d = math.hypot(dx, dy)
            if d <= range_world:
                rx = cx_r + dx / range_world * radar_radius
                ry = cy_r + dy / range_world * radar_radius
            else:
                # Project to radar edge
                ang = math.atan2(dy, dx)
                rx = cx_r + math.cos(ang) * (radar_radius - 4)
                ry = cy_r + math.sin(ang) * (radar_radius - 4)
            pygame.draw.line(screen, color,
                             (int(rx) - 5, int(ry)), (int(rx) + 5, int(ry)), 1)
            pygame.draw.line(screen, color,
                             (int(rx), int(ry) - 5), (int(rx), int(ry) + 5), 1)

        # Range label
        lbl = self.font_small.render(f"RADAR  {range_world // 1000}k px",
                                     True, color)
        screen.blit(lbl, (cx_r - lbl.get_width() // 2,
                          cy_r + radar_radius + 2))

    def get_target_planet(self):
        return self.target_planet
