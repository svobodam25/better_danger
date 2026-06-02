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

    NEW = "new"
    CONTINUE = "continue"
    EXIT = "exit"

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
            (self.NEW,      "NEW GAME"),
            (self.CONTINUE, "CONTINUE"),
            (self.EXIT,     "EXIT"),
        ]
        self.buttons = []
        for i, (action, label) in enumerate(self.items):
            x = cx - bw // 2
            y = cy - bh // 2 + i * (bh + gap)
            self.buttons.append(MenuButton(label, x, y, bw, bh, font_large, action=action))

        self.selected_idx = 0
        self._refresh_save_state()

    def _refresh_save_state(self):
        self.has_save = savemod.has_save()
        if not self.has_save and self.items[self.selected_idx][0] == self.CONTINUE:
            self.selected_idx = 0

    def reset(self):
        """Re-check disk state and reset selection when re-entering the menu."""
        self._refresh_save_state()

    def _is_enabled(self, action):
        return not (action == self.CONTINUE and not self.has_save)

    def handle_input(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_w, pygame.K_UP):
                self.selected_idx = self._move(-1)
            elif event.key in (pygame.K_s, pygame.K_DOWN):
                self.selected_idx = self._move(1)
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                action = self.items[self.selected_idx][0]
                if self._is_enabled(action):
                    return action
            elif event.key == pygame.K_ESCAPE:
                return self.EXIT
        elif event.type == pygame.MOUSEMOTION:
            for i, btn in enumerate(self.buttons):
                if btn.rect.collidepoint(event.pos) and self._is_enabled(self.items[i][0]):
                    self.selected_idx = i
                    break
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, btn in enumerate(self.buttons):
                if btn.rect.collidepoint(event.pos):
                    action = self.items[i][0]
                    if self._is_enabled(action):
                        self.selected_idx = i
                        return action
        return None

    def _move(self, delta):
        n = len(self.items)
        idx = self.selected_idx
        for _ in range(n):
            idx = (idx + delta) % n
            if self._is_enabled(self.items[idx][0]):
                return idx
        return self.selected_idx

    def draw(self, screen):
        screen.fill(cfg.BLACK)

        title = self.font_huge.render("BETTER DANGER", True, cfg.WHITE)
        screen.blit(title, (
            cfg.SCREEN_WIDTH // 2 - title.get_width() // 2,
            cfg.SCREEN_HEIGHT // 4 - title.get_height() // 2,
        ))
        sub = self.font_small.render("Monochrome space trading", True, cfg.WHITE)
        screen.blit(sub, (
            cfg.SCREEN_WIDTH // 2 - sub.get_width() // 2,
            cfg.SCREEN_HEIGHT // 4 + title.get_height() // 2 + 6,
        ))

        for i, btn in enumerate(self.buttons):
            action = self.items[i][0]
            btn.selected = (i == self.selected_idx)
            if not self._is_enabled(action):
                # Disabled button — draw dim outline only
                pygame.draw.rect(screen, cfg.WHITE, btn.rect, 1)
                text_surf = self.font_large.render(btn.text + "  (no save)", True, cfg.WHITE)
                tx = btn.rect.x + (btn.rect.w - text_surf.get_width()) // 2
                ty = btn.rect.y + (btn.rect.h - text_surf.get_height()) // 2
                # Striped overlay to convey "disabled"
                screen.blit(text_surf, (tx, ty))
                for y in range(btn.rect.y, btn.rect.y + btn.rect.h, 4):
                    pygame.draw.line(screen, cfg.BLACK,
                                     (btn.rect.x, y), (btn.rect.x + btn.rect.w, y), 1)
                pygame.draw.rect(screen, cfg.WHITE, btn.rect, 1)
            else:
                btn.draw(screen)

        hint = self.font_small.render(
            "W/S or mouse to move  ENTER to select  ESC to exit",
            True, cfg.WHITE)
        screen.blit(hint, (
            cfg.SCREEN_WIDTH // 2 - hint.get_width() // 2,
            cfg.SCREEN_HEIGHT - 40,
        ))


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
