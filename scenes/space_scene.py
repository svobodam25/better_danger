import math
import os
import random
import pygame
import settings as cfg
from entities.planet import Planet
from entities.player import Player
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
        self.generated_planets = {}  # planet_id -> Planet

        # Background stars (parallax layers)
        self.stars = self._generate_stars()

        # Start planet
        start_planet = self._get_or_generate_planet(0, 0)
        self.player.know_planet(start_planet)

        self.elapsed_time = 0.0
        self.next_scene = None
        self.target_planet = None

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

    def handle_input(self, event):
        """Handle keyboard/mouse events for space scene."""
        # Map screen takes priority
        if self.map_screen.visible:
            self.map_screen.handle_input(event)
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
            elif event.key == pygame.K_ESCAPE:
                return "pause"

        return None

    def update(self, dt, keys):
        """Update space scene logic."""
        if self.map_screen.visible:
            return None

        self.elapsed_time += dt

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

        # Generate nearby planets
        self._generate_nearby_planets()

        # Check for planet proximity (docking trigger)
        for key, planet in self.generated_planets.items():
            if check_planet_collision(self.player, planet):
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

        # Draw HUD
        self.hud.draw(screen, self.player, self.elapsed_time)

        # Draw map overlay
        self.map_screen.draw(screen, self.player, self.generated_planets)

        # Draw message
        if self.message:
            self.message.draw(screen)

    def get_target_planet(self):
        return self.target_planet
