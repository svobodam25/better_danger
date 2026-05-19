import math
import random
import pygame
import settings as cfg
from entities.ai_ship import AIShip
from ui.menu import MessageBox


class DockScene:
    """Scene 2: Side-view docking — Flappy Bird style gate + many parking slots.
    Controls: SPACE = thrust up, A/D = horizontal, gravity pulls down.
    """

    def __init__(self, player, font_small, font_medium, font_large):
        self.player = player
        self.font_small = font_small
        self.font_medium = font_medium
        self.font_large = font_large
        self.reset()

    def reset(self):
        """Initialize/reset the docking scene."""
        w = cfg.SCREEN_WIDTH
        h = cfg.SCREEN_HEIGHT

        # Hangar dimensions
        self.floor_y = h - 30
        self.ceiling_y = 30
        self.hangar_left = w * 0.30   # entrance gate position
        self.hangar_right = w - 20

        # Player ship starts outside (left of gate) — BIGGER ship
        self.ship_x = 60.0
        self.ship_y = float(h // 2)
        self.ship_vx = 0.0
        self.ship_vy = 0.0
        self.ship_w = 50
        self.ship_h = 20
        self.angle = 0.0

        # Gravity & thrust — FASTER
        self.gravity = 350.0          # px/s² downward
        self.thrust_power = 420.0     # px/s² upward
        self.horizontal_speed = 280.0 # px/s horizontal

        # Gate (STATIC — does not move)
        self.gate_x = self.hangar_left
        self.gate_gap = 200           # height of the opening (wider)
        self.gate_center = float(h // 2)  # fixed at center

        # Many parking slots inside hangar — BIGGER slots
        self.slots = []
        slot_w = 90
        slot_h = 45
        slot_gap = 20
        slots_per_row = 5
        start_x = int(self.hangar_left + 100)
        start_y = int(self.ceiling_y + 60)
        total_slots = slots_per_row * 3  # 3 rows of 5 = 15 slots

        for i in range(total_slots):
            row = i // slots_per_row
            col = i % slots_per_row
            sx = start_x + col * (slot_w + slot_gap)
            sy = start_y + row * (slot_h + 30)
            # Ensure all rows fit inside hangar
            sy = min(sy, self.floor_y - slot_h - 10)
            self.slots.append({
                "x": sx, "y": sy, "w": slot_w, "h": slot_h,
                "occupied": False, "target": False,
            })

        # Pick random target slot
        self.target_slot_idx = random.randint(0, total_slots - 1)
        self.slots[self.target_slot_idx]["target"] = True

        # Occupy ~40% of slots with AI ships
        for i in range(total_slots):
            if i != self.target_slot_idx and random.random() < 0.4:
                self.slots[i]["occupied"] = True

        # State
        self.passed_gate = False
        self.gate_collision_cooldown = 0.0
        self.wrong_slot_timer = 0.0
        self.message = None
        self.flash_timer = 0.0
        self.collision_cooldown = 0.0

        # Traffic ships (departing / arriving through gate)
        self.traffic_ships = []       # list of {"x","y","vx","vy","direction","w","h"}
        self.traffic_spawn_timer = 2.0  # seconds between spawns
        self.traffic_spawn_cooldown = 1.5

    def handle_input(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return "abort"
        return None

    def _get_ship_rect(self):
        """Get ship bounding rectangle."""
        return pygame.Rect(
            self.ship_x - self.ship_w // 2,
            self.ship_y - self.ship_h // 2,
            self.ship_w, self.ship_h
        )

    def _get_gate_rects(self):
        """Get top and bottom gate barrier rects."""
        half_gap = self.gate_gap // 2
        top_rect = pygame.Rect(
            self.gate_x - 3, 0,
            6, int(self.gate_center - half_gap)
        )
        bot_rect = pygame.Rect(
            self.gate_x - 3, int(self.gate_center + half_gap),
            6, cfg.SCREEN_HEIGHT
        )
        return top_rect, bot_rect

    def _check_gate_collision(self):
        """Check if ship collides with the gate barriers."""
        if self.passed_gate:
            return False
        if self.gate_collision_cooldown > 0:
            return False
        ship_rect = self._get_ship_rect()
        top_rect, bot_rect = self._get_gate_rects()
        return ship_rect.colliderect(top_rect) or ship_rect.colliderect(bot_rect)

    def _check_passed_gate(self):
        """Check if ship has successfully passed through the gate."""
        if self.passed_gate:
            return True
        # Ship center must be to the right of the gate
        # and the ship's vertical position within the gap
        half_gap = self.gate_gap // 2
        ship_rect = self._get_ship_rect()
        if ship_rect.left > self.gate_x + 15:
            # Check if within gap vertically
            if self.gate_center - half_gap < self.ship_y < self.gate_center + half_gap:
                return True
        return False

    def _check_wall_collision(self):
        """Check collision with ceiling and floor."""
        return (self.ship_y - self.ship_h // 2 <= self.ceiling_y or
                self.ship_y + self.ship_h // 2 >= self.floor_y)

    def _check_slot_collision(self, slot):
        """Check collision between ship and a parked AI ship in slot."""
        if not slot["occupied"]:
            return False
        ship_rect = self._get_ship_rect()
        slot_rect = pygame.Rect(slot["x"], slot["y"], slot["w"], slot["h"])
        return ship_rect.colliderect(slot_rect)

    def _check_parked_in_slot(self, slot_idx):
        """Check if ship is correctly positioned in the target slot."""
        slot = self.slots[slot_idx]
        center_x = slot["x"] + slot["w"] / 2
        center_y = slot["y"] + slot["h"] / 2
        dx = abs(self.ship_x - center_x)
        dy = abs(self.ship_y - center_y)
        return (dx < cfg.DOCK_TOLERANCE_POS and
                dy < cfg.DOCK_TOLERANCE_POS)

    def _spawn_traffic_ship(self):
        """Spawn a ship departing from inside the hangar or arriving from outside."""
        half_gap = self.gate_gap // 2
        gate_y = self.gate_center

        # 60% departing (coming from right, going left through gate)
        # 40% arriving (coming from left, going right through gate)
        if random.random() < 0.6:
            # DEPARTING: spawns inside hangar, flies left through gate
            spawn_x = random.uniform(self.hangar_left + 80, self.hangar_right - 50)
            spawn_y = gate_y + random.uniform(-half_gap * 0.8, half_gap * 0.8)
            vx = -random.uniform(60, 120)
            vy = random.uniform(-20, 20)
            direction = -1
        else:
            # ARRIVING: spawns outside left, flies right through gate into hangar
            spawn_x = random.uniform(10, self.hangar_left - 60)
            spawn_y = gate_y + random.uniform(-half_gap * 0.8, half_gap * 0.8)
            vx = random.uniform(60, 120)
            vy = random.uniform(-20, 20)
            direction = 1

        self.traffic_ships.append({
            "x": spawn_x,
            "y": spawn_y,
            "vx": vx,
            "vy": vy,
            "w": random.randint(40, 56),
            "h": random.randint(14, 22),
            "direction": direction,
        })

    def _update_traffic(self, dt):
        """Update traffic ships: move, spawn new ones, remove off-screen, check collisions."""
        # Spawn cooldown
        self.traffic_spawn_cooldown -= dt
        if self.traffic_spawn_cooldown <= 0:
            self._spawn_traffic_ship()
            self.traffic_spawn_cooldown = self.traffic_spawn_timer + random.uniform(-0.8, 1.5)

        ship_rect = self._get_ship_rect()

        # Update and prune traffic ships
        new_traffic = []
        for tship in self.traffic_ships:
            tship["x"] += tship["vx"] * dt
            tship["y"] += tship["vy"] * dt

            # Check collision with player
            if self.collision_cooldown <= 0:
                t_rect = pygame.Rect(
                    tship["x"] - tship["w"] // 2,
                    tship["y"] - tship["h"] // 2,
                    tship["w"], tship["h"]
                )
                if ship_rect.colliderect(t_rect):
                    self.player.damage(cfg.SHIP_COLLISION_DAMAGE)
                    self.player.credits = max(0, self.player.credits - cfg.WRONG_SLOT_PENALTY)
                    self.collision_cooldown = 0.8
                    self.message = MessageBox(
                        f"TRAFFIC CRASH! -{int(cfg.SHIP_COLLISION_DAMAGE)} HP",
                        self.font_medium, -80)
                    # Push player away
                    self.ship_vx = -tship["vx"] * 0.5
                    self.ship_vy = -tship["vy"] * 0.5
                    continue  # destroy the traffic ship

            # Remove if far off screen
            margin = 80
            if (-margin < tship["x"] < cfg.SCREEN_WIDTH + margin and
                    -margin < tship["y"] < cfg.SCREEN_HEIGHT + margin):
                new_traffic.append(tship)

        self.traffic_ships = new_traffic

    def _bounce_off_wall(self):
        """Bounce the ship away from walls."""
        if self.collision_cooldown > 0:
            return
        self.player.damage(cfg.WALL_DAMAGE)
        self.ship_vy = abs(self.ship_vy) * 0.3 if self.ship_y < cfg.SCREEN_HEIGHT // 2 else -abs(self.ship_vy) * 0.3
        self.ship_y = max(self.ceiling_y + self.ship_h + 5,
                          min(self.floor_y - self.ship_h - 5, self.ship_y))
        self.collision_cooldown = 0.8
        self.message = MessageBox(f"WALL! -{int(cfg.WALL_DAMAGE)} HP", self.font_medium, -80)

    def update(self, dt, keys):
        """Update docking scene."""
        self.flash_timer += dt

        if self.collision_cooldown > 0:
            self.collision_cooldown -= dt
        if self.gate_collision_cooldown > 0:
            self.gate_collision_cooldown -= dt

        # Gate is STATIC — no movement

        # === PLAYER CONTROLS ===
        # Gravity always pulls down
        self.ship_vy += self.gravity * dt

        # SPACE = thrust upward
        if keys[pygame.K_SPACE]:
            self.ship_vy -= self.thrust_power * dt

        # A/D = horizontal movement (only right side is useful generally)
        if keys[pygame.K_a]:
            self.ship_vx = -self.horizontal_speed
        elif keys[pygame.K_d]:
            self.ship_vx = self.horizontal_speed
        else:
            self.ship_vx = 0.0

        # Apply velocity
        self.ship_x += self.ship_vx * dt
        self.ship_y += self.ship_vy * dt

        # Clamp to screen bounds
        self.ship_x = max(self.ship_w // 2, min(cfg.SCREEN_WIDTH - self.ship_w // 2, self.ship_x))

        # Check gate collision BEFORE passing
        if not self.passed_gate:
            if self._check_gate_collision():
                self.player.damage(cfg.WALL_DAMAGE * 2)
                self.gate_collision_cooldown = 1.0
                # Bounce ship back left
                self.ship_x = self.gate_x - self.ship_w - 10
                self.ship_vx = 0
                self.ship_vy = -100
                self.message = MessageBox(f"GATE CRASH! -{int(cfg.WALL_DAMAGE * 2)} HP", self.font_medium, -80)

            # Check if passed through gate successfully
            if self._check_passed_gate():
                self.passed_gate = True
                self.message = MessageBox("ENTERED HANGAR!", self.font_medium, -80)

        # === TRAFFIC SHIPS (departing & arriving through gate) ===
        self._update_traffic(dt)

        # Wall collision (ceiling/floor)
        if self._check_wall_collision():
            self._bounce_off_wall()

        # Collision with parked AI ships in occupied slots
        for i, slot in enumerate(self.slots):
            if slot["occupied"] and self._check_slot_collision(slot):
                if self.collision_cooldown <= 0:
                    self.player.damage(cfg.SHIP_COLLISION_DAMAGE)
                    self.player.credits = max(0, self.player.credits - cfg.WRONG_SLOT_PENALTY // 2)
                    self.collision_cooldown = 0.8
                    self.message = MessageBox(
                        f"BUMP! -{int(cfg.SHIP_COLLISION_DAMAGE)} HP",
                        self.font_medium, -80)

        # Check parking — only after passing gate
        if self.passed_gate:
            # Check if parked in target slot
            if self._check_parked_in_slot(self.target_slot_idx):
                self.ship_vx = 0
                self.ship_vy = 0
                return "success"

            # Check if parked in wrong slot
            for i in range(len(self.slots)):
                if i != self.target_slot_idx and self._check_parked_in_slot(i):
                    self.wrong_slot_timer += dt
                    if self.wrong_slot_timer > 5.0:
                        self.player.damage(999)
                        return "dead"
                    if self.wrong_slot_timer > 3.0 and not hasattr(self, '_warned'):
                        self.message = MessageBox("WRONG SLOT! MOVE!", self.font_large, -60)
                        self._warned = True
                    break
            else:
                self.wrong_slot_timer = max(0, self.wrong_slot_timer - dt * 2)
                if hasattr(self, '_warned'):
                    del self._warned

        # Check if dead
        if self.player.is_dead():
            return "dead"

        # Update message
        if self.message:
            if self.message.update(dt):
                self.message = None

        return None

    def draw(self, screen):
        """Render the docking scene."""
        screen.fill(cfg.BLACK)
        color = cfg.WHITE
        w = cfg.SCREEN_WIDTH

        # === HANGAR INTERIOR ===
        # Ceiling & floor lines inside hangar
        pygame.draw.line(screen, color, (self.hangar_left, self.ceiling_y),
                         (self.hangar_right, self.ceiling_y), 2)
        pygame.draw.line(screen, color, (self.hangar_left, self.floor_y),
                         (self.hangar_right, self.floor_y), 2)

        # Hatch pattern on ceiling/floor inside hangar
        for x in range(int(self.hangar_left), int(self.hangar_right), 30):
            pygame.draw.line(screen, color, (x, self.ceiling_y), (x + 15, self.ceiling_y + 7), 1)
            pygame.draw.line(screen, color, (x, self.floor_y), (x + 15, self.floor_y - 7), 1)

        # Hangar left wall
        pygame.draw.line(screen, color, (self.hangar_left, self.ceiling_y),
                         (self.hangar_left, self.floor_y), 2)

        # === OUTSIDE AREA (left of gate) ===
        # Ceiling & floor outside
        pygame.draw.line(screen, color, (0, self.ceiling_y),
                         (self.hangar_left, self.ceiling_y), 1)
        pygame.draw.line(screen, color, (0, self.floor_y),
                         (self.hangar_left, self.floor_y), 1)

        # === GATE (Flappy Bird style barriers) ===
        gate_color = (200, 200, 200)  # slightly dimmer white for gate
        top_rect, bot_rect = self._get_gate_rects()
        # Gate bars with hatch pattern
        pygame.draw.rect(screen, color, top_rect)
        pygame.draw.rect(screen, color, bot_rect)
        # Gate frame
        pygame.draw.line(screen, color, (self.gate_x, self.ceiling_y), (self.gate_x, self.floor_y), 1)

        # Gate label
        label = self.font_small.render("GATE", True, color)
        screen.blit(label, (self.gate_x - label.get_width() // 2, self.ceiling_y - 18))

        # Gate gap indicator arrows
        half_gap = self.gate_gap // 2
        arrow_y_top = int(self.gate_center - half_gap)
        arrow_y_bot = int(self.gate_center + half_gap)
        pygame.draw.polygon(screen, color, [
            (self.gate_x - 10, arrow_y_top),
            (self.gate_x + 10, arrow_y_top),
            (self.gate_x, arrow_y_top + 8)
        ], 0)
        pygame.draw.polygon(screen, color, [
            (self.gate_x - 10, arrow_y_bot),
            (self.gate_x + 10, arrow_y_bot),
            (self.gate_x, arrow_y_bot - 8)
        ], 0)

        # === TRAFFIC SHIPS (departing / arriving) ===
        for tship in self.traffic_ships:
            tw, th = tship["w"], tship["h"]
            tx, ty = tship["x"], tship["y"]
            # Outline rectangle
            t_rect = pygame.Rect(tx - tw // 2, ty - th // 2, tw, th)
            pygame.draw.rect(screen, color, t_rect, 1)
            # Triangle nose in direction of travel
            if tship["direction"] > 0:
                nose_tip = (t_rect.x + t_rect.w + 6, t_rect.y + t_rect.h // 2)
                nose_base_l = (t_rect.x + t_rect.w, t_rect.y + 2)
                nose_base_r = (t_rect.x + t_rect.w, t_rect.y + t_rect.h - 2)
            else:
                nose_tip = (t_rect.x - 6, t_rect.y + t_rect.h // 2)
                nose_base_l = (t_rect.x, t_rect.y + 2)
                nose_base_r = (t_rect.x, t_rect.y + t_rect.h - 2)
            pygame.draw.polygon(screen, color, [nose_tip, nose_base_l, nose_base_r], 0)

        # === PARKING SLOTS ===
        for i, slot in enumerate(self.slots):
            rect = pygame.Rect(slot["x"], slot["y"], slot["w"], slot["h"])
            if slot["target"]:
                # Blinking target slot
                alpha = (math.sin(self.flash_timer * 5) + 1) / 2
                if alpha > 0.4:
                    pygame.draw.rect(screen, color, rect, 2)
                    # Arrow pointing to slot
                    arrow_cx = slot["x"] + slot["w"] // 2
                    pygame.draw.polygon(screen, color, [
                        (arrow_cx, slot["y"] - 10),
                        (arrow_cx - 6, slot["y"] - 3),
                        (arrow_cx + 6, slot["y"] - 3),
                    ], 0)
                else:
                    pygame.draw.rect(screen, color, rect, 1)
                num_surf = self.font_small.render(f"PARK {i + 1}", True, color)
            else:
                pygame.draw.rect(screen, color, rect, 1)
                num_surf = self.font_small.render(f"{i + 1}", True, color)

            screen.blit(num_surf, (slot["x"] + slot["w"] // 2 - num_surf.get_width() // 2,
                                   slot["y"] - 16))

            # Draw AI ship in occupied slot
            if slot["occupied"]:
                ai_rect = pygame.Rect(
                    slot["x"] + 5, slot["y"] + 3,
                    slot["w"] - 10, slot["h"] - 6
                )
                pygame.draw.rect(screen, color, ai_rect, 1)
                # Simple triangle nose
                nose_x = ai_rect.x + ai_rect.w
                nose_y = ai_rect.y + ai_rect.h // 2
                pygame.draw.polygon(screen, color, [
                    (nose_x, nose_y),
                    (nose_x - 8, nose_y - 5),
                    (nose_x - 8, nose_y + 5),
                ], 0)

        # === PLAYER SHIP ===
        # Side-view ship rectangle with triangle nose
        ship_rect = self._get_ship_rect()
        pygame.draw.rect(screen, color,
                         (ship_rect.x, ship_rect.y, ship_rect.w, ship_rect.h), 0)
        # Nose
        nose_tip = (ship_rect.x + ship_rect.w + 8, ship_rect.y + ship_rect.h // 2)
        nose_top = (ship_rect.x + ship_rect.w, ship_rect.y + 2)
        nose_bot = (ship_rect.x + ship_rect.w, ship_rect.y + ship_rect.h - 2)
        pygame.draw.polygon(screen, color, [nose_tip, nose_top, nose_bot], 0)
        # Thrust flame when thrusting
        keys = pygame.key.get_pressed()
        if keys[pygame.K_SPACE]:
            flame_x = ship_rect.x - 2
            flame_y = ship_rect.y + ship_rect.h // 2
            flame_len = random.randint(6, 14)
            pygame.draw.line(screen, color,
                             (flame_x, flame_y),
                             (flame_x - flame_len, flame_y), 2)

        # === INSTRUCTIONS ===
        instr = "SPACE:Thrust  A/D:Move  Gravity:Pull  ESC:Abort"
        instr_surf = self.font_small.render(instr, True, color)
        screen.blit(instr_surf, (cfg.SCREEN_WIDTH // 2 - instr_surf.get_width() // 2, 6))

        # Gate status and wrong slot warning
        if not self.passed_gate:
            gate_hint = self.font_medium.render("FLY THROUGH THE GATE!", True, color)
            screen.blit(gate_hint, (cfg.SCREEN_WIDTH // 2 - gate_hint.get_width() // 2,
                                    cfg.SCREEN_HEIGHT // 2 - 150))
        else:
            target = self.slots[self.target_slot_idx]
            park_hint = self.font_medium.render(f"PARK IN SLOT {self.target_slot_idx + 1}!", True, color)
            screen.blit(park_hint, (cfg.SCREEN_WIDTH // 2 - park_hint.get_width() // 2,
                                    cfg.SCREEN_HEIGHT // 2 - 150))

        # Wrong slot warning
        if self.wrong_slot_timer > 0 and self.passed_gate:
            remaining = max(0, 5.0 - self.wrong_slot_timer)
            if remaining < 2:
                warn_color = color
            else:
                warn_color = color
            warn = self.font_medium.render(f"WRONG SLOT! MOVE! {remaining:.1f}s", True, warn_color)
            screen.blit(warn, (cfg.SCREEN_WIDTH // 2 - warn.get_width() // 2,
                               cfg.SCREEN_HEIGHT // 2 - 100))

        # Messages
        if self.message:
            self.message.draw(screen)

        # HP bar at bottom
        hp_ratio = max(0, self.player.hp / self.player.max_hp)
        bar_w = 200
        bar_x = cfg.SCREEN_WIDTH - bar_w - 20
        bar_y = cfg.SCREEN_HEIGHT - 16
        pygame.draw.rect(screen, color, (bar_x, bar_y, bar_w, 10), 1)
        pygame.draw.rect(screen, color, (bar_x, bar_y, int(bar_w * hp_ratio), 10))
        hp_text = self.font_small.render(f"HP: {int(self.player.hp)}", True, color)
        screen.blit(hp_text, (bar_x - hp_text.get_width() - 10, bar_y - 2))
