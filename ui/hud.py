import math
import pygame
import settings as cfg


class HUD:
    """Heads-up display rendered during space flight."""

    def __init__(self, font_small, font_medium):
        self.font_small = font_small
        self.font_medium = font_medium

    def draw(self, screen, player, elapsed_time):
        """Draw all HUD elements on the screen."""
        color = cfg.WHITE
        y = 10
        spacing = 20

        # Top-left: rank, credits, fuel, HP
        texts = [
            f"RANK: {player.rank()}",
            f"CREDITS: {player.credits}",
            f"FUEL: {int(player.fuel)}/{int(player.max_fuel)}",
            f"HP: {int(player.hp)}/{int(player.max_hp)}",
        ]
        if player.fuel <= (player.max_fuel / 2):
            texts.insert(1, "WARNING: LOW FUEL")
        
        for i, text in enumerate(texts):
            # Pokud je to warning text, můžeme ho nechat blikat
            if "WARNING" in text:
                # Jednoduché blikání s pomocí elapsed_time (pokud je elapsed_time jako parametr, jinak jen vykreslíme)
                if int(elapsed_time * 2) % 2 == 0:
                    surf = self.font_small.render(text, True, color)
                    screen.blit(surf, (10, y))
            else:
                surf = self.font_small.render(text, True, color)
                screen.blit(surf, (10, y))
            y += spacing

        # Top-right: speed, coordinates, time
        y = 10
        speed = math.hypot(player.vx, player.vy)
        right_texts = [
            f"SPEED: {int(speed)} px/s",
            f"X: {int(player.x)}  Y: {int(player.y)}",
            f"TIME: {int(elapsed_time // 60):02d}:{int(elapsed_time % 60):02d}",
        ]
        for text in right_texts:
            surf = self.font_small.render(text, True, color)
            screen.blit(surf, (cfg.SCREEN_WIDTH - surf.get_width() - 10, y))
            y += spacing

        # Bottom-center: cargo bar
        cargo_used = player.cargo_used()
        cargo_max = player.max_cargo
        bar_x = 10
        bar_y = cfg.SCREEN_HEIGHT - 30
        bar_w = 200
        bar_h = 16
        pygame.draw.rect(screen, color, (bar_x, bar_y, bar_w, bar_h), 1)
        if cargo_max > 0:
            fill_w = int((cargo_used / cargo_max) * bar_w)
            pygame.draw.rect(screen, color, (bar_x, bar_y, fill_w, bar_h))
        cargo_text = self.font_small.render(f"CARGO: {cargo_used}/{cargo_max}", True, color)
        screen.blit(cargo_text, (bar_x + bar_w + 10, bar_y - 2))

        # Bottom-center: speed bar (referenced against SPEED_DISPLAY_REF, not the hard cap)
        speed_ratio = min(speed / cfg.SPEED_DISPLAY_REF, 1.0)
        spd_bar_x = cfg.SCREEN_WIDTH // 2 - 100
        spd_bar_y = cfg.SCREEN_HEIGHT - 30
        spd_bar_w = 200
        spd_bar_h = 10
        pygame.draw.rect(screen, color, (spd_bar_x, spd_bar_y, spd_bar_w, spd_bar_h), 1)
        fill_w = int(speed_ratio * spd_bar_w)
        pygame.draw.rect(screen, color, (spd_bar_x, spd_bar_y, fill_w, spd_bar_h))

        # Bottom-center: controls hint (right corner is reserved for radar)
        hints = [
            "WASD:Fly  Shift:Boost  M:Map  Tab:Waypoint  Esc:Pause",
        ]
        if player.has_hyperdrive:
            hints[0] += "  J:WARP"
        hint_surf = self.font_small.render(hints[0], True, color)
        screen.blit(hint_surf, ((cfg.SCREEN_WIDTH - hint_surf.get_width()) // 2,
                                cfg.SCREEN_HEIGHT - 14))

        # Warp cooldown indicator
        if player.warp_cooldown > 0:
            cd_text = f"WARP COOLDOWN: {player.warp_cooldown:.1f}s"
            cd_surf = self.font_medium.render(cd_text, True, color)
            screen.blit(cd_surf, (cfg.SCREEN_WIDTH // 2 - cd_surf.get_width() // 2,
                                  cfg.SCREEN_HEIGHT // 2 + 50))
