import json
import pygame
import settings as cfg
from ui.menu import MenuButton, TextInput, MessageBox, SaveSlotPicker
from utils import save as savemod


class TradeScene:
    """Scene 3: Trading GUI after successful docking."""

    SECTIONS = ["BUY", "SELL", "MAPS", "UPGRADES", "REFUEL", "REPAIR", "SAVE"]

    def __init__(self, player, planet, font_small, font_medium, font_large, font_huge=None):
        self.player = player
        self.planet = planet
        self.font_small = font_small
        self.font_medium = font_medium
        self.font_large = font_large
        self.font_huge = font_huge or font_large
        self.current_section = 0
        self.scroll_offset = 0
        self.selected_item = 0
        self.message = None
        self.input_active = False
        self.quantity_input = None
        self.buy_mode = True  # True = buying, False = selling
        self._leave_requested = False

        # Track last LMB click for double-click → action on item rows.
        self._last_row_click_time = 0
        self._last_row_click_idx = -1

        # Slot picker overlay (opened via SAVE tab)
        self.slot_picker = None

        # Load map data
        import os
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(base_dir, "data", "items.json"), "r") as f:
            self.items_data = json.load(f)

    def handle_input(self, event):
        """Handle keyboard input for trade menu."""
        # Slot picker takes over input while open
        if self.slot_picker is not None:
            picked = self.slot_picker.handle_input(event)
            if picked is None:
                return None
            if picked[0] == "cancel":
                self.slot_picker = None
            elif picked[0] == "select":
                slot = picked[1]
                self._save_to_slot(slot)
                self.slot_picker = None
            return None

        if self.input_active and self.quantity_input:
            val = self.quantity_input.handle_event(event)
            if val is not None:
                self._process_transaction(val)
                self.input_active = False
                self.quantity_input = None
            return None

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._leave_requested = True
                return None
            elif event.key == pygame.K_TAB:
                self.current_section = (self.current_section + 1) % len(self.SECTIONS)
                self.scroll_offset = 0
                self.selected_item = 0
            elif event.key == pygame.K_UP:
                self.selected_item = max(0, self.selected_item - 1)
            elif event.key == pygame.K_DOWN:
                items = self._get_section_items()
                self.selected_item = min(len(items) - 1, self.selected_item + 1)
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self._handle_enter()
            elif event.key == pygame.K_w:
                self.selected_item = max(0, self.selected_item - 1)
            elif event.key == pygame.K_s:
                items = self._get_section_items()
                self.selected_item = min(len(items) - 1, self.selected_item + 1)
            elif event.key == pygame.K_1:
                self.current_section = 0
                self.selected_item = 0
            elif event.key == pygame.K_2:
                self.current_section = 1
                self.selected_item = 0
            elif event.key == pygame.K_3:
                self.current_section = 2
                self.selected_item = 0
            elif event.key == pygame.K_4:
                self.current_section = 3
                self.selected_item = 0
            elif event.key == pygame.K_5:
                self.current_section = 4
                self.selected_item = 0
            elif event.key == pygame.K_6:
                self.current_section = 5
                self.selected_item = 0
            elif event.key == pygame.K_7:
                self.current_section = 6
                self.selected_item = 0
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._handle_mouse_click(event.pos)

        return None

    def _handle_mouse_click(self, pos):
        """Mouse support: click tab to switch section, click row to select,
        double-click row to confirm (same as Enter)."""
        mx, my = pos

        # Tab strip — keep these dims in sync with draw()
        tab_y = 70
        tab_h = 28
        tab_w = cfg.SCREEN_WIDTH // len(self.SECTIONS)
        if tab_y <= my <= tab_y + tab_h:
            idx = mx // tab_w
            if 0 <= idx < len(self.SECTIONS):
                if idx != self.current_section:
                    self.current_section = int(idx)
                    self.scroll_offset = 0
                    self.selected_item = 0
                return

        # Item rows — match _draw_item_row hitbox
        content_y = 110
        row_h = 36
        items = self._get_section_items()
        if not items or mx < 40 or mx > cfg.SCREEN_WIDTH - 40:
            return
        rel = my - (content_y - 2)
        if rel < 0:
            return
        idx = rel // row_h
        if 0 <= idx < len(items):
            idx = int(idx)
            now = pygame.time.get_ticks()
            if (idx == self.selected_item
                    and idx == self._last_row_click_idx
                    and now - self._last_row_click_time < 350):
                # Double-click — perform the action
                self._handle_enter()
            else:
                self.selected_item = idx
            self._last_row_click_time = now
            self._last_row_click_idx = idx

    def _get_section_items(self):
        """Get list of items for the current section."""
        if self.current_section == 0:  # BUY
            return [(cid, cdata) for cid, cdata in cfg.COMMODITIES.items()]
        elif self.current_section == 1:  # SELL
            return [(cid, item) for cid, item in self.player.inventory.items()]
        elif self.current_section == 2:  # MAPS
            return [(mid, self.items_data["maps"][mid]) for mid in self.planet.maps_for_sale]
        elif self.current_section == 3:  # UPGRADES
            return [(uid, cfg.UPGRADES[uid]) for uid in self.planet.upgrades_available
                    if uid not in self.player.upgrades]
        elif self.current_section == 4:  # REFUEL
            return [("refuel", {"name": "Refuel", "cost": 1, "desc": "1 credit per fuel unit"})]
        elif self.current_section == 5:  # REPAIR
            return [("repair", {"name": "Repair", "cost": 2, "desc": "2 credits per HP"})]
        elif self.current_section == 6:  # SAVE
            return [("save", {"name": "Save Game",
                              "desc": "Persist current progress (only available at stations)"})]
        return []

    def _handle_enter(self):
        """Handle Enter key based on current section."""
        items = self._get_section_items()
        if not items or self.selected_item >= len(items):
            return

        if self.current_section == 0:  # BUY
            comm_id = items[self.selected_item][0]
            self.buy_mode = True
            self._start_quantity_input(comm_id)
        elif self.current_section == 1:  # SELL
            comm_id = items[self.selected_item][0]
            self.buy_mode = False
            self._start_quantity_input(comm_id)
        elif self.current_section == 2:  # MAPS
            self._buy_map(items[self.selected_item][0])
        elif self.current_section == 3:  # UPGRADES
            self._buy_upgrade(items[self.selected_item][0])
        elif self.current_section == 4:  # REFUEL
            self._start_quantity_input("refuel")
        elif self.current_section == 5:  # REPAIR
            self._start_quantity_input("repair")
        elif self.current_section == 6:  # SAVE
            self._open_save_picker()

    def _open_save_picker(self):
        self.slot_picker = SaveSlotPicker(
            SaveSlotPicker.SAVE,
            self.font_small, self.font_medium, self.font_large, self.font_huge,
            title="SAVE TO SLOT")

    def _save_to_slot(self, slot):
        ok = savemod.save_game(
            self.player,
            self.player.known_planets.values(),
            slot=slot,
            docked_planet=self.planet,
        )
        if ok:
            # Stash slot on the player so the Game loop can adopt it as current.
            self.player.last_saved_slot = slot
            self.message = MessageBox(f"Saved to slot {slot}.", self.font_medium)
        else:
            self.message = MessageBox("Save failed!", self.font_medium)

    def _start_quantity_input(self, item_id):
        self.input_active = True
        self.quantity_input = TextInput(
            cfg.SCREEN_WIDTH // 2 - 100, cfg.SCREEN_HEIGHT // 2 + 100, 200, 30, self.font_medium)
        self.quantity_input.active = True
        self.pending_item = item_id

    def _process_transaction(self, quantity):
        if quantity <= 0:
            return

        if self.pending_item == "refuel":
            needed = int(self.player.max_fuel - self.player.fuel)
            amount = min(quantity, needed)
            if self.player.refuel(amount):
                self.message = MessageBox(f"Refueled +{amount} fuel", self.font_medium)
            else:
                self.message = MessageBox("Not enough credits!", self.font_medium)
        elif self.pending_item == "repair":
            needed = int(self.player.max_hp - self.player.hp)
            amount = min(quantity, needed)
            if self.player.repair(amount):
                self.message = MessageBox(f"Repaired +{amount} HP", self.font_medium)
            else:
                self.message = MessageBox("Not enough credits!", self.font_medium)
        elif self.buy_mode:
            price = self.planet.buy_price(self.pending_item)
            max_qty = min(
                quantity,
                self.player.credits // price if price > 0 else 0,
                self.planet.stock.get(self.pending_item, 0),
            )
            # Also limit by cargo
            weight = cfg.COMMODITIES[self.pending_item]["weight"]
            cargo_free = self.player.cargo_free()
            max_by_cargo = cargo_free // weight if weight > 0 else 0
            max_qty = min(max_qty, max_by_cargo)

            if max_qty <= 0:
                self.message = MessageBox("Cannot buy! (credits/cargo/stock)", self.font_medium)
                return

            if self.player.buy(self.pending_item, max_qty, price):
                self.planet.remove_stock(self.pending_item, max_qty)
                name = cfg.COMMODITIES[self.pending_item]["name"]
                self.message = MessageBox(f"Bought {max_qty}x {name} @ {price}cr", self.font_medium)
        else:  # SELL
            price = self.planet.sell_price(self.pending_item)
            owned = self.player.inventory.get(self.pending_item, {}).get("qty", 0)
            amount = min(quantity, owned)
            if amount <= 0:
                self.message = MessageBox("Nothing to sell!", self.font_medium)
                return
            if self.player.sell(self.pending_item, amount, price):
                self.planet.add_stock(self.pending_item, amount)
                name = cfg.COMMODITIES[self.pending_item]["name"]
                self.message = MessageBox(f"Sold {amount}x {name} @ {price}cr", self.font_medium)

    def _buy_map(self, map_id):
        map_data = self.items_data["maps"][map_id]
        if self.player.credits < map_data["cost"]:
            self.message = MessageBox("Not enough credits!", self.font_medium)
            return
        self.player.credits -= map_data["cost"]
        # Reveal nearby undiscovered planets — handled by space scene
        self.message = MessageBox(f"Bought {map_data['name']}!", self.font_medium)
        # Store revealed count for space scene to use
        self.player._pending_reveals = map_data["reveals"]

    def _buy_upgrade(self, upgrade_id):
        if upgrade_id in self.player.upgrades:
            self.message = MessageBox("Already installed!", self.font_medium)
            return
        prereq = cfg.UPGRADE_PREREQUISITES.get(upgrade_id)
        if prereq and prereq not in self.player.upgrades:
            req_name = cfg.UPGRADES[prereq]["name"]
            self.message = MessageBox(f"Locked — install {req_name} first", self.font_medium)
            return
        cost = cfg.UPGRADES[upgrade_id]["cost"]
        if self.player.credits < cost:
            self.message = MessageBox("Not enough credits!", self.font_medium)
            return
        if self.player.apply_upgrade(upgrade_id):
            name = cfg.UPGRADES[upgrade_id]["name"]
            self.message = MessageBox(f"Installed: {name}!", self.font_medium)

    def update(self, dt):
        if self._leave_requested:
            return "leave"
        if self.message:
            if self.message.update(dt):
                self.message = None

    def draw(self, screen):
        """Render the trade scene."""
        # Slot picker overlay takes over the whole screen
        if self.slot_picker is not None:
            self.slot_picker.draw(screen)
            return

        screen.fill(cfg.BLACK)
        color = cfg.WHITE

        # Header
        header = self.font_large.render(f"TRADE — {self.planet.name} ({self.planet.planet_type})", True, color)
        screen.blit(header, (cfg.SCREEN_WIDTH // 2 - header.get_width() // 2, 10))

        # Credits
        cred_text = self.font_medium.render(f"Credits: {self.player.credits}  |  "
                                            f"Cargo: {self.player.cargo_used()}/{self.player.max_cargo}  |  "
                                            f"Fuel: {int(self.player.fuel)}/{int(self.player.max_fuel)}  |  "
                                            f"HP: {int(self.player.hp)}/{int(self.player.max_hp)}", True, color)
        screen.blit(cred_text, (cfg.SCREEN_WIDTH // 2 - cred_text.get_width() // 2, 45))

        # Section tabs
        tab_y = 70
        tab_w = cfg.SCREEN_WIDTH // len(self.SECTIONS)
        for i, section in enumerate(self.SECTIONS):
            tab_x = i * tab_w
            rect = pygame.Rect(tab_x, tab_y, tab_w - 2, 28)
            if i == self.current_section:
                pygame.draw.rect(screen, color, rect)
                text_color = cfg.BLACK
            else:
                pygame.draw.rect(screen, color, rect, 1)
                text_color = color
            tab_text = self.font_small.render(f"{i + 1}. {section}", True, text_color)
            screen.blit(tab_text, (tab_x + (tab_w - tab_text.get_width()) // 2, tab_y + 4))

        # Section content
        content_y = 110
        items = self._get_section_items()

        if not items:
            no_items = self.font_medium.render("Nothing available", True, color)
            screen.blit(no_items, (cfg.SCREEN_WIDTH // 2 - no_items.get_width() // 2, content_y + 50))
        else:
            for i, (item_id, item_data) in enumerate(items):
                y = content_y + i * 36
                if y > cfg.SCREEN_HEIGHT - 80:
                    break

                is_selected = (i == self.selected_item)

                if self.current_section == 0:  # BUY
                    comm = cfg.COMMODITIES[item_id]
                    buy_p = self.planet.buy_price(item_id)
                    stock = self.planet.stock.get(item_id, 0)
                    text = f"{comm['name']:<16} Buy: {buy_p:>4} cr  Stock: {stock:>4}  Wt: {comm['weight']}"
                    self._draw_item_row(screen, y, text, is_selected, color)
                elif self.current_section == 1:  # SELL
                    comm = cfg.COMMODITIES[item_id]
                    qty = item_data["qty"]
                    buy_p = item_data["buy_price"]
                    sell_p = self.planet.sell_price(item_id)
                    profit = sell_p - buy_p
                    sign = "+" if profit >= 0 else ""
                    text = (f"{comm['name']:<16} Qty: {qty:>3}  Bought@: {buy_p:>4}  "
                            f"Sell@: {sell_p:>4}  {sign}{profit}cr/ea")
                    self._draw_item_row(screen, y, text, is_selected, color)
                elif self.current_section == 2:  # MAPS
                    text = f"{item_data['name']:<24} Cost: {item_data['cost']:>5} cr  {item_data['desc']}"
                    self._draw_item_row(screen, y, text, is_selected, color)
                elif self.current_section == 3:  # UPGRADES
                    installed = item_id in self.player.upgrades
                    prereq = cfg.UPGRADE_PREREQUISITES.get(item_id)
                    if installed:
                        status = "[INSTALLED]"
                    elif prereq and prereq not in self.player.upgrades:
                        status = f"[LOCKED — needs {cfg.UPGRADES[prereq]['name']}]"
                    else:
                        status = ""
                    text = f"{item_data['name']:<20} Cost: {item_data['cost']:>5} cr  {item_data['desc']} {status}"
                    self._draw_item_row(screen, y, text, is_selected, color)
                elif self.current_section == 4:  # REFUEL
                    needed = max(0, int(self.player.max_fuel - self.player.fuel))
                    text = f"Refuel Ship — 1 cr per unit  |  Need: {needed}  |  Cost: {needed} cr"
                    self._draw_item_row(screen, y, text, is_selected, color)
                elif self.current_section == 5:  # REPAIR
                    needed = max(0, int(self.player.max_hp - self.player.hp))
                    text = f"Repair Ship — 2 cr per HP  |  Need: {needed} HP  |  Cost: {needed * 2} cr"
                    self._draw_item_row(screen, y, text, is_selected, color)
                elif self.current_section == 6:  # SAVE
                    text = f"{item_data['name']:<24} {item_data['desc']}"
                    self._draw_item_row(screen, y, text, is_selected, color)

        # Help text
        help_y = cfg.SCREEN_HEIGHT - 40
        help_text = self.font_small.render(
            "TAB/click tab:Switch  1-7:Quick  UP/DOWN/click:Navigate  ENTER/dbl-click:Action  ESC:Leave",
            True, color)
        screen.blit(help_text, (cfg.SCREEN_WIDTH // 2 - help_text.get_width() // 2, help_y))

        # Quantity input
        if self.input_active and self.quantity_input:
            prompt = self.font_medium.render("Enter quantity:", True, color)
            screen.blit(prompt, (cfg.SCREEN_WIDTH // 2 - prompt.get_width() // 2,
                                 cfg.SCREEN_HEIGHT // 2 + 70))
            self.quantity_input.draw(screen)

        # Message
        if self.message:
            self.message.draw(screen)

    def _draw_item_row(self, screen, y, text, selected, color):
        """Draw a single selectable item row."""
        if selected:
            # Highlight background
            highlight = pygame.Rect(40, y - 2, cfg.SCREEN_WIDTH - 80, 30)
            pygame.draw.rect(screen, color, highlight, 1)
            prefix = "> "
        else:
            prefix = "  "
        surf = self.font_small.render(prefix + text, True, color)
        screen.blit(surf, (50, y + 2))
