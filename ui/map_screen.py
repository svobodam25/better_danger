import math
import pygame
import settings as cfg


class MapScreen:
    """Full-screen map overlay. Player-centered, supports pan/zoom and waypoint selection."""

    def __init__(self, font_small, font_medium, font_large):
        self.font_small = font_small
        self.font_medium = font_medium
        self.font_large = font_large
        self.visible = False
        # Zoom: ratio of screen px to world px (e.g. 0.005 = 1 screen px ≈ 200 world px)
        self.zoom = 0.005
        # Pan: extra world-space offset on top of player-centered view
        self.pan_x = 0.0
        self.pan_y = 0.0
        self.selected_idx = 0  # index into sorted-by-distance known planets
        self.unit_mode = "auto"  # cycled by U: "auto" | "px" | "km"

    def _fmt_distance(self, v):
        """Format a world-space distance/position value according to unit_mode.
        Game scale: 1 px = 10 km."""
        if self.unit_mode == "px":
            return f"{int(v)} px"
        if self.unit_mode == "km":
            return f"{v / cfg.PX_PER_KM:,.0f} km"
        if self.unit_mode == "ls":
            return f"{v / cfg.PX_PER_LS:.3f} ls"
        if self.unit_mode == "au":
            return f"{v / cfg.PX_PER_AU:.5f} AU"
        if self.unit_mode == "ly":
            return f"{v / cfg.PX_PER_LY:.8f} ly"
        # auto — pick the most readable unit for the magnitude
        av = abs(v)
        if av < cfg.PX_PER_LS * 0.01:        # < 0.01 ls (~3000 km)
            return f"{v / cfg.PX_PER_KM:,.0f} km"
        if av < cfg.PX_PER_AU * 0.01:        # < 0.01 AU (~5 ls)
            return f"{v / cfg.PX_PER_LS:.2f} ls"
        if av < cfg.PX_PER_LY * 0.01:        # < 0.01 ly
            return f"{v / cfg.PX_PER_AU:.3f} AU"
        return f"{v / cfg.PX_PER_LY:.4f} ly"

    def visible_world_rect(self, player):
        """Returns (min_x, min_y, max_x, max_y) in world coords."""
        half_w = (cfg.SCREEN_WIDTH / 2) / self.zoom
        half_h = (cfg.SCREEN_HEIGHT / 2) / self.zoom
        cx = player.x + self.pan_x
        cy = player.y + self.pan_y
        return (cx - half_w, cy - half_h, cx + half_w, cy + half_h)

    def toggle(self):
        self.visible = not self.visible
        if self.visible:
            self.pan_x = 0.0
            self.pan_y = 0.0

    def _sorted_planets(self, player):
        planets = list(player.known_planets.values())
        planets.sort(key=lambda p: math.hypot(p.x - player.x, p.y - player.y))
        return planets

    def handle_input(self, event, player):
        if not self.visible:
            return False
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_m, pygame.K_ESCAPE):
                self.visible = False
                return True
            elif event.key in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
                self.zoom = min(1.0, self.zoom * 1.5)
            elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                self.zoom = max(0.00005, self.zoom / 1.5)
            elif event.key in (pygame.K_w, pygame.K_UP):
                self.pan_y -= 100 / self.zoom
            elif event.key in (pygame.K_s, pygame.K_DOWN):
                self.pan_y += 100 / self.zoom
            elif event.key in (pygame.K_a, pygame.K_LEFT):
                self.pan_x -= 100 / self.zoom
            elif event.key in (pygame.K_d, pygame.K_RIGHT):
                self.pan_x += 100 / self.zoom
            elif event.key == pygame.K_HOME:
                self.pan_x = 0.0
                self.pan_y = 0.0
            elif event.key == pygame.K_u:
                modes = ["auto", "km", "ls", "au", "ly", "px"]
                idx = modes.index(self.unit_mode) if self.unit_mode in modes else 0
                self.unit_mode = modes[(idx + 1) % len(modes)]
            elif event.key == pygame.K_TAB:
                planets = self._sorted_planets(player)
                if planets:
                    self.selected_idx = (self.selected_idx + 1) % len(planets)
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                planets = self._sorted_planets(player)
                if planets and self.selected_idx < len(planets):
                    target = planets[self.selected_idx]
                    player.waypoint = (target.x, target.y)
            elif event.key == pygame.K_BACKSPACE:
                player.waypoint = None
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            wx, wy = self._screen_to_world(mx, my, player)
            planets = self._sorted_planets(player)
            if planets:
                best_idx = 0
                best_d = float("inf")
                for i, p in enumerate(planets):
                    d = math.hypot(p.x - wx, p.y - wy)
                    if d < best_d:
                        best_d = d
                        best_idx = i
                self.selected_idx = best_idx
                # Double-click sets waypoint; single-click only selects.
                # Here: single-click selects; user presses Enter to confirm.
        return True

    def _world_to_screen(self, wx, wy, player):
        cx = cfg.SCREEN_WIDTH // 2
        cy = cfg.SCREEN_HEIGHT // 2
        sx = cx + (wx - player.x - self.pan_x) * self.zoom
        sy = cy + (wy - player.y - self.pan_y) * self.zoom
        return sx, sy

    def _screen_to_world(self, sx, sy, player):
        cx = cfg.SCREEN_WIDTH // 2
        cy = cfg.SCREEN_HEIGHT // 2
        wx = (sx - cx) / self.zoom + player.x + self.pan_x
        wy = (sy - cy) / self.zoom + player.y + self.pan_y
        return wx, wy

    def draw(self, screen, player, planets):
        if not self.visible:
            return
        screen.fill(cfg.BLACK)
        color = cfg.WHITE

        # --- Grid: ~10 lines across, snapped to nice power-of-ten world spacing ---
        target_world_span = cfg.SCREEN_WIDTH / self.zoom
        approx_step = target_world_span / 10
        magnitude = 10 ** math.floor(math.log10(max(1, approx_step)))
        for mult in (1, 2, 5, 10):
            if mult * magnitude >= approx_step:
                grid_world_spacing = mult * magnitude
                break
        else:
            grid_world_spacing = magnitude

        # Find visible world rect
        wx_left, wy_top = self._screen_to_world(0, 0, player)
        wx_right, wy_bot = self._screen_to_world(cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT, player)
        first_gx = math.floor(wx_left / grid_world_spacing) * grid_world_spacing
        first_gy = math.floor(wy_top / grid_world_spacing) * grid_world_spacing
        gx = first_gx
        while gx <= wx_right:
            sx, _ = self._world_to_screen(gx, 0, player)
            pygame.draw.line(screen, color, (int(sx), 0), (int(sx), cfg.SCREEN_HEIGHT), 1)
            gx += grid_world_spacing
        gy = first_gy
        while gy <= wy_bot:
            _, sy = self._world_to_screen(0, gy, player)
            pygame.draw.line(screen, color, (0, int(sy)), (cfg.SCREEN_WIDTH, int(sy)), 1)
            gy += grid_world_spacing

        # --- Only KNOWN planets shown on the map — buying star charts is how you discover ---
        sorted_known = self._sorted_planets(player)
        selected_pid = (sorted_known[self.selected_idx].pid
                        if sorted_known and self.selected_idx < len(sorted_known)
                        else None)
        for planet in sorted_known:
            sx, sy = self._world_to_screen(planet.x, planet.y, player)
            if not (-50 < sx < cfg.SCREEN_WIDTH + 50 and -50 < sy < cfg.SCREEN_HEIGHT + 50):
                continue
            r = max(3, int(planet.radius * self.zoom))
            pygame.draw.circle(screen, color, (int(sx), int(sy)), r, 0)
            if planet.pid == selected_pid:
                pygame.draw.circle(screen, color, (int(sx), int(sy)), r + 8, 2)
            is_wp = (player.waypoint and
                     abs(planet.x - player.waypoint[0]) < 1 and
                     abs(planet.y - player.waypoint[1]) < 1)
            if is_wp:
                pygame.draw.circle(screen, color, (int(sx), int(sy)), r + 14, 1)
                wp_lbl = self.font_small.render("[WAYPOINT]", True, color)
                screen.blit(wp_lbl, (sx - wp_lbl.get_width() // 2, sy + r + 20))
            name_surf = self.font_small.render(planet.name, True, color)
            screen.blit(name_surf, (sx - name_surf.get_width() // 2, sy + r + 4))

        # --- Player marker ---
        px, py = self._world_to_screen(player.x, player.y, player)
        rad = math.radians(player.angle)
        size = 10
        tip = (px + math.cos(rad) * size, py + math.sin(rad) * size)
        left = (px + math.cos(rad + 2.5) * size * 0.6, py + math.sin(rad + 2.5) * size * 0.6)
        right = (px + math.cos(rad - 2.5) * size * 0.6, py + math.sin(rad - 2.5) * size * 0.6)
        pygame.draw.polygon(screen, color, [tip, left, right], 0)
        you_lbl = self.font_small.render("YOU", True, color)
        screen.blit(you_lbl, (px - you_lbl.get_width() // 2, py - 22))

        # --- Selected planet info ---
        if sorted_known and self.selected_idx < len(sorted_known):
            sel = sorted_known[self.selected_idx]
            dist = math.hypot(sel.x - player.x, sel.y - player.y)
            info_lines = [
                f"SELECTED: {sel.name} ({sel.planet_type})",
                f"Distance: {self._fmt_distance(dist)}",
                f"Position: ({self._fmt_distance(sel.x)}, {self._fmt_distance(sel.y)})",
                "ENTER = set waypoint",
            ]
            box_w = 320
            box_h = len(info_lines) * 18 + 8
            bx = cfg.SCREEN_WIDTH - box_w - 10
            by = 10
            pygame.draw.rect(screen, cfg.BLACK, (bx, by, box_w, box_h))
            pygame.draw.rect(screen, color, (bx, by, box_w, box_h), 1)
            for j, line in enumerate(info_lines):
                surf = self.font_small.render(line, True, color)
                screen.blit(surf, (bx + 6, by + 4 + j * 18))

        # --- Legend / controls (top-left) ---
        legend = [
            "MAP — M/Esc:close  +/-:zoom  WASD:pan  Home:recenter  U:units",
            "TAB:cycle planets  ENTER:set waypoint  BACKSPACE:clear  LMB:select",
            f"Zoom: {self.zoom:.5f}   units: {self.unit_mode.upper()}",
            f"Known planets: {len(sorted_known)}   (buy star charts at stations to reveal more)",
            f"Position: ({self._fmt_distance(player.x)}, {self._fmt_distance(player.y)})",
        ]
        if player.waypoint:
            wp_dist = math.hypot(player.waypoint[0] - player.x, player.waypoint[1] - player.y)
            legend.append(
                f"WAYPOINT: ({self._fmt_distance(player.waypoint[0])}, "
                f"{self._fmt_distance(player.waypoint[1])}) — {self._fmt_distance(wp_dist)}")
        for i, line in enumerate(legend):
            surf = self.font_small.render(line, True, color)
            screen.blit(surf, (10, 10 + i * 18))

        # --- Scale bar bottom-left ---
        bar_world = grid_world_spacing
        bar_px = bar_world * self.zoom
        by = cfg.SCREEN_HEIGHT - 30
        bx = 20
        pygame.draw.line(screen, color, (bx, by), (bx + bar_px, by), 2)
        pygame.draw.line(screen, color, (bx, by - 5), (bx, by + 5), 2)
        pygame.draw.line(screen, color, (bx + bar_px, by - 5), (bx + bar_px, by + 5), 2)
        sb_lbl = self.font_small.render(self._fmt_distance(bar_world), True, color)
        screen.blit(sb_lbl, (bx, by + 8))
