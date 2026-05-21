import pygame
import settings as cfg


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
