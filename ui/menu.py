import time
import pygame
import settings as cfg
from utils import save as savemod


class MenuButton:
    """A simple menu button (text-based)."""

    def __init__(self, text, x, y, w, h, font, action=None):
        self.text = text
        self.rect = pygame.Rect(x, y, w, h)
        self.font = font
        self.action = action
        self.hovered = False
        self.selected = False

    def update(self, mouse_pos):
        self.hovered = self.rect.collidepoint(mouse_pos)

    def draw(self, screen):
        color = cfg.WHITE
        if self.selected:
            # Draw filled
            pygame.draw.rect(screen, color, self.rect)
            text_color = cfg.BLACK
        elif self.hovered:
            pygame.draw.rect(screen, color, self.rect, 2)
            text_color = color
        else:
            pygame.draw.rect(screen, color, self.rect, 1)
            text_color = color

        text_surf = self.font.render(self.text, True, text_color)
        screen.blit(text_surf, (
            self.rect.x + (self.rect.w - text_surf.get_width()) // 2,
            self.rect.y + (self.rect.h - text_surf.get_height()) // 2,
        ))


class TextInput:
    """Simple text input for quantity entry."""

    def __init__(self, x, y, w, h, font):
        self.rect = pygame.Rect(x, y, w, h)
        self.font = font
        self.text = ""
        self.active = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.active = self.rect.collidepoint(event.pos)
        elif event.type == pygame.KEYDOWN and self.active:
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.active = False
                return self.get_value()
            elif event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            elif event.unicode.isdigit():
                self.text += event.unicode
        return None

    def get_value(self):
        try:
            return int(self.text) if self.text else 0
        except ValueError:
            return 0

    def draw(self, screen):
        color = cfg.WHITE
        width = 2 if self.active else 1
        pygame.draw.rect(screen, color, self.rect, width)
        display_text = self.text + ("_" if self.active else "")
        text_surf = self.font.render(display_text, True, color)
        screen.blit(text_surf, (
            self.rect.x + 5,
            self.rect.y + (self.rect.h - text_surf.get_height()) // 2,
        ))


class MainMenu:
    """Title-screen menu with NEW GAME / CONTINUE / EXIT.
    CONTINUE is disabled when no save file is present."""

    PLAY = "play"
    SETTINGS = "settings"
    EXIT = "exit"
    BACK = "back"   # ESC — return to running game if one exists, otherwise ignored

    def __init__(self, font_small, font_medium, font_large, font_huge):
        self.font_small = font_small
        self.font_medium = font_medium
        self.font_large = font_large
        self.font_huge = font_huge

        cx = cfg.SCREEN_WIDTH // 2
        cy = cfg.SCREEN_HEIGHT // 2
        bw, bh = 320, 56
        gap = 18

        self.items = [
            (self.PLAY,     "PLAY"),
            (self.SETTINGS, "SETTINGS"),
            (self.EXIT,     "EXIT"),
        ]
        # Centre the whole stack so adding more items doesn't drift it off-centre
        total_h = len(self.items) * bh + (len(self.items) - 1) * gap
        start_y = cy - total_h // 2
        self.buttons = []
        for i, (action, label) in enumerate(self.items):
            x = cx - bw // 2
            y = start_y + i * (bh + gap)
            self.buttons.append(MenuButton(label, x, y, bw, bh, font_large, action=action))

        self.selected_idx = 0

    def reset(self):
        """Kept for compatibility — nothing to refresh now that PLAY routes
        unconditionally through the slot picker."""
        pass

    def handle_input(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_w, pygame.K_UP):
                self.selected_idx = (self.selected_idx - 1) % len(self.items)
            elif event.key in (pygame.K_s, pygame.K_DOWN):
                self.selected_idx = (self.selected_idx + 1) % len(self.items)
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                return self.items[self.selected_idx][0]
            elif event.key == pygame.K_ESCAPE:
                # Treat ESC as "go back" — the Game decides whether that means
                # resume a running session or just stay put. Never quit on ESC.
                return self.BACK
        elif event.type == pygame.MOUSEMOTION:
            for i, btn in enumerate(self.buttons):
                if btn.rect.collidepoint(event.pos):
                    self.selected_idx = i
                    break
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, btn in enumerate(self.buttons):
                if btn.rect.collidepoint(event.pos):
                    self.selected_idx = i
                    return self.items[i][0]
        return None

    def draw(self, screen):
        screen.fill(cfg.BLACK)

        title = self.font_huge.render("BETTER DANGER", True, cfg.WHITE)
        screen.blit(title, (
            cfg.SCREEN_WIDTH // 2 - title.get_width() // 2,
            cfg.SCREEN_HEIGHT // 4 - title.get_height() // 2,
        ))

        for i, btn in enumerate(self.buttons):
            btn.selected = (i == self.selected_idx)
            btn.draw(screen)

        hint = self.font_small.render(
            "W/S or mouse to move  ENTER to select  ESC to exit",
            True, cfg.WHITE)
        screen.blit(hint, (
            cfg.SCREEN_WIDTH // 2 - hint.get_width() // 2,
            cfg.SCREEN_HEIGHT - 40,
        ))


