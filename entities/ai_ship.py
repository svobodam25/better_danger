import math
import random


class AIShip:
    """AI ship for the docking scene — sits parked in a slot."""

    def __init__(self, slot_x, slot_y, slot_w, slot_h):
        self.x = slot_x + slot_w / 2
        self.y = slot_y + slot_h / 2
        self.width = random.randint(30, 50)
        self.height = random.randint(12, 20)
        self.color = (255, 255, 255)  # outline only


class DepartingShip:
    """A ship that is leaving the hangar during docking."""

    def __init__(self, x, y, direction=1):
        self.x = float(x)
        self.y = float(y)
        self.width = 40
        self.height = 16
        self.vx = 80.0 * direction  # moving right (+) or left (-)
        self.vy = 0.0
        self.active = True

    def update(self, dt):
        self.x += self.vx * dt

    def off_screen(self, screen_w, screen_h):
        return (self.x < -100 or self.x > screen_w + 100 or
                self.y < -100 or self.y > screen_h + 100)
