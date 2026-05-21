# Better Danger — Main Entry Point
# Elite Danger, but better. Monochrome space trading game.
# Infinite universe, procedurally generated planets, newtonian physics.

import sys
import math
import random
import pygame
import settings as cfg
from entities.player import Player
from entities.planet import Planet
from scenes.space_scene import SpaceScene
from scenes.dock_scene import DockScene
from scenes.trade_scene import TradeScene
from utils.helpers import snap_to_grid


class Game:
    """Main game class managing scenes and game loop."""

    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT))
        pygame.display.set_caption("Better Danger")
        self.clock = pygame.time.Clock()

        # Fonts (try system monospace, fallback to default)
        font_name = "consolas" if sys.platform == "win32" else None
        try:
            self.font_small = pygame.font.SysFont(font_name or "monospace", cfg.FONT_SMALL)
            self.font_medium = pygame.font.SysFont(font_name or "monospace", cfg.FONT_MEDIUM)
            self.font_large = pygame.font.SysFont(font_name or "monospace", cfg.FONT_LARGE)
            self.font_huge = pygame.font.SysFont(font_name or "monospace", cfg.FONT_HUGE)
        except Exception:
            self.font_small = pygame.font.Font(None, cfg.FONT_SMALL)
            self.font_medium = pygame.font.Font(None, cfg.FONT_MEDIUM)
            self.font_large = pygame.font.Font(None, cfg.FONT_LARGE)
            self.font_huge = pygame.font.Font(None, cfg.FONT_HUGE)

        # Game state
        self.scene = "space"  # "space", "dock", "trade", "menu", "dead"
        self.running = True
        self.paused = False

        # Player
        self.player = Player(0, 0)

        # Scenes
        self.space_scene = SpaceScene(self.player, self.font_small, self.font_medium, self.font_large)
        self.dock_scene = None
        self.trade_scene = None

        # Reveal queue (maps bought)
        self.pending_reveals = 0
        self.reveal_timer = 0.0

        # Death timer (show death screen briefly)
        self.death_timer = 0.0

    def run(self):
        """Main game loop."""
        while self.running:
            dt = self.clock.tick(cfg.FPS) / 1000.0
            # Cap dt to prevent physics explosions
            dt = min(dt, 0.1)

            keys = pygame.key.get_pressed()

            # Process events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False

                # Scene-specific event handling
                result = None
                if self.scene == "space":
                    result = self.space_scene.handle_input(event)
                elif self.scene == "dock" and self.dock_scene:
                    result = self.dock_scene.handle_input(event)
                elif self.scene == "trade" and self.trade_scene:
                    result = self.trade_scene.handle_input(event)

                if result == "pause":
                    self.paused = not self.paused

            if self.paused:
                self._draw_pause()
                continue

            if self.scene == "dead":
                self.death_timer -= dt
                self._draw_death()
                if self.death_timer <= 0:
                    # Restart
                    self._restart()
                continue

            # Update based on current scene
            if self.scene == "space":
                result = self.space_scene.update(dt, keys)
                if result == "dock":
                    target = self.space_scene.get_target_planet()
                    if target:
                        self.dock_scene = DockScene(
                            self.player, self.font_small, self.font_medium, self.font_large)
                        self.scene = "dock"
                self.space_scene.draw(self.screen)

                # Handle pending map reveals
                if hasattr(self.player, '_pending_reveals') and self.player._pending_reveals > 0:
                    self._reveal_nearby_planets(self.player._pending_reveals)
                    self.player._pending_reveals = 0

            elif self.scene == "dock":
                result = self.dock_scene.update(dt, keys)
                if result == "success":
                    # Transition to trade
                    target = self.space_scene.get_target_planet()
                    if target:
                        self.trade_scene = TradeScene(
                            self.player, target,
                            self.font_small, self.font_medium, self.font_large)
                        self.scene = "trade"
                elif result == "dead":
                    self.scene = "dead"
                    self.death_timer = 3.0
                elif result == "abort":
                    # Go back to space (abort docking)
                    self._abort_dock()
                self.dock_scene.draw(self.screen)

            elif self.scene == "trade":
                result = self.trade_scene.update(dt)
                if result == "leave":
                    # Go back to space
                    self.scene = "space"
                    self.player.dock_cooldown = 3.0
                    # Push player away from planet
                    target = self.space_scene.get_target_planet()
                    if target:
                        angle = math.atan2(self.player.y - target.y, self.player.x - target.x)
                        self.player.x = target.x + math.cos(angle) * (cfg.DOCK_PROXIMITY + target.radius + 50)
                        self.player.y = target.y + math.sin(angle) * (cfg.DOCK_PROXIMITY + target.radius + 50)
                        self.player.vx = math.cos(angle) * 50
                        self.player.vy = math.sin(angle) * 50
                # Check for pending reveals
                if hasattr(self.player, '_pending_reveals') and self.player._pending_reveals > 0:
                    self._reveal_nearby_planets(self.player._pending_reveals)
                    self.player._pending_reveals = 0
                self.trade_scene.draw(self.screen)

            # Check if player died during space scene
            if self.player.is_dead() and self.scene != "dead":
                self.scene = "dead"
                self.death_timer = 3.0

            pygame.display.flip()

        pygame.quit()
        sys.exit()

    def _reveal_nearby_planets(self, count):
        """Reveal undiscovered planets nearest to the player."""
        unknown = []
        for key, planet in self.space_scene.generated_planets.items():
            if not self.player.knows_planet(planet.pid):
                dist = math.hypot(planet.x - self.player.x, planet.y - self.player.y)
                unknown.append((dist, planet))
        unknown.sort(key=lambda x: x[0])
        for _, planet in unknown[:count]:
            self.player.know_planet(planet)

    def _abort_dock(self):
        """Abort docking and return to space."""
        self.scene = "space"
        self.player.dock_cooldown = 3.0
        target = self.space_scene.get_target_planet()
        if target:
            angle = math.atan2(self.player.y - target.y, self.player.x - target.x)
            self.player.x = target.x + math.cos(angle) * (cfg.DOCK_PROXIMITY + target.radius + 80)
            self.player.y = target.y + math.sin(angle) * (cfg.DOCK_PROXIMITY + target.radius + 80)
            self.player.vx = 0
            self.player.vy = 0

    def _restart(self):
        """Restart the game after death."""
        self.player = Player(0, 0)
        self.space_scene = SpaceScene(self.player, self.font_small, self.font_medium, self.font_large)
        self.dock_scene = None
        self.trade_scene = None
        self.scene = "space"
        self.pending_reveals = 0
        self.paused = False

    def _draw_pause(self):
        """Draw pause overlay."""
        self.screen.fill(cfg.BLACK)
        pause_text = self.font_huge.render("PAUSED", True, cfg.WHITE)
        self.screen.blit(pause_text, (
            cfg.SCREEN_WIDTH // 2 - pause_text.get_width() // 2,
            cfg.SCREEN_HEIGHT // 2 - pause_text.get_height() // 2,
        ))
        hint = self.font_small.render("Press ESC to continue", True, cfg.WHITE)
        self.screen.blit(hint, (
            cfg.SCREEN_WIDTH // 2 - hint.get_width() // 2,
            cfg.SCREEN_HEIGHT // 2 + 40,
        ))
        pygame.display.flip()

    def _draw_death(self):
        """Draw death screen."""
        self.screen.fill(cfg.BLACK)
        death_text = self.font_huge.render("YOU DIED", True, cfg.WHITE)
        self.screen.blit(death_text, (
            cfg.SCREEN_WIDTH // 2 - death_text.get_width() // 2,
            cfg.SCREEN_HEIGHT // 2 - death_text.get_height() // 2,
        ))
        restart_text = self.font_medium.render(f"Restarting in {int(max(0, self.death_timer))}...", True, cfg.WHITE)
        self.screen.blit(restart_text, (
            cfg.SCREEN_WIDTH // 2 - restart_text.get_width() // 2,
            cfg.SCREEN_HEIGHT // 2 + 40,
        ))
        pygame.display.flip()


if __name__ == "__main__":
    game = Game()
    game.run()
