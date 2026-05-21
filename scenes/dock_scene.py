import math
import os
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
        
        # Load player sprite
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        img_path = os.path.join(base_dir, "obrazky elite", "pixil-frame-0 (20).png")
        try:
            self.ship_img = pygame.image.load(img_path).convert_alpha()
        except (pygame.error, FileNotFoundError) as e:
            print(f"Nepodařilo se načíst obrázek lodi do docku: {e}")
            self.ship_img = None

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

        # Gravity & thrust — MUCH STRONGER
        self.gravity = 0.0          # px/s² downward
        self.thrust_power = 600.0     # px/s² upward
        self.horizontal_speed = 320.0 # px/s horizontal

        # Gate (STATIC — does not move)
        self.gate_x = self.hangar_left
        self.gate_gap = 200           # height of the opening (wider)
        self.gate_center = float(h // 2)  # fixed at center

        # Parking slots — 3 on ceiling, 3 on floor (magnetic clamp stations)
        self.slots = []
        slot_w = 100
        slot_h = 40
        slot_gap = 30
        total_slots = 6  # 3 ceiling + 3 floor
        start_x = int(self.hangar_left + 200)  # pushed far right by gate

        for i in range(3):
            sx = start_x + i * (slot_w + slot_gap)
            # Ceiling slot
            self.slots.append({
                "x": sx, "y": self.ceiling_y, "w": slot_w, "h": slot_h,
                "occupied": False, "target": False, "ceiling": True,
            })
            # Floor slot
            self.slots.append({
                "x": sx, "y": self.floor_y - slot_h, "w": slot_w, "h": slot_h,
                "occupied": False, "target": False, "ceiling": False,
            })

        # Pick random target slot
        self.target_slot_idx = random.randint(0, total_slots - 1)
        self.slots[self.target_slot_idx]["target"] = True

        # Occupy ~40% of slots with AI ships
        for i in range(total_slots):
            if i != self.target_slot_idx and random.random() < 0.4:
                self.slots[i]["occupied"] = True

        self.clamped = False        # True when grabbed by a slot
        self.clamped_at_ceiling = False
        self.docking_timer = 0.0    # countdown when parked in target slot

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
        """Get top and bottom gate barrier rects — VERY THICK gate (10x)."""
        half_gap = self.gate_gap // 2
        gate_thickness = 140
        top_rect = pygame.Rect(
            self.gate_x - gate_thickness // 2, 0,
            gate_thickness, int(self.gate_center - half_gap)
        )
        bot_rect = pygame.Rect(
            self.gate_x - gate_thickness // 2, int(self.gate_center + half_gap),
            gate_thickness, cfg.SCREEN_HEIGHT
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
        if ship_rect.left > self.gate_x + 20:
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

        # For ceiling slots: ship must be just below the slot
        # For floor slots: ship must be just above the slot
        if slot.get("ceiling", False):
            expected_y = slot["y"] + slot["h"] + self.ship_h // 2 + 2
        else:
            expected_y = slot["y"] - self.ship_h // 2 - 2
        dy = abs(self.ship_y - expected_y)

        return (dx < cfg.DOCK_TOLERANCE_POS and
                dy < cfg.DOCK_TOLERANCE_POS + 15)

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
        self.message = MessageBox(f"WALL! -{int(cfg.WALL_DAMAGE)} HP", self.font_medium, -120)

    def update(self, dt, keys):
        """Update docking scene."""
        self.flash_timer += dt

        if self.collision_cooldown > 0:
            self.collision_cooldown -= dt
        if self.gate_collision_cooldown > 0:
            self.gate_collision_cooldown -= dt

        # Gate is STATIC — no movement

        # === PLAYER CONTROLS ===
        # Gravity pulls down (unless clamped to a station)
        if not self.clamped:
            self.ship_vy += self.gravity * dt

        # Boost on Shift
        speed_mult = 2.0 if (keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]) else 1.0
        current_speed = self.horizontal_speed * speed_mult

        # W/S = vertical movement
        if keys[pygame.K_w]:
            self.ship_vy = -current_speed
        elif keys[pygame.K_s]:
            self.ship_vy = current_speed
        else:
            self.ship_vy = 0.0

        # A/D = horizontal movement
        if keys[pygame.K_a]:
            self.ship_vx = -current_speed
        elif keys[pygame.K_d]:
            self.ship_vx = current_speed
        else:
            self.ship_vx = 0.0

        if self.ship_vx != 0 or self.ship_vy != 0:
            self.angle = math.degrees(math.atan2(self.ship_vy, self.ship_vx))

        # Fly-away abort: if ship goes far left, return to space
        if self.ship_x < -30:
            return "abort"

        # Apply velocity
        self.ship_x += self.ship_vx * dt
        self.ship_y += self.ship_vy * dt

        # Clamp to screen bounds
        self.ship_x = max(self.ship_w // 2, min(cfg.SCREEN_WIDTH - self.ship_w // 2, self.ship_x))

        # Gate collision — HARD WALL, cannot pass through solid gate
        if not self.passed_gate:
            ship_rect = self._get_ship_rect()
            top_rect, bot_rect = self._get_gate_rects()

            # Hard block: if ship overlaps gate, push it back
            if ship_rect.colliderect(top_rect):
                # Ship hit top gate — push to the left side
                self.ship_x = min(self.ship_x, self.gate_x - top_rect.w // 2 - self.ship_w // 2 - 2)
                self.ship_vx = 0
                if self.gate_collision_cooldown <= 0:
                    self.player.damage(cfg.WALL_DAMAGE)
                    self.gate_collision_cooldown = 0.5
                    self.message = MessageBox(f"GATE! -{int(cfg.WALL_DAMAGE)} HP", self.font_medium, -120)
            elif ship_rect.colliderect(bot_rect):
                self.ship_x = min(self.ship_x, self.gate_x - bot_rect.w // 2 - self.ship_w // 2 - 2)
                self.ship_vx = 0
                if self.gate_collision_cooldown <= 0:
                    self.player.damage(cfg.WALL_DAMAGE)
                    self.gate_collision_cooldown = 0.5
                    self.message = MessageBox(f"GATE! -{int(cfg.WALL_DAMAGE)} HP", self.font_medium, -120)

            # Check if passed through gate successfully
            if self._check_passed_gate():
                self.passed_gate = True
                self.message = MessageBox("ENTERED HANGAR!", self.font_medium, -120)

        # === TRAFFIC SHIPS (departing & arriving through gate) ===
        self._update_traffic(dt)

        # Clamp check — magnetic grab at slot stations (ceiling/floor)
        ship_rect = self._get_ship_rect()
        was_clamped = self.clamped
        self.clamped = False
        for slot in self.slots:
            slot_rect = pygame.Rect(slot["x"], slot["y"], slot["w"], slot["h"])
            if ship_rect.colliderect(slot_rect):
                self.clamped = True
                self.clamped_at_ceiling = slot.get("ceiling", False)
                # Snap to slot
                if self.clamped_at_ceiling:
                    self.ship_y = slot["y"] + slot["h"] + self.ship_h // 2 + 1
                else:
                    self.ship_y = slot["y"] - self.ship_h // 2 - 1
                self.ship_vy = 0
                break

        # Wall collision (ceiling/floor) — only if not clamped
        if not self.clamped and self._check_wall_collision():
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
            # Check if parked in target slot — 1.5s docking sequence
            if self._check_parked_in_slot(self.target_slot_idx):
                self.ship_vx = 0
                self.ship_vy = 0
                self.docking_timer += dt
                if self.docking_timer >= 1.5:
                    return "success"
            else:
                self.docking_timer = 0.0

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

        # Hangar left wall — split by gate gap (no line through the opening)
        half_gap = self.gate_gap // 2
        gap_top = int(self.gate_center - half_gap)
        gap_bot = int(self.gate_center + half_gap)
        pygame.draw.line(screen, color, (self.hangar_left, self.ceiling_y),
                         (self.hangar_left, gap_top), 2)
        pygame.draw.line(screen, color, (self.hangar_left, gap_bot),
                         (self.hangar_left, self.floor_y), 2)

        # === OUTSIDE AREA (left of gate) ===
        # Ceiling & floor outside
        pygame.draw.line(screen, color, (0, self.ceiling_y),
                         (self.hangar_left, self.ceiling_y), 1)
        pygame.draw.line(screen, color, (0, self.floor_y),
                         (self.hangar_left, self.floor_y), 1)

        # === GATE (massive thick barriers, clean gap opening) ===
        top_rect, bot_rect = self._get_gate_rects()
        half_gap = self.gate_gap // 2
        gap_top = int(self.gate_center - half_gap)
        gap_bot = int(self.gate_center + half_gap)

        # Gate bars — solid white blocks
        pygame.draw.rect(screen, color, top_rect)
        pygame.draw.rect(screen, color, bot_rect)

        # Diagonal hazard stripes on the gate
        for gy in range(0, top_rect.height, 10):
            x0 = top_rect.x
            x1 = top_rect.x + top_rect.w
            pygame.draw.line(screen, cfg.BLACK, (x0, gy), (x1, gy + 10), 2)
        for gy in range(bot_rect.y, bot_rect.y + bot_rect.height, 10):
            x0 = bot_rect.x
            x1 = bot_rect.x + bot_rect.w
            pygame.draw.line(screen, cfg.BLACK, (x0, gy), (x1, gy + 10), 2)

        # Clean gap — no lines inside the opening, just open space
        # Vertical edges of the gate on each side of the gap
        gate_left = top_rect.x
        gate_right = top_rect.x + top_rect.w

        # Gate label centered above
        label = self.font_small.render("GATE", True, color)
        screen.blit(label, (self.gate_x - label.get_width() // 2, self.ceiling_y - 18))


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

        # === PARKING SLOTS (magnetic clamp stations — 3 ceiling + 3 floor) ===
        for i, slot in enumerate(self.slots):
            rect = pygame.Rect(slot["x"], slot["y"], slot["w"], slot["h"])
            is_ceiling = slot.get("ceiling", False)

            # Slot body (clamp-style with diagonal grip lines)
            pygame.draw.rect(screen, color, rect, 0)
            # Diagonal grip lines
            for gx in range(rect.x + 4, rect.x + rect.w - 4, 10):
                if is_ceiling:
                    pygame.draw.line(screen, cfg.BLACK, (gx, rect.y), (gx + 8, rect.y + rect.h), 2)
                else:
                    pygame.draw.line(screen, cfg.BLACK, (gx, rect.y + rect.h), (gx + 8, rect.y), 2)

            if slot["target"]:
                # Blinking target slot — thick white border
                alpha = (math.sin(self.flash_timer * 5) + 1) / 2
                border_w = 3 if alpha > 0.4 else 1
                pygame.draw.rect(screen, color, rect, border_w)
            else:
                pygame.draw.rect(screen, color, rect, 1)

            # Slot number — C for ceiling, G for ground
            label_text = f"C{i // 2 + 1}" if is_ceiling else f"G{i // 2 + 1}"
            num_surf = self.font_small.render(label_text, True, color)
            label_y = rect.y - 16 if is_ceiling else rect.y + rect.h + 4
            screen.blit(num_surf, (rect.x + rect.w // 2 - num_surf.get_width() // 2, label_y))

            # Draw AI ship in occupied slot
            if slot["occupied"]:
                ai_rect = pygame.Rect(
                    rect.x + 5, rect.y + 3,
                    rect.w - 10, rect.h - 6
                )
                pygame.draw.rect(screen, color, ai_rect, 1)
                nose_x = ai_rect.x + ai_rect.w
                nose_y = ai_rect.y + ai_rect.h // 2
                pygame.draw.polygon(screen, color, [
                    (nose_x, nose_y),
                    (nose_x - 8, nose_y - 5),
                    (nose_x - 8, nose_y + 5),
                ], 0)

        # Target slot big label — centered on screen
        target = self.slots[self.target_slot_idx]
        is_ceiling = target.get("ceiling", False)
        slot_label = f"C{self.target_slot_idx // 2 + 1}" if is_ceiling else f"G{self.target_slot_idx // 2 + 1}"
        park_text = self.font_large.render(f"PARK IN SLOT {slot_label}", True, color)
        screen.blit(park_text, (cfg.SCREEN_WIDTH // 2 - park_text.get_width() // 2, 140))

        # Docking progress indicator — centered on screen
        if self.docking_timer > 0:
            progress = min(1.0, self.docking_timer / 1.5)
            dock_text = self.font_large.render(f"DOCKING... {int(progress * 100)}%", True, color)
            screen.blit(dock_text, (cfg.SCREEN_WIDTH // 2 - dock_text.get_width() // 2, 170))
            # Progress bar
            bar_w = 300
            bar_x = cfg.SCREEN_WIDTH // 2 - bar_w // 2
            bar_y = cfg.SCREEN_HEIGHT // 2 + 10
            pygame.draw.rect(screen, color, (bar_x, bar_y, bar_w, 12), 1)
            pygame.draw.rect(screen, color, (bar_x, bar_y, int(bar_w * progress), 12))

        # === PLAYER SHIP (detailed model, faces direction of movement) ===
        ship_rect = self._get_ship_rect()
        sx, sy, sw, sh = ship_rect.x, ship_rect.y, ship_rect.w, ship_rect.h
        keys = pygame.key.get_pressed()

        # Facing direction: A = left, D = right
        facing_right = keys[pygame.K_d] or (not keys[pygame.K_a] and not keys[pygame.K_d])

        if hasattr(self, 'ship_img') and self.ship_img:
            # Draw sprite
            img_to_draw = self.ship_img
            
            # Rotate image to face movement direction based on self.angle
            # Pygame rotates counter-clockwise. Pixel art points UP usually,
            # so we offset by 90 degrees just like in space_scene.
            # But the user asked to rotate it 90 degrees right in dock, 
            # maybe because their source image points RIGHT?
            # We will rotate based on calculated angle.
            img_to_draw = pygame.transform.rotate(img_to_draw, -self.angle - 90)
            
            # Vykreslení
            rect = img_to_draw.get_rect(center=(sx + sw // 2, sy + sh // 2))
            screen.blit(img_to_draw, rect.topleft)
            
            # Plameny (flames)
            if keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT] or keys[pygame.K_w] or keys[pygame.K_a] or keys[pygame.K_s] or keys[pygame.K_d]:
                rad = math.radians(self.angle)
                # Konec lodi je proti směru pohybu
                flame_x = (sx + sw // 2) - math.cos(rad) * (sw // 2)
                flame_y = (sy + sh // 2) - math.sin(rad) * (sh // 2)
                
                flame_len = random.randint(15, 25)
                f2_len = random.randint(10, 20)
                
                # Výpočet koncových bodů plamenů
                end_x = flame_x - math.cos(rad) * flame_len
                end_y = flame_y - math.sin(rad) * flame_len
                
                pygame.draw.line(screen, color, (flame_x, flame_y), (end_x, end_y), 3)
                
        else:
            # Původní vykreslování lodi
            if facing_right:
                # --- FACING RIGHT ---
                body_rect = pygame.Rect(sx + 6, sy, int(sw * 0.7), sh)
                pygame.draw.rect(screen, color, body_rect, 0)
                cockpit_x = sx + sw - int(sw * 0.35)
                cockpit_y = sy + 3
                cockpit_w = int(sw * 0.22)
                cockpit_h = sh - 6
                pygame.draw.rect(screen, cfg.BLACK, (cockpit_x, cockpit_y, cockpit_w, cockpit_h), 0)
                pygame.draw.rect(screen, color, (cockpit_x, cockpit_y, cockpit_w, cockpit_h), 1)

                fin_top = [(sx + sw // 2 - 4, sy), (sx + sw // 2 + 4, sy), (sx + sw // 2, sy - 8)]
                pygame.draw.polygon(screen, color, fin_top, 0)
                fin_bot = [(sx + sw // 2 - 4, sy + sh), (sx + sw // 2 + 4, sy + sh), (sx + sw // 2, sy + sh + 8)]
                pygame.draw.polygon(screen, color, fin_bot, 0)

                nose_len = 12
                nose_tip = (sx + sw + nose_len, sy + sh // 2)
                nose_top = (sx + sw, sy + 2)
                nose_bot = (sx + sw, sy + sh - 2)
                pygame.draw.polygon(screen, color, [nose_tip, nose_top, nose_bot], 0)

                engine_w = 8
                engine_h = sh - 6
                pygame.draw.rect(screen, color, (sx, sy + 3, engine_w, engine_h), 1)

                if keys[pygame.K_SPACE]:
                    flame_x = sx
                    flame_y = sy + sh // 2
                    flame_len = random.randint(10, 20)
                    pygame.draw.line(screen, color, (flame_x, flame_y - 2), (flame_x - flame_len, flame_y - 2), 2)
                    pygame.draw.line(screen, color, (flame_x, flame_y + 2), (flame_x - flame_len, flame_y + 2), 2)
                    f2_len = random.randint(6, 16)
                    pygame.draw.line(screen, color, (flame_x, flame_y), (flame_x - f2_len, flame_y), 3)
            else:
                # --- FACING LEFT ---
                body_rect = pygame.Rect(sx + sw - 6 - int(sw * 0.7), sy, int(sw * 0.7), sh)
                pygame.draw.rect(screen, color, body_rect, 0)

                cockpit_x = sx + int(sw * 0.13)
                cockpit_y = sy + 3
                cockpit_w = int(sw * 0.22)
                cockpit_h = sh - 6
                pygame.draw.rect(screen, cfg.BLACK, (cockpit_x, cockpit_y, cockpit_w, cockpit_h), 0)
                pygame.draw.rect(screen, color, (cockpit_x, cockpit_y, cockpit_w, cockpit_h), 1)

                fin_top = [(sx + sw // 2 - 4, sy), (sx + sw // 2 + 4, sy), (sx + sw // 2, sy - 8)]
                pygame.draw.polygon(screen, color, fin_top, 0)
                fin_bot = [(sx + sw // 2 - 4, sy + sh), (sx + sw // 2 + 4, sy + sh), (sx + sw // 2, sy + sh + 8)]
                pygame.draw.polygon(screen, color, fin_bot, 0)

                nose_len = 12
                nose_tip = (sx - nose_len, sy + sh // 2)
                nose_top = (sx, sy + 2)
                nose_bot = (sx, sy + sh - 2)
                pygame.draw.polygon(screen, color, [nose_tip, nose_top, nose_bot], 0)

                engine_w = 8
                engine_h = sh - 6
                pygame.draw.rect(screen, color, (sx + sw - engine_w, sy + 3, engine_w, engine_h), 1)

                if keys[pygame.K_SPACE]:
                    flame_x = sx + sw
                    flame_y = sy + sh // 2
                    flame_len = random.randint(10, 20)
                    pygame.draw.line(screen, color, (flame_x, flame_y - 2), (flame_x + flame_len, flame_y - 2), 2)
                    pygame.draw.line(screen, color, (flame_x, flame_y + 2), (flame_x + flame_len, flame_y + 2), 2)
                    f2_len = random.randint(6, 16)
                    pygame.draw.line(screen, color, (flame_x, flame_y), (flame_x + f2_len, flame_y), 3)


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