class SettingsScreen:
    """Settings overlay. Currently holds the Moon ↔ Sun theme slider
    (controls whether the space scene renders inverted)."""

    BACK = "back"

    def __init__(self, font_small, font_medium, font_large, font_huge,
                 get_invert, set_invert):
        self.font_small = font_small
        self.font_medium = font_medium
        self.font_large = font_large
        self.font_huge = font_huge
        self.get_invert = get_invert
        self.set_invert = set_invert

        # Slider geometry — horizontal track centred on screen
        cx = cfg.SCREEN_WIDTH // 2
        cy = cfg.SCREEN_HEIGHT // 2
        self.track_w = 400
        self.track_h = 6
        self.track_rect = pygame.Rect(
            cx - self.track_w // 2, cy, self.track_w, self.track_h)
        # Glyph + label rects on the left/right side of the track, used as
        # additional click targets so users can snap by clicking the icon.
        self.left_rect = pygame.Rect(cx - self.track_w // 2 - 80,
                                     cy - 40, 64, 80)
        self.right_rect = pygame.Rect(cx + self.track_w // 2 + 16,
                                      cy - 40, 64, 80)
        self.handle_radius = 14
        self._dragging = False

    def _value(self):
        return 1.0 if self.get_invert() else 0.0

    def _handle_pos(self):
        v = self._value()
        x = self.track_rect.left + int(v * self.track_w)
        y = self.track_rect.centery
        return (x, y)

    def _handle_rect(self):
        x, y = self._handle_pos()
        r = self.handle_radius
        return pygame.Rect(x - r, y - r, r * 2, r * 2)

    def _snap_from_x(self, mouse_x):
        # Anything past midpoint counts as the bright (sun, inverted) side.
        mid = self.track_rect.centerx
        self.set_invert(mouse_x > mid)

    def handle_input(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return self.BACK
            if event.key in (pygame.K_a, pygame.K_LEFT):
                self.set_invert(False)
            elif event.key in (pygame.K_d, pygame.K_RIGHT):
                self.set_invert(True)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._handle_rect().inflate(12, 12).collidepoint(event.pos):
                self._dragging = True
            elif self.track_rect.inflate(0, 24).collidepoint(event.pos):
                self._snap_from_x(event.pos[0])
            elif self.left_rect.collidepoint(event.pos):
                self.set_invert(False)
            elif self.right_rect.collidepoint(event.pos):
                self.set_invert(True)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._dragging = False
        elif event.type == pygame.MOUSEMOTION and self._dragging:
            self._snap_from_x(event.pos[0])
        return None

    def _draw_moon(self, screen, cx, cy, r):
        # Crescent moon: a filled circle with a black circle offset to bite
        # out the right side.
        pygame.draw.circle(screen, cfg.WHITE, (cx, cy), r, 0)
        pygame.draw.circle(screen, cfg.BLACK, (cx + r // 2, cy), r, 0)
        # Re-outline so the unbiased silhouette stays readable
        pygame.draw.circle(screen, cfg.WHITE, (cx, cy), r, 1)

    def _draw_sun(self, screen, cx, cy, r):
        # Sun: ring + 8 short rays
        pygame.draw.circle(screen, cfg.WHITE, (cx, cy), r, 2)
        import math
        for i in range(8):
            a = i * (math.pi / 4)
            x1 = cx + int(math.cos(a) * (r + 4))
            y1 = cy + int(math.sin(a) * (r + 4))
            x2 = cx + int(math.cos(a) * (r + 12))
            y2 = cy + int(math.sin(a) * (r + 12))
            pygame.draw.line(screen, cfg.WHITE, (x1, y1), (x2, y2), 2)

    def draw(self, screen):
        screen.fill(cfg.BLACK)

        title = self.font_huge.render("SETTINGS", True, cfg.WHITE)
        screen.blit(title, (cfg.SCREEN_WIDTH // 2 - title.get_width() // 2, 80))

        label = self.font_medium.render("Space theme", True, cfg.WHITE)
        screen.blit(label, (cfg.SCREEN_WIDTH // 2 - label.get_width() // 2,
                            self.track_rect.top - 80))

        # Track
        pygame.draw.rect(screen, cfg.WHITE, self.track_rect, 1)

        # Moon / Sun glyphs
        self._draw_moon(screen, self.left_rect.centerx, self.left_rect.centery, 18)
        self._draw_sun(screen, self.right_rect.centerx, self.right_rect.centery, 14)

        # Captions under the glyphs
        cap_left = self.font_small.render("MOON", True, cfg.WHITE)
        cap_right = self.font_small.render("SUN", True, cfg.WHITE)
        screen.blit(cap_left, (self.left_rect.centerx - cap_left.get_width() // 2,
                               self.left_rect.bottom + 4))
        screen.blit(cap_right, (self.right_rect.centerx - cap_right.get_width() // 2,
                                self.right_rect.bottom + 4))

        # Handle
        hx, hy = self._handle_pos()
        pygame.draw.circle(screen, cfg.WHITE, (hx, hy), self.handle_radius, 0)

        # Current mode caption below the slider
        mode = "SUN — bright space (inverted)" if self.get_invert() else "MOON — dark space (default)"
        cap = self.font_small.render(mode, True, cfg.WHITE)
        screen.blit(cap, (cfg.SCREEN_WIDTH // 2 - cap.get_width() // 2,
                          self.track_rect.bottom + 40))

        hint = self.font_small.render(
            "Click slider or icons  A/D to switch  ESC to go back",
            True, cfg.WHITE)
        screen.blit(hint, (cfg.SCREEN_WIDTH // 2 - hint.get_width() // 2,
                           cfg.SCREEN_HEIGHT - 40))


class SaveSlotPicker:
    """Modal slot picker. Modes:
      LOAD — only filled slots clickable (used for resumes outside the main menu).
      SAVE — every slot clickable; filled slots flagged OVERWRITE.
      PLAY — every slot clickable; filled = continue, empty = '+ NEW GAME'.
    Inputs return None, ('cancel',), or ('select', slot_int)."""

    LOAD = "load"
    SAVE = "save"
    PLAY = "play"

    DEFAULT_TITLES = {
        LOAD: "LOAD GAME",
        SAVE: "SAVE GAME",
        PLAY: "PLAY",
    }

    def __init__(self, mode, font_small, font_medium, font_large, font_huge, title=None):
        self.mode = mode
        self.title = title or self.DEFAULT_TITLES.get(mode, "SELECT SLOT")
        self.font_small = font_small
        self.font_medium = font_medium
        self.font_large = font_large
        self.font_huge = font_huge

        self.slots = []          # list of (slot_num, summary or None)
        self.row_rects = []      # pygame.Rect per row, populated by refresh()
        self.selected_idx = 0
        self.refresh()

    def refresh(self):
        self.slots = savemod.list_saves()

        n = len(self.slots)
        row_h = 64
        row_w = 720
        gap = 8
        total_h = n * row_h + (n - 1) * gap
        start_y = (cfg.SCREEN_HEIGHT - total_h) // 2
        start_x = (cfg.SCREEN_WIDTH - row_w) // 2

        self.row_rects = []
        for i in range(n):
            rect = pygame.Rect(start_x, start_y + i * (row_h + gap), row_w, row_h)
            self.row_rects.append(rect)

        # Default selection: first enabled slot
        for i, (_, info) in enumerate(self.slots):
            if self._is_enabled(info):
                self.selected_idx = i
                break

    def _is_enabled(self, info):
        if self.mode == self.LOAD:
            return info is not None
        return True  # SAVE and PLAY allow any slot

    def _move(self, delta):
        n = len(self.slots)
        idx = self.selected_idx
        for _ in range(n):
            idx = (idx + delta) % n
            if self._is_enabled(self.slots[idx][1]):
                return idx
        return self.selected_idx

    def handle_input(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return ("cancel",)
            if event.key in (pygame.K_w, pygame.K_UP):
                self.selected_idx = self._move(-1)
            elif event.key in (pygame.K_s, pygame.K_DOWN):
                self.selected_idx = self._move(1)
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                slot, info = self.slots[self.selected_idx]
                if self._is_enabled(info):
                    return ("select", slot)
            else:
                # Number keys 1..N pick slot directly
                for i in range(len(self.slots)):
                    key = getattr(pygame, f"K_{i + 1}", None)
                    if key is not None and event.key == key:
                        slot, info = self.slots[i]
                        if self._is_enabled(info):
                            self.selected_idx = i
                            return ("select", slot)
        elif event.type == pygame.MOUSEMOTION:
            for i, rect in enumerate(self.row_rects):
                if rect.collidepoint(event.pos) and self._is_enabled(self.slots[i][1]):
                    self.selected_idx = i
                    break
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, rect in enumerate(self.row_rects):
                if rect.collidepoint(event.pos):
                    slot, info = self.slots[i]
                    if self._is_enabled(info):
                        self.selected_idx = i
                        return ("select", slot)
        return None

    @staticmethod
    def _fmt_age(saved_at):
        if not saved_at:
            return ""
        delta = max(0, time.time() - saved_at)
        if delta < 60:
            return "just now"
        if delta < 3600:
            return f"{int(delta // 60)} min ago"
        if delta < 86400:
            return f"{int(delta // 3600)} h ago"
        return f"{int(delta // 86400)} d ago"

    def draw(self, screen):
        screen.fill(cfg.BLACK)

        title = self.font_huge.render(self.title, True, cfg.WHITE)
        screen.blit(title, (cfg.SCREEN_WIDTH // 2 - title.get_width() // 2, 60))

        for i, (rect, (slot, info)) in enumerate(zip(self.row_rects, self.slots)):
            enabled = self._is_enabled(info)
            is_sel = (i == self.selected_idx)

            # Frame
            if is_sel and enabled:
                pygame.draw.rect(screen, cfg.WHITE, rect)
                fg = cfg.BLACK
            else:
                pygame.draw.rect(screen, cfg.WHITE, rect, 1)
                fg = cfg.WHITE

            slot_label = self.font_large.render(f"SLOT {slot}", True, fg)
            screen.blit(slot_label, (rect.x + 16, rect.y + (rect.h - slot_label.get_height()) // 2))

            if info is None:
                if self.mode == self.PLAY:
                    empty_text = "+ NEW GAME"
                else:
                    empty_text = "— EMPTY —"
                empty = self.font_medium.render(empty_text, True, fg)
                screen.blit(empty, (rect.x + 180,
                                    rect.y + (rect.h - empty.get_height()) // 2))
                if self.mode == self.SAVE:
                    hint = self.font_small.render("click to save here", True, fg)
                    screen.blit(hint, (rect.right - hint.get_width() - 16,
                                       rect.y + rect.h // 2 - hint.get_height() // 2))
            else:
                station = info.get("last_station") or "unknown"
                line1 = (f"{info.get('rank', '?')}  |  {info['credits']} cr  |  "
                         f"HP {info['hp']}/{info['max_hp']}  |  "
                         f"{info['known_planets']} planets")
                line2 = f"Last station: {station}   ({self._fmt_age(info.get('saved_at'))})"
                s1 = self.font_small.render(line1, True, fg)
                s2 = self.font_small.render(line2, True, fg)
                screen.blit(s1, (rect.x + 180, rect.y + 12))
                screen.blit(s2, (rect.x + 180, rect.y + 32))
                if self.mode == self.SAVE:
                    warn = self.font_small.render("OVERWRITE", True, fg)
                    screen.blit(warn, (rect.right - warn.get_width() - 16, rect.y + 6))
                elif self.mode == self.PLAY:
                    cont = self.font_small.render("CONTINUE", True, fg)
                    screen.blit(cont, (rect.right - cont.get_width() - 16, rect.y + 6))

            # Disabled overlay (LOAD on empty slot)
            if not enabled:
                for y in range(rect.y, rect.y + rect.h, 4):
                    pygame.draw.line(screen, cfg.BLACK,
                                     (rect.x, y), (rect.right, y), 1)
                pygame.draw.rect(screen, cfg.WHITE, rect, 1)

        hint = self.font_small.render(
            "W/S or mouse to move  1-5 quick pick  ENTER/click to confirm  ESC to cancel",
            True, cfg.WHITE)
        screen.blit(hint, (cfg.SCREEN_WIDTH // 2 - hint.get_width() // 2,
                           cfg.SCREEN_HEIGHT - 40))


class MessageBox:
    """A message overlay for confirmations and alerts."""

    def __init__(self, text, font, y_offset=0):
        self.text = text
        self.font = font
        self.timer = 2.0
        self.y_offset = y_offset

    def update(self, dt):
        self.timer -= dt
        return self.timer <= 0

    def draw(self, screen):
        if self.timer <= 0:
            return
        alpha = min(1.0, self.timer * 2)  # fade in last 0.5s
        surf = self.font.render(self.text, True, cfg.WHITE)
        x = (cfg.SCREEN_WIDTH - surf.get_width()) // 2
        y = cfg.SCREEN_HEIGHT // 2 + self.y_offset
        screen.blit(surf, (x, y))
