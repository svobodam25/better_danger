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
from scenes.mine_scene import MineScene
from utils.helpers import snap_to_grid
from utils import save as savemod
from ui.menu import MainMenu


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

        # Game state — start at title screen; actual game scenes created on demand.
        self.scene = "menu"  # "menu", "space", "dock", "trade", "mine", "dead"
        self.running = True
        self.paused = False

        # Player / scenes are created when the user picks New or Continue from the menu.
        self.player = None
        self.space_scene = None
        self.dock_scene = None
        self.trade_scene = None
        self.mine_scene = None

        # Title screen
        self.main_menu = MainMenu(
            self.font_small, self.font_medium, self.font_large, self.font_huge)

        # Reveal queue (maps bought)
        self.pending_reveals = 0
        self.reveal_timer = 0.0

        # Death timer (show death screen briefly)
        self.death_timer = 0.0

    def _start_new_game(self):
        """Wipe any existing save and start a fresh run."""
        savemod.delete_save()
        self.player = Player(0, 0)
        self.space_scene = SpaceScene(
            self.player, self.font_small, self.font_medium, self.font_large)
        self.dock_scene = None
        self.trade_scene = None
        self.mine_scene = None
        self.scene = "space"
        self.paused = False

    def _continue_game(self):
        """Load saved state and resume in the space scene. Falls back to New if save is bad."""
        save_data = savemod.load_game()
        if not save_data:
            self._start_new_game()
            return
        self.player = Player(0, 0)
        self.space_scene = SpaceScene(
            self.player, self.font_small, self.font_medium, self.font_large)
        try:
            savemod.apply_to_player(self.player, save_data)
            for gx, gy in save_data.get("known_planet_grid", []):
                planet = self.space_scene._get_or_generate_planet(gx, gy)
                self.player.know_planet(planet)
        except (KeyError, TypeError, ValueError):
            savemod.delete_save()
            self._start_new_game()
            return
        self.dock_scene = None
        self.trade_scene = None
        self.mine_scene = None
        self.scene = "space"
        self.paused = False

    def _return_to_menu(self):
        """Go back to the title screen (used after death)."""
        self.player = None
        self.space_scene = None
        self.dock_scene = None
        self.trade_scene = None
        self.mine_scene = None
        self.paused = False
        self.scene = "menu"
        self.main_menu.reset()

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
                    # Save only happens at stations; quitting from space discards progress
                    # since the last station visit. Persisted state stays intact on disk.

                # Scene-specific event handling
                result = None
                if self.scene == "menu":
                    action = self.main_menu.handle_input(event)
                    if action == MainMenu.NEW:
                        self._start_new_game()
                    elif action == MainMenu.CONTINUE:
                        self._continue_game()
                    elif action == MainMenu.EXIT:
                        self.running = False
                elif self.scene == "space":
                    result = self.space_scene.handle_input(event)
                    if result == "menu":
                        self._return_to_menu()
                        result = None
                elif self.scene == "dock" and self.dock_scene:
                    result = self.dock_scene.handle_input(event)
                elif self.scene == "trade" and self.trade_scene:
                    result = self.trade_scene.handle_input(event)
                elif self.scene == "mine" and self.mine_scene:
                    result = self.mine_scene.handle_input(event)
                    if result == "leave":
                        self.scene = "space"

            # Title screen render — no game logic, no autosave, no death handling.
            if self.scene == "menu":
                self.main_menu.draw(self.screen)
                pygame.display.flip()
                continue

            if self.paused:
                self._draw_pause()
                continue

            if self.scene == "dead":
                self.death_timer -= dt
                self._draw_death()
                if self.death_timer <= 0:
                    self._return_to_menu()
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
                elif result == "mine":
                    ast = self.space_scene.target_asteroid
                    if ast:
                        self.mine_scene = MineScene(
                            self.player, ast,
                            self.font_small, self.font_medium, self.font_large, self.font_huge)
                        self.scene = "mine"
                self.space_scene.draw(self.screen)

                # Handle pending map reveals
                if hasattr(self.player, '_pending_reveals') and self.player._pending_reveals > 0:
                    self._reveal_nearby_planets(self.player._pending_reveals)
                    self.player._pending_reveals = 0

            elif self.scene == "dock":
                result = self.dock_scene.update(dt, keys)
                if result == "success":
                    # Transition to trade — now docked at the station, safe to autosave.
                    target = self.space_scene.get_target_planet()
                    if target:
                        self.trade_scene = TradeScene(
                            self.player, target,
                            self.font_small, self.font_medium, self.font_large)
                        self.scene = "trade"
                        self._autosave()
                elif result == "dead":
                    self.scene = "dead"
                    self.death_timer = 3.0
                elif result == "abort":
                    # Go back to space (abort docking)
                    self._abort_dock()
                self.dock_scene.draw(self.screen)

            elif self.scene == "mine":
                result = self.mine_scene.update(dt, keys)
                if result == "leave":
                    self.scene = "space"
                self.mine_scene.draw(self.screen)

            elif self.scene == "trade":
                result = self.trade_scene.update(dt)
                if result == "leave":
                    # Go back to space
                    self.scene = "space"
                    self.player.dock_cooldown = 3.0
                    self._autosave()
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
                # Death wipes the save so the next launch is a fresh run
                savemod.delete_save()

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

    def _autosave(self):
        """Persist the current player + known-planet state to disk."""
        if self.player is None or self.player.is_dead():
            return
        savemod.save_game(self.player, self.player.known_planets.values())

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
        restart_text = self.font_medium.render(f"Returning to menu in {int(max(0, self.death_timer))}...", True, cfg.WHITE)
        self.screen.blit(restart_text, (
            cfg.SCREEN_WIDTH // 2 - restart_text.get_width() // 2,
            cfg.SCREEN_HEIGHT // 2 + 40,
        ))
        pygame.display.flip()


if __name__ == "__main__":
    game = Game()
    game.run()
