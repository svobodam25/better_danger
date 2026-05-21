import math
import pygame
import settings as cfg


class MapScreen:
    """Full-screen map overlay showing known planets."""

    def __init__(self, font_small, font_medium, font_large):
        self.font_small = font_small
        self.font_medium = font_medium
        self.font_large = font_large
        self.visible = False
        self.zoom = 1.0
        self.pan_x = 0
        self.pan_y = 0

    def toggle(self):
        self.visible = not self.visible

    def handle_input(self, event):
        if not self.visible:
            return False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_m:
                self.visible = False
                return True
            elif event.key == pygame.K_EQUALS or event.key == pygame.K_PLUS:
                self.zoom = min(4.0, self.zoom * 1.2)
            elif event.key == pygame.K_MINUS:
                self.zoom = max(0.25, self.zoom / 1.2)
        return True

    def draw(self, screen, player, planets):
        """Draw the map overlay."""
        if not self.visible:
            return

        # Semi-transparent overlay (not possible in pure 1-bit, so use full black)
        screen.fill(cfg.BLACK)

        color = cfg.WHITE
        cx = cfg.SCREEN_WIDTH // 2
        cy = cfg.SCREEN_HEIGHT // 2

        # Draw grid lines
        grid_spacing = int(500 * self.zoom)
        if grid_spacing < 20:
            grid_spacing = 20
        offset_x = (self.pan_x % grid_spacing)
        offset_y = (self.pan_y % grid_spacing)
        for x in range(offset_x, cfg.SCREEN_WIDTH, grid_spacing):
            pygame.draw.line(screen, color, (x, 0), (x, cfg.SCREEN_HEIGHT), 1)
        for y in range(offset_y, cfg.SCREEN_HEIGHT, grid_spacing):
            pygame.draw.line(screen, color, (0, y), (cfg.SCREEN_WIDTH, y), 1)

        # Convert player position to screen
        px = cx + (player.x + self.pan_x) * self.zoom
        py = cy + (player.y + self.pan_y) * self.zoom

        # Draw known planets
        for pid, planet in player.known_planets.items():
            sx = cx + (planet.x + self.pan_x) * self.zoom
            sy = cy + (planet.y + self.pan_y) * self.zoom
            # Only draw if on screen
            if -50 < sx < cfg.SCREEN_WIDTH + 50 and -50 < sy < cfg.SCREEN_HEIGHT + 50:
                r = max(3, int(planet.radius * self.zoom))
                pygame.draw.circle(screen, color, (int(sx), int(sy)), r, 0)
                # Planet name
                name_surf = self.font_small.render(planet.name, True, color)
                screen.blit(name_surf, (sx - name_surf.get_width() // 2, sy + r + 4))
                # Planet type
                type_surf = self.font_small.render(f"({planet.planet_type})", True, color)
                screen.blit(type_surf, (sx - type_surf.get_width() // 2, sy + r + 18))

        # Draw player position
        # Player triangle
        rad = math.radians(player.angle)
        size = 10
        tip = (px + math.cos(rad) * size, py + math.sin(rad) * size)
        left = (px + math.cos(rad + 2.5) * size * 0.6,
                py + math.sin(rad + 2.5) * size * 0.6)
        right = (px + math.cos(rad - 2.5) * size * 0.6,
                 py + math.sin(rad - 2.5) * size * 0.6)
        pygame.draw.polygon(screen, color, [tip, left, right], 0)
        pygame.draw.circle(screen, color, (int(px), int(py)), 4, 1)

        # Player label
        label = self.font_small.render("YOU", True, color)
        screen.blit(label, (px - label.get_width() // 2, py - 20))

        # Legend
        legend_y = 10
        legend_x = 10
        title = self.font_medium.render("MAP (M to close, +/- zoom)", True, color)
        screen.blit(title, (legend_x, legend_y))
        legend_y += 25
        info_lines = [
            f"Zoom: {self.zoom:.1f}x",
            f"Known planets: {len(player.known_planets)}",
            f"Position: ({int(player.x)}, {int(player.y)})",
        ]
        for line in info_lines:
            surf = self.font_small.render(line, True, color)
            screen.blit(surf, (legend_x, legend_y))
            legend_y += 18
