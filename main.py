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
from ui.menu import MainMenu, SaveSlotPicker, SettingsScreen


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

        # Modal slot picker (opened from the menu when CONTINUE is chosen)
        self.slot_picker = None

        # Settings overlay (opened from the menu when SETTINGS is chosen)
        self.settings_screen = None

        # Theme inversion is applied ONLY to the space scene render — menus,
        # dock/trade/mine and overlays stay in the default monochrome theme.
        self.invert_space_colors = False
        self._invert_surface = pygame.Surface(
            (cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT))
        self._invert_surface.fill((255, 255, 255))

        # Which save slot the current session writes to / respawns from.
        # None until the player picks a slot (load picker or first manual save).
        self.current_slot = None

        # Reveal queue (maps bought)
        self.pending_reveals = 0
        self.reveal_timer = 0.0

        # Death timer (show death screen briefly)
        self.death_timer = 0.0

    def _start_new_game(self, slot=None):
        """Start a fresh run. If `slot` is given the session is bound to that
        slot — any pre-existing save there is wiped and future autosaves write
        to it. Without `slot`, no slot is associated until the player saves."""
        if slot is not None:
            savemod.delete_save(slot)
        self.player = Player(0, 0)
        self.space_scene = SpaceScene(
            self.player, self.font_small, self.font_medium, self.font_large)
        self.dock_scene = None
        self.trade_scene = None
        self.mine_scene = None
        self.scene = "space"
        self.paused = False
        self.current_slot = slot

    def _continue_game(self, slot):
        """Load saved state from `slot` and resume in the space scene."""
        save_data = savemod.load_game(slot)
        if not save_data:
            self._return_to_menu()
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
            savemod.delete_save(slot)
            self._return_to_menu()
            return
        self.dock_scene = None
        self.trade_scene = None
        self.mine_scene = None
        self.scene = "space"
        self.paused = False
        self.current_slot = slot

    def _return_to_menu(self):
        """Drop all game state and show the title screen (used after death + no save)."""
        self.player = None
        self.space_scene = None
        self.dock_scene = None
        self.trade_scene = None
        self.mine_scene = None
        self.paused = False
        self.scene = "menu"
        self.main_menu.reset()

    def _open_menu(self):
        """Pause-style menu opened mid-game — keep the live session intact so
        ESC at the menu can bring the player straight back."""
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
                    if self.slot_picker is not None:
                        picked = self.slot_picker.handle_input(event)
                        if picked is not None:
                            if picked[0] == "select":
                                slot = picked[1]
                                mode = self.slot_picker.mode
                                self.slot_picker = None
                                # In PLAY mode: filled slot continues, empty starts new.
                                if mode == SaveSlotPicker.PLAY:
                                    if savemod.has_save(slot):
                                        self._continue_game(slot)
                                    else:
                                        self._start_new_game(slot=slot)
                                else:
                                    self._continue_game(slot)
                            elif picked[0] == "cancel":
                                self.slot_picker = None
                                self.main_menu.reset()
                        continue
                    if self.settings_screen is not None:
                        s_act = self.settings_screen.handle_input(event)
                        if s_act == SettingsScreen.BACK:
                            self.settings_screen = None
                        continue
                    action = self.main_menu.handle_input(event)
                    if action == MainMenu.PLAY:
                        # Cuphead-style: one button → slot picker covering both
                        # continue (filled slots) and new game (empty slots).
                        self.slot_picker = SaveSlotPicker(
                            SaveSlotPicker.PLAY,
                            self.font_small, self.font_medium,
                            self.font_large, self.font_huge)
                    elif action == MainMenu.SETTINGS:
                        self.settings_screen = SettingsScreen(
                            self.font_small, self.font_medium,
                            self.font_large, self.font_huge,
                            get_invert=lambda: self.invert_space_colors,
                            set_invert=self._set_invert_space_colors)
                    elif action == MainMenu.EXIT:
                        self.running = False
                    elif action == MainMenu.BACK:
                        # ESC at the menu — resume the live session if one exists,
                        # otherwise ignore (do NOT quit the game).
                        if self.player is not None and self.space_scene is not None:
                            self.scene = "space"
                elif self.scene == "space":
                    result = self.space_scene.handle_input(event)
                    if result == "menu":
                        self._open_menu()
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
                if self.slot_picker is not None:
                    self.slot_picker.draw(self.screen)
                elif self.settings_screen is not None:
                    self.settings_screen.draw(self.screen)
                else:
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
                    # Respawn at the slot this run is bound to; fall back to the
                    # most recent save if for some reason no slot is set.
                    slot = self.current_slot
                    if slot is None or not savemod.has_save(slot):
                        slot = savemod.most_recent_slot()
                    if slot is not None:
                        self._continue_game(slot)
                    else:
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
                if self.invert_space_colors:
                    self._apply_space_inversion()

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
                            self.font_small, self.font_medium, self.font_large,
                            self.font_huge)
                        self.scene = "trade"
                        self._autosave(docked_planet=target)
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
                    # Push player away from planet first, then autosave the
                    # post-departure pose — keeps the save in safe space.
                    target = self.space_scene.get_target_planet()
                    if target:
                        angle = math.atan2(self.player.y - target.y, self.player.x - target.x)
                        self.player.x = target.x + math.cos(angle) * (cfg.DOCK_PROXIMITY + target.radius + 50)
                        self.player.y = target.y + math.sin(angle) * (cfg.DOCK_PROXIMITY + target.radius + 50)
                        self.player.vx = math.cos(angle) * 50
                        self.player.vy = math.sin(angle) * 50
                    self._autosave(docked_planet=target)
                # Check for pending reveals
                if hasattr(self.player, '_pending_reveals') and self.player._pending_reveals > 0:
                    self._reveal_nearby_planets(self.player._pending_reveals)
                    self.player._pending_reveals = 0
                self.trade_scene.draw(self.screen)

            # Adopt any slot the player just chose via the trade-scene SAVE picker
            slot_pick = getattr(self.player, "last_saved_slot", None)
            if slot_pick is not None:
                self.current_slot = slot_pick
                self.player.last_saved_slot = None

            # Check if player died during space scene
            if self.player.is_dead() and self.scene != "dead":
                self.scene = "dead"
                self.death_timer = 3.0
                # Keep the save so we can respawn at the last station checkpoint.

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

    def _set_invert_space_colors(self, value):
        self.invert_space_colors = bool(value)

    def _apply_space_inversion(self):
        """Color-invert the screen in-place. Used right after the space scene
        renders to flip black space into white and white sprites into black."""
        self._invert_surface.fill((255, 255, 255))
        self._invert_surface.blit(
            self.screen, (0, 0), special_flags=pygame.BLEND_RGB_SUB)
        self.screen.blit(self._invert_surface, (0, 0))

    def _autosave(self, docked_planet=None):
        """Persist the current player + known-planet state to the current slot.
        No-op when no slot is associated yet (player hasn't picked one via
        Continue or manual Save) — first save is always explicit."""
        if self.player is None or self.player.is_dead():
            return
        if self.current_slot is None:
            return
        savemod.save_game(
            self.player,
            self.player.known_planets.values(),
            slot=self.current_slot,
            docked_planet=docked_planet,
        )

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
        self._flip()

    def _draw_death(self):
        """Draw death screen with cause + checkpoint countdown."""
        self.screen.fill(cfg.BLACK)
        death_text = self.font_huge.render("YOU DIED", True, cfg.WHITE)
        self.screen.blit(death_text, (
            cfg.SCREEN_WIDTH // 2 - death_text.get_width() // 2,
            cfg.SCREEN_HEIGHT // 2 - death_text.get_height() // 2 - 30,
        ))

        cause = getattr(self.player, "last_damage_cause", None) if self.player else None
        if cause:
            cause_text = self.font_medium.render(
                f"Cause of death: {cause}", True, cfg.WHITE)
            self.screen.blit(cause_text, (
                cfg.SCREEN_WIDTH // 2 - cause_text.get_width() // 2,
                cfg.SCREEN_HEIGHT // 2 + 20,
            ))

        respawn_slot = self.current_slot if (
            self.current_slot is not None and savemod.has_save(self.current_slot)
        ) else savemod.most_recent_slot()
        if respawn_slot is not None:
            line = f"Respawning at slot {respawn_slot} in {int(max(0, self.death_timer))}..."
        else:
            line = f"Returning to menu in {int(max(0, self.death_timer))}..."
        restart_text = self.font_medium.render(line, True, cfg.WHITE)
        self.screen.blit(restart_text, (
            cfg.SCREEN_WIDTH // 2 - restart_text.get_width() // 2,
            cfg.SCREEN_HEIGHT // 2 + 60,
        ))
        self._flip()


if __name__ == "__main__":
    game = Game()
    game.run()
