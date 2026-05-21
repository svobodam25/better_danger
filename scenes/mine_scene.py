import math
import random
import pygame
import settings as cfg


class MineScene:
    """Asteroid drilling minigame.
    Hold SPACE to drill — progress rises but so does heat. Release to cool.
    Hit 100% progress before heat hits 100% to mine the asteroid.
    Overheat = damage + partial reward."""

    STATE_DRILLING = "drilling"
    STATE_SUCCESS = "success"
    STATE_OVERHEAT = "overheat"
    STATE_ABORT = "abort"

    def __init__(self, player, asteroid, font_small, font_medium, font_large, font_huge):
        self.player = player
        self.asteroid = asteroid
        self.font_small = font_small
        self.font_medium = font_medium
        self.font_large = font_large
        self.font_huge = font_huge

        self.progress = 0.0
        self.heat = 0.0
        self.drilling = False
        self.state = self.STATE_DRILLING
        self.shake = 0.0
        self.result_timer = 0.0
        self.reward_msg = ""

        # Procedural asteroid shape (deterministic by id)
        rng = random.Random(asteroid.aid)
        n = rng.randint(9, 14)
        self.shape_points = []
        for i in range(n):
            angle = 2 * math.pi * i / n
            r = 120 + rng.uniform(-30, 30)
            self.shape_points.append((angle, r))

        # Drill bit position (drifts during drilling)
        self.drill_angle = rng.uniform(0, 2 * math.pi)
        self.drill_dir = rng.choice([-1, 1])

        # Heat rate factor from upgrade
        self.heat_rate_mult = cfg.MINE_DRILL_HEAT_REDUCTION if player.has_mining_drill else 1.0

    def handle_input(self, event):
        if self.state != self.STATE_DRILLING:
            if event.type == pygame.KEYDOWN:
                return "leave"
            return None
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.state = self.STATE_ABORT
                self.result_timer = 0.0
                self.reward_msg = "Aborted — no reward"
                return None
        return None

    def update(self, dt, keys):
        if self.state != self.STATE_DRILLING:
            self.result_timer += dt
            if self.result_timer >= 2.5:
                return "leave"
            return None

        self.drilling = keys[pygame.K_SPACE]

        if self.drilling:
            self.progress += cfg.MINE_PROGRESS_RATE * dt
            self.heat += cfg.MINE_HEAT_RATE * self.heat_rate_mult * dt
            self.shake = min(4, self.shake + dt * 12)
            self.drill_angle += dt * 0.6 * self.drill_dir
        else:
            self.heat = max(0, self.heat - cfg.MINE_COOL_RATE * dt)
            self.shake = max(0, self.shake - dt * 6)

        if self.heat >= 100:
            self.state = self.STATE_OVERHEAT
            self.player.damage(cfg.MINE_OVERHEAT_DAMAGE)
            self.result_timer = 0.0
            self._finalize_reward()
            return None

        if self.progress >= 100:
            self.state = self.STATE_SUCCESS
            self.result_timer = 0.0
            self._finalize_reward()
            return None

        return None

    def _finalize_reward(self):
        """Grant the loot proportional to outcome."""
        ast = self.asteroid
        multiplier = 1.0 if self.state == self.STATE_SUCCESS else 0.4

        if ast.reward_kind == "credits":
            cr = max(1, int(ast.reward_credits * multiplier))
            self.player.credits += cr
            self.player.total_earned += cr
            self.reward_msg = f"+{cr} credits"
        else:
            cid = ast.reward_commodity
            qty = max(1, int(ast.reward_qty * multiplier))
            weight = cfg.COMMODITIES[cid]["weight"]
            free = self.player.cargo_free()
            max_qty = free // weight if weight > 0 else 0
            actual = min(qty, max_qty)
            if actual > 0:
                if cid in self.player.inventory:
                    self.player.inventory[cid]["qty"] += actual
                else:
                    self.player.inventory[cid] = {
                        "commodity": cid, "qty": actual, "buy_price": 0,
                    }
                name = cfg.COMMODITIES[cid]["name"]
                self.reward_msg = f"+{actual}x {name}"
            else:
                bonus = cfg.COMMODITIES[cid]["base_price"] * qty
                self.player.credits += bonus
                self.player.total_earned += bonus
                self.reward_msg = f"Cargo full — +{bonus} cr"

        self.player.mined_asteroids.add(ast.aid)

    def draw(self, screen):
        screen.fill(cfg.BLACK)
        color = cfg.WHITE
        cx = cfg.SCREEN_WIDTH // 2
        cy = cfg.SCREEN_HEIGHT // 2 - 30

        # Shake offset while drilling
        if self.shake > 0:
            ox = random.uniform(-self.shake, self.shake)
            oy = random.uniform(-self.shake, self.shake)
        else:
            ox = oy = 0

        # Asteroid silhouette
        pts = []
        for angle, r in self.shape_points:
            pts.append((cx + math.cos(angle) * r + ox,
                        cy + math.sin(angle) * r + oy))
        pygame.draw.polygon(screen, color, pts, 2)
        # Inner cracks for visual texture
        for angle, r in self.shape_points[::3]:
            ix1 = cx + math.cos(angle) * (r * 0.3) + ox
            iy1 = cy + math.sin(angle) * (r * 0.3) + oy
            ix2 = cx + math.cos(angle) * (r * 0.7) + ox
            iy2 = cy + math.sin(angle) * (r * 0.7) + oy
            pygame.draw.line(screen, color, (ix1, iy1), (ix2, iy2), 1)

        # Drill beam from top of screen to asteroid surface point
        if self.drilling and self.state == self.STATE_DRILLING:
            target_r = 120
            tx = cx + math.cos(self.drill_angle) * target_r + ox
            ty = cy + math.sin(self.drill_angle) * target_r + oy
            beam_start = (cfg.SCREEN_WIDTH // 2, 80)
            pygame.draw.line(screen, color, beam_start, (tx, ty), 3)
            # Sparks
            for _ in range(6):
                spx = tx + random.uniform(-18, 18)
                spy = ty + random.uniform(-18, 18)
                pygame.draw.circle(screen, color, (int(spx), int(spy)), 1)

        # Title
        title = self.font_large.render("MINING", True, color)
        screen.blit(title, (cfg.SCREEN_WIDTH // 2 - title.get_width() // 2, 20))

        # Progress bar (bottom-left)
        bar_w = 360
        bar_h = 26
        bar_x = 50
        bar_y = cfg.SCREEN_HEIGHT - 110
        pygame.draw.rect(screen, color, (bar_x, bar_y, bar_w, bar_h), 2)
        fill_w = int(bar_w * min(1.0, self.progress / 100))
        pygame.draw.rect(screen, color, (bar_x, bar_y, fill_w, bar_h))
        prog_lbl = self.font_small.render(f"PROGRESS: {int(self.progress)}%", True, color)
        screen.blit(prog_lbl, (bar_x, bar_y - 22))

        # Heat bar (bottom-right) with danger marker at 90%
        bar_x2 = cfg.SCREEN_WIDTH - bar_w - 50
        pygame.draw.rect(screen, color, (bar_x2, bar_y, bar_w, bar_h), 2)
        fill_w2 = int(bar_w * min(1.0, self.heat / 100))
        # Pulse when in danger zone
        if self.heat > 75 and self.state == self.STATE_DRILLING:
            if int(self.result_timer * 12 + self.shake * 4) % 2 == 0:
                # Cross-hatch effect on heat bar
                for hx in range(bar_x2 + 2, bar_x2 + fill_w2, 6):
                    pygame.draw.line(screen, cfg.BLACK,
                                     (hx, bar_y + 2), (hx + 3, bar_y + bar_h - 2), 1)
        pygame.draw.rect(screen, color, (bar_x2, bar_y, fill_w2, bar_h))
        # 90% danger tick
        danger_x = bar_x2 + int(bar_w * 0.9)
        pygame.draw.line(screen, color,
                         (danger_x, bar_y - 6), (danger_x, bar_y + bar_h + 6), 2)
        heat_lbl = self.font_small.render(f"HEAT: {int(self.heat)}%", True, color)
        screen.blit(heat_lbl, (bar_x2, bar_y - 22))

        # Instructions / outcome
        if self.state == self.STATE_DRILLING:
            help1 = self.font_medium.render(
                "Hold SPACE = drill   Release = cool   ESC = abort",
                True, color)
            screen.blit(help1, (cfg.SCREEN_WIDTH // 2 - help1.get_width() // 2,
                                cfg.SCREEN_HEIGHT - 40))
        elif self.state == self.STATE_SUCCESS:
            big = self.font_huge.render("MINED!", True, color)
            screen.blit(big, (cfg.SCREEN_WIDTH // 2 - big.get_width() // 2,
                              cfg.SCREEN_HEIGHT - 200))
            sub = self.font_medium.render(self.reward_msg, True, color)
            screen.blit(sub, (cfg.SCREEN_WIDTH // 2 - sub.get_width() // 2,
                              cfg.SCREEN_HEIGHT - 145))
        elif self.state == self.STATE_OVERHEAT:
            big = self.font_huge.render("OVERHEAT!", True, color)
            screen.blit(big, (cfg.SCREEN_WIDTH // 2 - big.get_width() // 2,
                              cfg.SCREEN_HEIGHT - 200))
            sub = self.font_medium.render(
                f"-{int(cfg.MINE_OVERHEAT_DAMAGE)} HP   {self.reward_msg}",
                True, color)
            screen.blit(sub, (cfg.SCREEN_WIDTH // 2 - sub.get_width() // 2,
                              cfg.SCREEN_HEIGHT - 145))
        elif self.state == self.STATE_ABORT:
            big = self.font_huge.render("ABORTED", True, color)
            screen.blit(big, (cfg.SCREEN_WIDTH // 2 - big.get_width() // 2,
                              cfg.SCREEN_HEIGHT - 200))
