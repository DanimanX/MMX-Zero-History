#!/usr/bin/env python3
"""Generate MMX Zero History brand art (original, repo-owned).

Everything here is drawn from primitives: gradients, grids, capsule pods and
typography. No game sprite, logo or ROM-derived pixel is used, so the output
is safe to commit and to publish.

Every canvas is 16:9 -- the same aspect the game renders at since v0.0.2:

    banner.png        1920x1080   README hero
    mapa-etapas.png   1920x1080   stage map and weakness ring
    capsulas.png      1920x1080   wandering capsules
    linea-tiempo.png  1920x1080   story timeline
    android.png       1920x1080   touch controls and gamepad mapping

It also writes the Android launch plate:

    android/app/src/main/res/drawable-nodpi/splash.png   1920x1080

Run:

    python3 tools/make_brand_art.py

Only Pillow is required. Fonts are resolved from a candidate list so the tool
works on Debian/Ubuntu, Fedora and macOS alike; if none of the candidates
exist, Pillow's built-in bitmap font is used and the layout still fits because
every string is measured before it is drawn.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "img"
ANDROID_RES = ROOT / "android" / "app" / "src" / "main" / "res" / "drawable-nodpi"
ANDROID_RES_ROOT = ROOT / "android" / "app" / "src" / "main" / "res"
LEGACY_ICONS = {
    "mipmap-mdpi": 48,
    "mipmap-hdpi": 72,
    "mipmap-xhdpi": 96,
    "mipmap-xxhdpi": 144,
    "mipmap-xxxhdpi": 192,
}

# Prefer a real proportional face; fall back through the usual distro paths.
FONT_CANDIDATES = {
    "bold": [
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/gsfonts/NimbusSans-Bold.otf",
        "/usr/share/fonts/TTF/Hack-Bold.ttf",
    ],
    "regular": [
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/gsfonts/NimbusSans-Regular.otf",
        "/usr/share/fonts/TTF/Hack-Regular.ttf",
    ],
    "mono": [
        "/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf",
        "/usr/share/fonts/liberation/LiberationMono-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
        "/usr/share/fonts/gsfonts/NimbusMonoPS-Bold.otf",
        "/usr/share/fonts/TTF/JetBrainsMonoNLNerdFont-Bold.ttf",
    ],
}

BG_TOP = (8, 12, 24)
BG_BOT = (18, 10, 28)
CYAN = (86, 232, 255)
AMBER = (255, 176, 64)
RED = (255, 92, 92)
VIOLET = (168, 138, 255)
GREEN = (110, 255, 210)
GREY = (150, 162, 180)
WHITE = (238, 244, 255)

W, H = 1920, 1080
M = 96  # safe margin

_font_cache: dict[tuple[str, int], ImageFont.ImageFont] = {}


def _font_path(kind: str) -> str | None:
    for candidate in FONT_CANDIDATES[kind]:
        if Path(candidate).is_file():
            return candidate
    return None


def font(kind: str, size: int) -> ImageFont.ImageFont:
    key = (kind, size)
    cached = _font_cache.get(key)
    if cached is not None:
        return cached
    path = _font_path(kind)
    if path is None:
        face: ImageFont.ImageFont = ImageFont.load_default(size)
    else:
        face = ImageFont.truetype(path, size)
    _font_cache[key] = face
    return face


def text_width(draw: ImageDraw.ImageDraw, text: str,
               face: ImageFont.ImageFont) -> float:
    return draw.textlength(text, font=face)


def fit_font(draw: ImageDraw.ImageDraw, kind: str, size: int, text: str,
             max_width: float, min_size: int = 12) -> ImageFont.ImageFont:
    """Largest face at or below `size` that keeps `text` inside `max_width`."""
    while size > min_size:
        face = font(kind, size)
        if text_width(draw, text, face) <= max_width:
            return face
        size -= 2
    return font(kind, min_size)


def vertical_gradient(size: tuple[int, int], top: tuple[int, int, int],
                      bottom: tuple[int, int, int]) -> Image.Image:
    w, h = size
    strip = Image.new("RGB", (1, h))
    px = strip.load()
    for y in range(h):
        t = y / max(1, h - 1)
        px[0, y] = tuple(round(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
    resample = getattr(Image, "Resampling", Image).BILINEAR
    return strip.resize((w, h), resample).convert("RGBA")


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


def circuit_grid(base: Image.Image, step: int = 60) -> None:
    def grid(d: ImageDraw.ImageDraw) -> None:
        w, h = base.size
        for x in range(0, w, step):
            d.line([(x, 0), (x, h)], fill=(90, 190, 230, 22), width=1)
        for y in range(0, h, step):
            d.line([(0, y), (w, y)], fill=(90, 190, 230, 22), width=1)
        # A few brighter traces so the grid does not read as graph paper.
        d.line([(0, h * 0.74), (w * 0.28, h * 0.74), (w * 0.36, h * 0.52),
                (w, h * 0.52)], fill=(86, 232, 255, 58), width=2)
        d.line([(0, h * 0.30), (w * 0.18, h * 0.30), (w * 0.26, h * 0.14),
                (w, h * 0.14)], fill=(255, 176, 64, 44), width=2)

    translucent(base, grid)


def frame_16x9(img: Image.Image, box: tuple[int, int, int, int],
               accent: tuple[int, int, int] = CYAN, width: int = 3,
               label: str = "16:9") -> None:
    """A viewport frame with corner ticks and a small ratio tag."""
    x0, y0, x1, y1 = box

    def draw_frame(d: ImageDraw.ImageDraw) -> None:
        d.rectangle(box, outline=(*accent, 120), width=width)
        tick = 26
        for (cx, cy, dx, dy) in (
            (x0, y0, 1, 1), (x1, y0, -1, 1),
            (x0, y1, 1, -1), (x1, y1, -1, -1),
        ):
            d.line([(cx, cy), (cx + dx * tick, cy)], fill=(*accent, 235), width=4)
            d.line([(cx, cy), (cx, cy + dy * tick)], fill=(*accent, 235), width=4)

    translucent(img, draw_frame)

    if label:
        d = ImageDraw.Draw(img)
        face = font("mono", 18)
        tw = text_width(d, label, face)
        pad = 12
        bx0, by0 = x0 + 18, y0 - 16
        translucent(img, lambda dd: dd.rounded_rectangle(
            [bx0, by0, bx0 + tw + pad * 2, by0 + 32], radius=6,
            fill=(*accent, 34), outline=(*accent, 200), width=1))
        d.text((bx0 + pad, by0 + 7), label, font=face, fill=(*accent, 245))


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
        face = font("mono", max(11, w // 8))
        tw = text_width(d, label, face)
        d.text((cx - tw / 2, cy + h // 2 - face.size - 18), label, font=face,
               fill=(*accent, 220))


def title_block(img: Image.Image, kicker: str, title: str, subtitle: str,
                accent: tuple[int, int, int] = AMBER) -> None:
    d = ImageDraw.Draw(img)
    kicker_face = font("mono", 24)
    d.text((M, 78), kicker.upper(), font=kicker_face, fill=(*CYAN, 235))

    title_face = fit_font(d, "bold", 66, title, W - 2 * M)
    d.text((M - 4, 116), title, font=title_face, fill=(*WHITE, 255))

    d.rectangle([M, 208, M + 132, 214], fill=(*accent, 255))

    sub_face = fit_font(d, "regular", 28, subtitle, W - 2 * M)
    d.text((M, 236), subtitle, font=sub_face, fill=(*GREY, 245))


def pill(img: Image.Image, x: int, y: int, text: str,
         accent: tuple[int, int, int] = VIOLET, size: int = 22) -> int:
    d = ImageDraw.Draw(img)
    face = font("mono", size)
    tw = text_width(d, text, face)
    w = tw + 40
    h = size + 22
    translucent(img, lambda dd: dd.rounded_rectangle(
        [x, y, x + w, y + h], radius=8, fill=(*accent, 26),
        outline=(*accent, 210), width=2))
    d.text((x + 20, y + (h - size) / 2 - 2), text, font=face,
           fill=(*accent, 250))
    return w


def banner() -> None:
    img = vertical_gradient((W, H), BG_TOP, BG_BOT)
    circuit_grid(img, 60)

    # Right: a 16:9 viewport holding the stasis line-up.
    vx0, vy0 = 1010, 300
    vx1, vy1 = vx0 + 800, vy0 + 450
    frame_16x9(img, (vx0, vy0, vx1, vy1), CYAN, 3,
               "16:9 nativo · 342 × 224")

    PODS = ((1180, CYAN, 300), (1330, AMBER, 360), (1480, VIOLET, 270))
    for i, (x, accent, h) in enumerate(PODS):
        cy = 520 - i * 6
        capsule(img, x, cy, 118, h, accent, f"W-0{i + 1}")

    # Left: wordmark, measured so it can never run into the viewport frame.
    d = ImageDraw.Draw(img)
    d.text((M, 208), "MEGA MAN X", font=font("bold", 58), fill=(*CYAN, 255))
    wordmark = "ZERO HISTORY"
    d.text((M - 6, 268),
           wordmark, font=fit_font(d, "bold", 166, wordmark, 900),
           fill=(*WHITE, 255))
    d.rectangle([M, 456, M + 330, 470], fill=(*AMBER, 255))

    tag = "La historia que Zero nunca alcanzó a contar"
    d.text((M, 508), tag, font=fit_font(d, "bold", 44, tag, 880),
           fill=(*AMBER, 255))
    for i, line in enumerate((
        "Recompilación nativa · español chileno",
        "Ocho jefes, ocho memorias, tres finales",
    )):
        d.text((M, 590 + i * 46), line, font=font("regular", 30),
               fill=(*GREY, 245))

    # Platform chips.
    x = M
    for name in ("Linux", "Windows", "macOS", "Android"):
        x += pill(img, x, 736, name, CYAN if name != "Android" else GREEN) + 14

    w = pill(img, M, 832, "v0.0.5 — Bóveda Ω", VIOLET, 24)
    pill(img, M + w + 14, 832, "16:9 EN TODAS LAS VERSIONES", AMBER, 24)

    img.convert("RGB").save(OUT / "banner.png", quality=94)


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
ACCENTS = [CYAN, AMBER, (140, 210, 255), RED, GREEN,
           (150, 220, 110), VIOLET, (240, 140, 200)]


def stage_map() -> None:
    img = vertical_gradient((W, H), (10, 12, 22), (22, 12, 30))
    circuit_grid(img, 60)
    title_block(img, "Bóveda Ω", "Mapa de etapas",
                "ocho revisiones W de la línea Zero, más el jefe final")

    cw, ch, gap = 402, 200, 32
    x0, y0 = M, 300

    def cards(dd: ImageDraw.ImageDraw) -> None:
        for i in range(len(STAGES)):
            col, row = i % 4, i // 4
            x = x0 + col * (cw + gap)
            y = y0 + row * (ch + gap)
            accent = ACCENTS[i]
            dd.rounded_rectangle([x, y, x + cw, y + ch], radius=14,
                                 fill=(255, 255, 255, 12),
                                 outline=(*accent, 195), width=2)

    translucent(img, cards)

    d = ImageDraw.Draw(img)
    for i, (code, name, place, weapon) in enumerate(STAGES):
        col, row = i % 4, i // 4
        x = x0 + col * (cw + gap)
        y = y0 + row * (ch + gap)
        accent = ACCENTS[i]
        d.rectangle([x + 1, y + 1, x + 11, y + ch - 1], fill=(*accent, 235))
        d.text((x + 32, y + 24), code, font=font("mono", 24),
               fill=(*accent, 255))
        name_face = fit_font(d, "bold", 34, name, cw - 56)
        d.text((x + 32, y + 60), name, font=name_face, fill=(*WHITE, 255))
        d.text((x + 32, y + 112), place, font=font("regular", 22),
               fill=(*GREY, 255))
        d.text((x + 32, y + 150), f"Arma: {weapon}", font=font("regular", 22),
               fill=(*accent, 240))

    fx, fy, fw, fh = M, 760, 4 * cw + 3 * gap, 150
    translucent(img, lambda dd: dd.rounded_rectangle(
        [fx, fy, fx + fw, fy + fh], radius=16,
        fill=(255, 92, 92, 26), outline=(*RED, 220), width=2))
    d.text((fx + 32, fy + 20), "FINAL", font=font("mono", 24),
           fill=(*RED, 255))
    d.text((fx + 32, fy + 52), "Bóveda Ω — Cero-Ω y el Eco de Wily",
           font=font("bold", 38), fill=(*WHITE, 255))
    d.text((fx + 32, fy + 104),
           "Se abre con las 8 memorias. El final cambia según cuántos fragmentos juntaste.",
           font=font("regular", 23), fill=(*GREY, 245))
    pill(img, fx + fw - 272, fy + 46, "16:9 · 342 × 224", RED, 21)

    d.text((M, 942), "CADENA DE DEBILIDADES", font=font("mono", 22),
           fill=(*AMBER, 255))
    chain = "Puma → Cobalto → Alerce → Mantis → Caldor → Grifo → Sierpe → Reloj → Puma"
    d.text((M, 976), chain,
           font=fit_font(d, "bold", 34, chain, W - 2 * M),
           fill=(*WHITE, 245))
    d.text((M, 1024),
           "Cada jefe suelta su arma y la cadena se cierra en anillo: ningún orden deja al jugador sin salida.",
           font=font("regular", 22), fill=(*GREY, 225))

    img.convert("RGB").save(OUT / "mapa-etapas.png", quality=94)


CAPSULES = [
    ("Botas", "salto y dash aéreo", CYAN),
    ("Armadura", "daño reducido", AMBER),
    ("Casco", "rompe bloques", VIOLET),
    ("Buster", "carga doble", GREEN),
    ("Sable Zero", "habilita a Zero", RED),
    ("Núcleo 01", "fragmento de memoria", (150, 220, 110)),
    ("Núcleo 02", "fragmento de memoria", (240, 140, 200)),
    ("Núcleo 03", "fragmento de memoria", (140, 210, 255)),
]


def capsules_art() -> None:
    img = vertical_gradient((W, H), (10, 12, 22), (24, 14, 26))
    circuit_grid(img, 60)
    title_block(img, "Una por etapa", "Cápsulas errantes",
                "tres nichos por etapa, contenido barajado por semilla, siempre alcanzable")

    slot = (W - 2 * M) // 8  # 216
    d = ImageDraw.Draw(img)
    for i, (name, effect, accent) in enumerate(CAPSULES):
        cx = M + slot // 2 + i * slot
        capsule(img, cx, 470, 112, 238, accent, f"0{i + 1}")
        name_face = fit_font(d, "bold", 27, name, slot - 24)
        d.text((cx - text_width(d, name, name_face) / 2, 616), name,
               font=name_face, fill=(*WHITE, 255))
        words = effect.split()
        lines = [" ".join(words[j:j + 2]) for j in range(0, len(words), 2)]
        for j, line in enumerate(lines):
            face = fit_font(d, "regular", 20, line, slot - 16)
            d.text((cx - text_width(d, line, face) / 2, 660 + j * 28), line,
                   font=face, fill=(*GREY, 240))

    d.rectangle([M, 800, W - M, 803], fill=(*AMBER, 130))
    note = "Semilla visible en el select de etapas · Modo Historia reproducible · Modo Speedrun fijo"
    d.text((M, 830), note, font=fit_font(d, "regular", 26, note, W - 2 * M),
           fill=(*AMBER, 235))

    d.text((M, 906), "16:9 EN TODAS LAS VERSIONES", font=font("mono", 22),
           fill=(*CYAN, 230))
    d.text((M, 940),
           "El reparto de cápsulas es idéntico en Linux, Windows, macOS y Android; lo único que cambia es el tamaño de la ventana.",
           font=font("regular", 22), fill=(*GREY, 225))

    img.convert("RGB").save(OUT / "capsulas.png", quality=94)


def timeline() -> None:
    img = vertical_gradient((W, H), (10, 12, 22), (20, 12, 28))
    circuit_grid(img, 60)
    title_block(img, "Línea de tiempo", "Qué pasó con Zero",
                "cinco momentos, ninguno contado en una cinemática")

    y = 560
    d = ImageDraw.Draw(img)
    d.line([(140, y), (W - 140, y)], fill=(*GREY, 110), width=3)
    beats = [
        ("21XX-Δ", ["Wily ensambla la", "unidad W-00"], RED),
        ("21XX-Δ+3", ["Primera salida:", "matar a Mega Man"], AMBER),
        ("21XX-Δ+9", ["Sello de la Bóveda Ω", "bajo Atacama"], CYAN),
        ("Hoy", ["Ocho revisiones W", "se reactivan"], VIOLET),
        ("Final", ["Zero decide si", "sigue siendo Zero"], GREEN),
    ]
    span = (W - 280)
    step = span // len(beats)
    for i, (when, lines, accent) in enumerate(beats):
        cx = 140 + i * step + step // 2
        d.ellipse([cx - 14, y - 14, cx + 14, y + 14], fill=(*accent, 255))
        d.ellipse([cx - 26, y - 26, cx + 26, y + 26],
                  outline=(*accent, 130), width=2)
        when_face = font("mono", 22)
        d.text((cx - text_width(d, when, when_face) / 2, y - 96), when,
               font=when_face, fill=(*accent, 245))
        for j, line in enumerate(lines):
            face = fit_font(d, "regular", 24, line, step - 28)
            d.text((cx - text_width(d, line, face) / 2, y + 54 + j * 34),
                   line, font=face, fill=(*WHITE, 240))

    closing = "Cada jefe carga un fragmento cifrado de esa memoria. Juntarlos es la historia."
    d.text((M, 880), closing,
           font=fit_font(d, "bold", 34, closing, W - 2 * M),
           fill=(*AMBER, 245))
    d.text((M, 946),
           "Tres finales según cuántos fragmentos juntaste · el último es el que importa.",
           font=font("regular", 24), fill=(*GREY, 230))

    img.convert("RGB").save(OUT / "linea-tiempo.png", quality=94)


def _phone_screen(img: Image.Image, box: tuple[int, int, int, int]) -> None:
    """A stylised 16:9 playfield plus the touch overlay inside `box`."""
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0

    def backdrop(d: ImageDraw.ImageDraw) -> None:
        d.rectangle(box, fill=(12, 30, 48, 255))
        d.rectangle([x0, y0 + int(h * 0.62), x1, y1], fill=(20, 58, 52, 255))

    translucent(img, backdrop)

    d = ImageDraw.Draw(img)
    d.text((x0 + 18, y0 + 14), "342 × 224 nativo · 16:9",
           font=font("mono", 17), fill=(*WHITE, 225))

    unit = min(w, h)

    def key(x: float, y: float, ww: float, hh: float, accent, label: str) -> None:
        bx0, by0 = x0 + x * w, y0 + y * h
        bw, bh = ww * unit, hh * unit
        translucent(img, lambda dd: dd.rounded_rectangle(
            [bx0, by0, bx0 + bw, by0 + bh], radius=12,
            fill=(255, 255, 255, 30), outline=(*accent, 205), width=2))
        face = font("bold", max(11, int(min(bw, bh) * 0.38)))
        tw = text_width(d, label, face)
        d.text((bx0 + (bw - tw) / 2, by0 + (bh - face.size) / 2 - 3), label,
               font=face, fill=(*WHITE, 240))

    # D-pad (square keys) bottom-left. The arm is slightly larger than the
    # key so the four keys never overlap and every key stays on screen.
    kx, ky, size = 0.230, 0.770, 0.120
    arm = size * 1.06
    for label, dx, dy in (("▲", 0, -1), ("▼", 0, 1), ("<", -1, 0), (">", 1, 0)):
        cx = kx + dx * arm
        cy = ky + dy * arm
        key(cx - size / 2, cy - size / 2, size, size, CYAN, label)

    # Face diamond bottom-right, inset so the B key is not clipped.
    fx, fy, off, r = 0.790, 0.770, 0.120, 0.076
    for label, dx, dy in (("Y", 0, -1), ("B", 1, 0), ("A", 0, 1), ("X", -1, 0)):
        cx = fx + dx * off
        cy = fy + dy * off
        translucent(img, lambda dd: dd.ellipse(
            [x0 + cx * w - r * unit, y0 + cy * h - r * unit,
             x0 + cx * w + r * unit, y0 + cy * h + r * unit],
            fill=(255, 255, 255, 32), outline=(*AMBER, 225), width=2))
        face = font("bold", max(11, int(r * unit * 0.9)))
        tw = text_width(d, label, face)
        d.text((x0 + cx * w - tw / 2, y0 + cy * h - face.size * 0.62), label,
               font=face, fill=(*WHITE, 245))

    # Shoulders above the diamond, start centred between the clusters.
    key(0.706, 0.470, 0.098, 0.075, VIOLET, "L")
    key(0.876, 0.470, 0.098, 0.075, VIOLET, "R")
    key(0.446, 0.560, 0.108, 0.070, GREY, "start")


def android_layout() -> None:
    img = vertical_gradient((W, H), (9, 12, 22), (18, 12, 28))
    circuit_grid(img, 60)
    title_block(img, "Android", "16:9 de borde a borde",
                "pantalla completa inmersiva, recorte de notch y controles táctiles cuadrados")

    # Landscape device: a true 16:9 viewport inside a thin bezel.
    sx, sy, sw = 96, 300, 960
    sh = sw * 9 // 16
    bx0, by0 = sx - 18, sy - 18
    bx1, by1 = sx + sw + 18, sy + sh + 18
    translucent(img, lambda dd: dd.rounded_rectangle(
        [bx0, by0, bx1, by1], radius=34, fill=(14, 16, 26, 255),
        outline=(*GREY, 165), width=3))
    _phone_screen(img, (sx, sy, sx + sw, sy + sh))

    # Right-hand mapping table.
    d = ImageDraw.Draw(img)
    d.text((1150, 300), "Mapeo equivalente", font=font("bold", 36),
           fill=(*AMBER, 255))
    rows = [
        ("D-pad táctil", "Direcciones (X3 usa D-pad, no stick)"),
        ("Y / B / A / X", "Los cuatro botones SNES"),
        ("L / R", "Hombros izquierdo y derecho"),
        ("start / select", "Pausa, confirmación y menús"),
        ("Mando Bluetooth", "SDL_GameController: Xbox, DualShock, 8BitDo"),
        ("Vibración", "Opcional, apagada por defecto"),
    ]

    def row_bgs(dd: ImageDraw.ImageDraw) -> None:
        for i in range(len(rows)):
            y = 366 + i * 72
            dd.rounded_rectangle([1150, y, 1824, y + 58], radius=8,
                                 fill=(255, 255, 255, 12))

    translucent(img, row_bgs)
    for i, (a, b) in enumerate(rows):
        y = 366 + i * 72
        d.text((1170, y + 8), a, font=font("bold", 24), fill=(*CYAN, 245))
        d.text((1170, y + 34), b, font=fit_font(d, "regular", 21, b, 620),
               fill=(*GREY, 245))

    d.text((1150, 820), "Sin notch, sin barras, sin recorte:",
           font=font("bold", 24), fill=(*WHITE, 245))
    d.text((1150, 858),
           "layoutInDisplayCutoutMode = shortEdges",
           font=font("mono", 20), fill=(*GREEN, 230))
    d.text((1150, 890), "immersive sticky · sensorLandscape",
           font=font("mono", 20), fill=(*GREEN, 230))
    d.text((1150, 942),
           "Los botones se dimensionan sobre el lado corto, así siguen siendo",
           font=font("regular", 21), fill=(*GREY, 235))
    d.text((1150, 970),
           "cuadrados en 16:9, 19.5:9 y 20:9, y quedan dentro de los márgenes seguros.",
           font=font("regular", 21), fill=(*GREY, 235))

    img.convert("RGB").save(OUT / "android.png", quality=94)


def android_splash() -> None:
    """Launch plate: the same 16:9 frame the game presents."""
    img = vertical_gradient((W, H), BG_TOP, BG_BOT)
    circuit_grid(img, 72)
    frame_16x9(img, (M, 120, W - M, H - 120), CYAN, 2,
               "16:9 · 342 × 224")

    d = ImageDraw.Draw(img)
    title = "ZERO HISTORY"
    face = fit_font(d, "bold", 150, title, W - 2 * M - 240)
    tw = text_width(d, title, face)
    d.text(((W - tw) / 2, 430), title, font=face, fill=(*WHITE, 255))
    kicker = "MEGA MAN X"
    kface = font("bold", 44)
    kw = text_width(d, kicker, kface)
    d.text(((W - kw) / 2, 366), kicker, font=kface, fill=(*CYAN, 255))
    tag = "La historia que Zero nunca alcanzó a contar"
    tface = fit_font(d, "regular", 30, tag, W - 2 * M - 240)
    d.text(((W - text_width(d, tag, tface)) / 2, 618), tag, font=tface,
           fill=(*AMBER, 245))

    for i, accent in enumerate((CYAN, AMBER, VIOLET)):
        capsule(img, W // 2 - 160 + i * 160, 800, 74, 120, accent)

    img.convert("RGB").save(ANDROID_RES / "splash.png", quality=92)


def _draw_mark(size: int, scale: float) -> Image.Image:
    """Capsule + Omega, transparent background, centred."""
    layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    cx, cy = size // 2, size // 2
    w, h = int(size * scale * 0.52), int(size * scale * 0.86)
    body = [cx - w // 2, cy - h // 2, cx + w // 2, cy + h // 2]
    d.rounded_rectangle(body, radius=max(8, w // 3), fill=(20, 40, 60, 225),
                        outline=(*CYAN, 255), width=max(3, size // 96))
    band = max(4, h // 9)
    d.rectangle([body[0] + 2, cy - band, body[2] - 2, cy + band],
                fill=(*CYAN, 64))
    light = max(4, w // 8)
    d.ellipse([cx - light, cy - light, cx + light, cy + light],
              fill=(*AMBER, 255))
    face = font("bold", max(18, int(size * scale * 0.36)))
    tw = text_width(d, "Ω", face)
    d.text((cx - tw / 2, cy + h * 0.17), "Ω", font=face, fill=(*WHITE, 255))
    return layer


def launcher_icons() -> None:
    """Branded launcher icon (legacy mipmaps + adaptive foreground)."""
    base = 512
    bg = vertical_gradient((base, base), BG_TOP, BG_BOT)
    circuit_grid(bg, 64)
    bg.alpha_composite(_draw_mark(base, 0.72))
    mask = Image.new("L", (base, base), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, base, base],
                                           radius=base // 5, fill=255)
    bg.putalpha(mask)

    resample = getattr(Image, "Resampling", Image).LANCZOS
    for folder, px in LEGACY_ICONS.items():
        out = ANDROID_RES_ROOT / folder
        out.mkdir(parents=True, exist_ok=True)
        bg.resize((px, px), resample).save(out / "ic_launcher.png")

    # Adaptive foreground: transparent, motif inside the 66% safe zone.
    _draw_mark(432, 0.72).save(ANDROID_RES / "ic_launcher_foreground.png")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    ANDROID_RES.mkdir(parents=True, exist_ok=True)
    banner()
    stage_map()
    capsules_art()
    timeline()
    android_layout()
    android_splash()
    launcher_icons()
    for path in (OUT / "banner.png", OUT / "mapa-etapas.png",
                 OUT / "capsulas.png", OUT / "linea-tiempo.png",
                 OUT / "android.png", ANDROID_RES / "splash.png",
                 ANDROID_RES / "ic_launcher_foreground.png"):
        print(f"{path.relative_to(ROOT)}  {path.stat().st_size // 1024} KiB")


if __name__ == "__main__":
    main()
