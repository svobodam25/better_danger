# Better Danger — Herní Design Prompt (Speedrun Edition)

> **Elite Danger, jenže lepší — sandbox, cíl: max vylepšení lodě.**
> Černobílá 2D vesmírná hra o obchodování, průzkumu a přežití.
> **Technologie:** Python + Pygame
> **Barevná paleta:** POUZE černá a bílá (monochrome, 1-bit styl)

---

## 🎯 Cíl hry

**Sandbox** — žádná vítězná obrazovka. Cílem je získat všechny upgrady lodi a mít nejlepší vybavení. Hráč sám rozhodne, kdy "dohrál".

---

## 🚀 Přehled hry

Hráč je pilot vesmírné lodi v **nekonečném procedurálně generovaném vesmíru**. Cílem je vydělávat peníze obchodováním — nakupovat levně na jedné planetě a prodávat draze na druhé. K navigaci potřebuje mapy, které si musí koupit. Vesmír má realistickou newtonovskou fyziku (žádný odpor, kontinuální akcelerace).

### Vlastnosti:
- **Nekonečný vesmír** — planety jsou procedurálně generované na gridu (rozestup ~600 px)
- **Krátké vzdálenosti mezi planetami** — cestování je rychlé, zisky mírné
- **7 komodit**, 5 typů planet, 6 upgradů lodě
- **Hyperpohon** — warp skok na velkou vzdálenost
- Není vítězná podmínka — hráč hraje dokud chce

---

## 🎬 Scéna 1 — Cestování vesmírem (TOP-DOWN)

### Fyzika (Newtonovská mechanika)
- Žádný odpor/tření, loď si udržuje rychlost
- Rotace nezávisle na směru pohybu
- Rychlost omezena na 500 px/s (soft cap)

### Ovládání
| Klávesa | Akce |
|---------|------|
| `A` / `D` | Rotace lodi |
| `W` | Tah motorů |
| `S` | Brzdné trysky (po upgradu) |
| `J` | Hyperpohon (warp) |
| `M` | Mapa |
| `Esc` | Pauza |

### HUD
- Rychlost, palivo, HP, kredity, souřadnice, čas, cargo

---

## 🛬 Scéna 2 — Dokování (SIDE-VIEW)

- 3 parkovací sloty, 1–2 obsazené AI loděmi
- Náhodný cílový slot (bliká)
- Možné kolize se zdmi, AI loděmi, odlétající lodí
- Špatný slot → 5s varování → zničení

---

## 🛒 Scéna 3 — Obchod (GUI Menu)

### Sekce
1. **BUY** — nákup komodit z planety
2. **SELL** — prodej komodit s přehledem zisku/ztráty
3. **MAPS** — nákup map (odhalí blízké planety)
4. **UPGRADES** — vylepšení lodi
5. **REFUEL** — doplnění paliva (1 Kč/jednotka)
6. **REPAIR** — oprava lodi (2 Kč/HP)
