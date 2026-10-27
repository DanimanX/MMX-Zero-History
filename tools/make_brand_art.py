#!/usr/bin/env python3
"""Generate MMX Zero History brand art (original, repo-owned).

Everything here is drawn from primitives: gradients, grids, capsule pods and
typography. No game sprite, logo or ROM-derived pixel is used, so the output
is safe to commit and to publish.

    python3 tools/make_brand_art.py

Outputs land in docs/img/.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "img"

FONT_BOLD = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
FONT_REG = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
FONT_MONO = "/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf"

BG_TOP = (8, 12, 24)
BG_BOT = (18, 10, 28)
CYAN = (86, 232, 255)
AMBER = (255, 176, 64)
RED = (255, 92, 92)
VIOLET = (168, 138, 255)
GREY = (150, 162, 180)
WHITE = (238, 244, 255)


def font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size)


def vertical_gradient(size: tuple[int, int], top: tuple[int, int, int],
                      bottom: tuple[int, int, int]) -> Image.Image:
    w, h = size
    strip = Image.new("RGB", (1, h))
    px = strip.load()
    for y in range(h):
        t = y / max(1, h - 1)
        px[0, y] = tuple(round(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
    return strip.resize((w, h), Image.BILINEAR).convert("RGBA")


def translucent(img: Image.Image, draw_fn, blur: float = 0.0) -> None:
    """Draw shapes with alpha on a scratch layer, then composite for real.

    ImageDraw writes raw pixels, so an (r, g, b, 8) fill would *replace* the
    canvas instead of blending with it. Every translucent shape goes through
    here instead.
    """
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw_fn(ImageDraw.Draw(layer))
    if blur:
        layer = layer.filter(ImageFilter.GaussianBlur(blur))
    img.alpha_composite(layer)


def circuit_grid(base: Image.Image, step: int = 40) -> None:
    def grid(d: ImageDraw.ImageDraw) -> None:
        w, h = base.size
        for x in range(0, w, step):
            d.line([(x, 0), (x, h)], fill=(90, 190, 230, 26), width=1)
        for y in range(0, h, step):
            d.line([(0, y), (w, y)], fill=(90, 190, 230, 26), width=1)
        # A few brighter traces so the grid does not read as graph paper.
        d.line([(0, h * 0.72), (w * 0.35, h * 0.72), (w * 0.42, h * 0.55),
                (w, h * 0.55)], fill=(86, 232, 255, 62), width=2)
        d.line([(0, h * 0.28), (w * 0.22, h * 0.28), (w * 0.30, h * 0.14),
                (w, h * 0.14)], fill=(255, 176, 64, 46), width=2)

    translucent(base, grid)


def capsule(img: Image.Image, cx: int, cy: int, w: int, h: int,
            accent: tuple[int, int, int], label: str = "") -> None:
    """A stasis pod: rounded body, waist band, hatch light."""
    body = [cx - w // 2, cy - h // 2, cx + w // 2, cy + h // 2]
    band = max(6, h // 9)

    def fills(d: ImageDraw.ImageDraw) -> None:
        d.rounded_rectangle(body, radius=w // 3, fill=(*accent, 26))
        d.rectangle([body[0] + 2, cy - band, body[2] - 2, cy + band],
                    fill=(*accent, 52))

    translucent(img, fills)

    d = ImageDraw.Draw(img)
    d.rounded_rectangle(body, radius=w // 3, outline=(*accent, 225),
                        width=max(2, w // 24))
    d.line([(body[0] + 3, cy - band), (body[2] - 3, cy - band)],
           fill=(*accent, 180), width=2)
    d.line([(body[0] + 3, cy + band), (body[2] - 3, cy + band)],
           fill=(*accent, 180), width=2)
    light = max(3, w // 8)
    d.ellipse([cx - light, cy - light, cx + light, cy + light],
              fill=(*accent, 245))
    if label:
        f = font(FONT_MONO, max(11, w // 5))
        tw = d.textlength(label, font=f)
        d.text((cx - tw / 2, cy + h // 2 + 8), label, font=f, fill=(*accent, 220))


def banner() -> None:
    img = vertical_gradient((1600, 520), BG_TOP, BG_BOT)
    circuit_grid(img, 44)

    PODS = ((1268, CYAN, 210), (1380, AMBER, 250), (1492, VIOLET, 190))

    def pod_shapes(d: ImageDraw.ImageDraw) -> None:
        for i, (x, accent, h) in enumerate(PODS):
            cy = 292 - i * 6
            d.rounded_rectangle([x - 39, cy - h // 2, x + 39, cy + h // 2],
                                radius=26, outline=(*accent, 190), width=4)

    # Glow first (blurred copy), then the crisp pod on top.
    translucent(img, pod_shapes, blur=14)
    for i, (x, accent, h) in enumerate(PODS):
        capsule(img, x, 292 - i * 6, 78, h, accent)

    d = ImageDraw.Draw(img)
    d.text((86, 96), "MEGA MAN X", font=font(FONT_BOLD, 40), fill=(*CYAN, 255))
    d.text((84, 142), "ZERO HISTORY", font=font(FONT_BOLD, 104), fill=(*WHITE, 255))
    d.rectangle([88, 268, 300, 274], fill=(*AMBER, 255))
    d.text((86, 296), "La historia que Zero nunca alcanzó a contar",
           font=font(FONT_BOLD, 30), fill=(*AMBER, 255))
    d.text((86, 346), "Recompilación nativa  ·  español chileno  ·  jefes y etapas nuevas",
           font=font(FONT_REG, 23), fill=(*GREY, 255))
    d.text((86, 384), "Linux · Windows · macOS · Android  ·  mando y controles táctiles",
           font=font(FONT_REG, 23), fill=(*GREY, 255))

    badge_f = font(FONT_MONO, 20)
    text = "v0.0.1 — Bóveda Ω"
    bw = d.textlength(text, font=badge_f)
    translucent(img, lambda dd: dd.rounded_rectangle(
        [86, 434, 86 + bw + 44, 486], radius=10, fill=(168, 138, 255, 26),
        outline=(*VIOLET, 210), width=2))
    d.text((108, 447), text, font=badge_f, fill=(*VIOLET, 255))
    img.convert("RGB").save(OUT / "banner.png", quality=92)


STAGES = [
    ("W-01", "Cóndor Cobalto", "Cordillera de los Andes", "Ala Cobalto"),
    ("W-02", "Salitre Sierpe", "Desierto de Atacama", "Salmuera"),
    ("W-03", "Glaciar Grifo", "Campo de Hielo Sur", "Aliento Blanco"),
    ("W-04", "Víbora Caldor", "Volcán Caldor", "Erupción"),
    ("W-05", "Marea Mantis", "Fiordos de Chiloé", "Ola Cortante"),
    ("W-06", "Jabalí Alerce", "Selva Valdiviana", "Astilla"),
    ("W-07", "Búho Reloj", "Puerto del Reloj", "Segundero"),
    ("W-08", "Puma Chatarra", "Desarmadero Wily", "Imán Puma"),
]
ACCENTS = [CYAN, AMBER, (140, 210, 255), RED, (110, 255, 210),
           (150, 220, 110), VIOLET, (240, 140, 200)]


def stage_map() -> None:
    img = vertical_gradient((1500, 840), (10, 12, 22), (22, 12, 30))
    circuit_grid(img, 50)
    d = ImageDraw.Draw(img)
    d.text((60, 40), "MAPA DE ETAPAS", font=font(FONT_BOLD, 40), fill=(*WHITE, 255))
    d.text((60, 92), "ocho revisiones W de la línea Zero, más la Bóveda Ω",
           font=font(FONT_REG, 22), fill=(*GREY, 255))

    cw, ch, gap = 330, 150, 24
    x0, y0 = 60, 156

    def cards(dd: ImageDraw.ImageDraw) -> None:
        for i in range(len(STAGES)):
            col, row = i % 4, i // 4
            x = x0 + col * (cw + gap)
            y = y0 + row * (ch + gap)
            accent = ACCENTS[i]
            dd.rounded_rectangle([x, y, x + cw, y + ch], radius=12,
                                 fill=(255, 255, 255, 12),
                                 outline=(*accent, 195), width=2)

    translucent(img, cards)

    for i, (code, name, place, weapon) in enumerate(STAGES):
        col, row = i % 4, i // 4
        x = x0 + col * (cw + gap)
        y = y0 + row * (ch + gap)
        accent = ACCENTS[i]
        d.rectangle([x + 1, y + 1, x + 9, y + ch - 1], fill=(*accent, 235))
        d.text((x + 26, y + 18), code, font=font(FONT_MONO, 20), fill=(*accent, 255))
        d.text((x + 26, y + 46), name, font=font(FONT_BOLD, 27), fill=(*WHITE, 255))
        d.text((x + 26, y + 84), place, font=font(FONT_REG, 18), fill=(*GREY, 255))
        d.text((x + 26, y + 112), f"Arma: {weapon}", font=font(FONT_REG, 18),
               fill=(*accent, 235))

    fx, fy = 60, 512

    def final_card(dd: ImageDraw.ImageDraw) -> None:
        dd.rounded_rectangle([fx, fy, fx + 1380, fy + 152], radius=14,
                             fill=(255, 92, 92, 22), outline=(*RED, 215), width=2)

    translucent(img, final_card)
    d.text((fx + 28, fy + 20), "FINAL", font=font(FONT_MONO, 20), fill=(*RED, 255))
    d.text((fx + 28, fy + 48), "Bóveda Ω — Cero-Ω y el Eco de Wily",
           font=font(FONT_BOLD, 32), fill=(*WHITE, 255))
    d.text((fx + 28, fy + 96),
           "Se abre con las 8 memorias. El final cambia según cuántos fragmentos juntaste.",
           font=font(FONT_REG, 19), fill=(*GREY, 255))

    d.text((60, 696), "CADENA DE DEBILIDADES",
           font=font(FONT_MONO, 18), fill=(*AMBER, 255))
    d.text((60, 724),
           "Puma → Cobalto → Alerce → Mantis → Caldor → Grifo → Sierpe → Reloj → Puma",
           font=font(FONT_BOLD, 22), fill=(*WHITE, 240))
    d.text((60, 766),
           "Cada jefe suelta su arma y la cadena se cierra en anillo: ningún orden deja al jugador sin salida.",
           font=font(FONT_REG, 17), fill=(*GREY, 235))
    img.convert("RGB").save(OUT / "mapa-etapas.png", quality=92)


CAPSULES = [
    ("Botas", "salto y dash aéreo", CYAN),
    ("Armadura", "daño reducido", AMBER),
    ("Casco", "rompe bloques", VIOLET),
    ("Buster", "carga doble", (110, 255, 210)),
    ("Sable Zero", "habilita a Zero", RED),
    ("Núcleo 01", "fragmento de memoria", (150, 220, 110)),
    ("Núcleo 02", "fragmento de memoria", (240, 140, 200)),
    ("Núcleo 03", "fragmento de memoria", (140, 210, 255)),
]


def capsules_art() -> None:
    img = vertical_gradient((1500, 486), (10, 12, 22), (24, 14, 26))
    circuit_grid(img, 50)
    d = ImageDraw.Draw(img)
    d.text((60, 40), "CÁPSULAS ERRANTES", font=font(FONT_BOLD, 36), fill=(*WHITE, 255))
    d.text((60, 88), "una por etapa, contenido barajado por semilla, siempre alcanzable",
           font=font(FONT_REG, 21), fill=(*GREY, 255))

    slot = 1440 // 8
    for i, (name, effect, accent) in enumerate(CAPSULES):
        cx = 60 + slot // 2 + i * slot
        capsule(img, cx, 208, 64, 100, accent, f"0{i + 1}")
        d.text((cx - slot // 2 + 4, 296), name, font=font(FONT_BOLD, 19),
               fill=(*WHITE, 255))
        words = effect.split()
        for j in range(0, len(words), 2):
            d.text((cx - slot // 2 + 4, 324 + j * 22),
                   " ".join(words[j:j + 2]), font=font(FONT_REG, 15),
                   fill=(*GREY, 240))

    d.rectangle([60, 406, 1440, 408], fill=(*AMBER, 130))
    d.text((60, 422),
           "Semilla visible en el select de etapas · Modo Historia reproducible · Modo Speedrun fijo",
           font=font(FONT_REG, 18), fill=(*AMBER, 235))
    img.convert("RGB").save(OUT / "capsulas.png", quality=92)


def timeline() -> None:
    img = vertical_gradient((1500, 430), (10, 12, 22), (20, 12, 28))
    circuit_grid(img, 50)
    d = ImageDraw.Draw(img)
    d.text((60, 38), "LÍNEA DE TIEMPO: QUÉ PASÓ CON ZERO",
           font=font(FONT_BOLD, 32), fill=(*WHITE, 255))
    y = 216
    d.line([(90, y), (1420, y)], fill=(*GREY, 110), width=3)
    beats = [
        ("21XX-Δ", ["Wily ensambla la", "unidad W-00"], RED),
        ("21XX-Δ+3", ["Primera salida:", "matar a Mega Man"], AMBER),
        ("21XX-Δ+9", ["Sello de la Bóveda Ω", "bajo Atacama"], CYAN),
        ("Hoy", ["Ocho revisiones W", "se reactivan"], VIOLET),
        ("Final", ["Zero decide si", "sigue siendo Zero"], (110, 255, 210)),
    ]
    step = 1320 // len(beats)
    for i, (when, lines, accent) in enumerate(beats):
        cx = 120 + i * step + step // 2
        d.ellipse([cx - 10, y - 10, cx + 10, y + 10], fill=(*accent, 255))
        d.text((cx - 46, y - 62), when, font=font(FONT_MONO, 17), fill=(*accent, 240))
        for j, line in enumerate(lines):
            d.text((cx - 86, y + 26 + j * 24), line, font=font(FONT_REG, 17),
                   fill=(*WHITE, 235))
    d.text((60, 372),
           "Cada jefe carga un fragmento cifrado de esa memoria. Juntarlos es la historia.",
           font=font(FONT_REG, 18), fill=(*GREY, 240))
    img.convert("RGB").save(OUT / "linea-tiempo.png", quality=92)


def android_layout() -> None:
    img = vertical_gradient((1200, 620), (9, 12, 22), (18, 12, 28))
    circuit_grid(img, 50)
    d = ImageDraw.Draw(img)
    d.text((56, 36), "ANDROID: CONTROLES TÁCTILES + MANDO", font=font(FONT_BOLD, 30),
           fill=(*WHITE, 255))
    d.text((56, 80), "el mando externo se detecta solo y los botones táctiles se ocultan al conectarlo",
           font=font(FONT_REG, 18), fill=(*GREY, 240))

    px, py, pw, ph = 90, 130, 330, 450

    def phone(dd: ImageDraw.ImageDraw) -> None:
        dd.rounded_rectangle([px, py, px + pw, py + ph], radius=36,
                             fill=(14, 16, 26, 255), outline=(*GREY, 165), width=3)

    translucent(img, phone)
    d.rounded_rectangle([px + 22, py + 26, px + pw - 22, py + ph - 96], radius=10,
                        fill=(28, 74, 104, 255))
    d.text((px + 44, py + 44), "escenario 16:9", font=font(FONT_REG, 15),
           fill=(*WHITE, 225))

    def pad(dd: ImageDraw.ImageDraw) -> None:
        cx, cy = px + 84, py + ph - 116
        for dx, dy in ((-26, 0), (26, 0), (0, -26), (0, 26)):
            dd.rounded_rectangle([cx + dx - 21, cy + dy - 21, cx + dx + 21, cy + dy + 21],
                                 radius=8, fill=(255, 255, 255, 36),
                                 outline=(*CYAN, 205), width=2)
        bx, by = px + pw - 88, py + ph - 120
        for dx, dy in ((0, -40), (40, 0), (0, 40), (-40, 0)):
            dd.ellipse([bx + dx - 20, by + dy - 20, bx + dx + 20, by + dy + 20],
                       fill=(255, 255, 255, 32), outline=(*AMBER, 225), width=2)
        for i in range(2):
            dd.rounded_rectangle([px + 34 + i * (pw - 104), py + ph - 200,
                                  px + 80 + i * (pw - 104), py + ph - 172],
                                 radius=8, outline=(*VIOLET, 205), width=2,
                                 fill=(255, 255, 255, 26))
        dd.rounded_rectangle([px + pw / 2 - 34, py + ph - 200,
                              px + pw / 2 + 34, py + ph - 172],
                             radius=8, outline=(*GREY, 185), width=2)

    translucent(img, pad)

    bx, by = px + pw - 88, py + ph - 120
    for dx, dy, label in ((0, -40, "Y"), (40, 0, "B"), (0, 40, "A"), (-40, 0, "X")):
        f = font(FONT_BOLD, 17)
        tw = d.textlength(label, font=f)
        d.text((bx + dx - tw / 2, by + dy - 11), label, font=f, fill=(*WHITE, 245))
    for i, label in enumerate(("L", "R")):
        d.text((px + 48 + i * (pw - 104), py + ph - 196), label,
               font=font(FONT_BOLD, 15), fill=(*VIOLET, 245))
    d.text((px + pw / 2 - 22, py + ph - 194), "start", font=font(FONT_REG, 13),
           fill=(*GREY, 240))

    d.text((470, 150), "Mapeo equivalente", font=font(FONT_BOLD, 24), fill=(*AMBER, 255))
    rows = [
        ("D-pad táctil", "Direcciones (X3 usa D-pad, no stick)"),
        ("Y / B / A / X", "Los cuatro botones SNES"),
        ("L / R", "Hombro izquierdo y derecho"),
        ("start", "Pausa y confirmación"),
        ("Mando Bluetooth", "SDL_GameController: Xbox, DualShock, 8BitDo"),
        ("Vibración", "Opcional, apagada por defecto"),
    ]

    def row_bgs(dd: ImageDraw.ImageDraw) -> None:
        for i in range(len(rows)):
            y = 196 + i * 46
            dd.rounded_rectangle([470, y - 8, 1110, y + 30], radius=6,
                                 fill=(255, 255, 255, 12))

    translucent(img, row_bgs)
    for i, (a, b) in enumerate(rows):
        y = 196 + i * 46
        d.text((488, y - 2), a, font=font(FONT_BOLD, 18), fill=(*CYAN, 245))
        d.text((672, y - 2), b, font=font(FONT_REG, 17), fill=(*GREY, 245))

    d.text((470, 500),
           "Tamaño, opacidad, espejado izquierdo/diestro y zona muerta configurables.",
           font=font(FONT_REG, 16), fill=(*GREY, 230))
    img.convert("RGB").save(OUT / "android.png", quality=92)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    banner()
    stage_map()
    capsules_art()
    timeline()
    android_layout()
    for name in ("banner.png", "mapa-etapas.png", "capsulas.png",
                 "linea-tiempo.png", "android.png"):
        p = OUT / name
        print(f"{p.relative_to(ROOT)}  {p.stat().st_size // 1024} KiB")


if __name__ == "__main__":
    main()
