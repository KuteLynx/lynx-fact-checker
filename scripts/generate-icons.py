"""Genera iconos PNG para la PWA de lynx-fact-checker."""
from PIL import Image, ImageDraw
import math

def _draw_lynx_face(draw, cx, cy, size):
    """Dibuja una carita de lynx/cat hacker estilo Dark Michi."""
    # Colores
    accent = (88, 166, 255)
    accent_glow = (120, 190, 255)
    text_color = (230, 237, 243)

    # Tamaño relativo
    r = size * 0.40  # radio de la cara

    # Círculo de la cara
    draw.ellipse(
        [cx - r, cy - r * 0.85, cx + r, cy + r * 0.7],
        fill=(22, 27, 34),
        outline=accent,
        width=max(2, int(size * 0.02)),
    )

    # Orejas (triángulos)
    ear_offset = r * 0.6
    ear_height = r * 0.5
    # Oreja izquierda
    draw.polygon(
        [
            (cx - ear_offset, cy - r * 0.5),
            (cx - ear_offset - r * 0.3, cy - r * 0.9),
            (cx - ear_offset + r * 0.1, cy - r * 0.7),
        ],
        fill=accent,
    )
    # Oreja derecha
    draw.polygon(
        [
            (cx + ear_offset, cy - r * 0.5),
            (cx + ear_offset + r * 0.3, cy - r * 0.9),
            (cx + ear_offset - r * 0.1, cy - r * 0.7),
        ],
        fill=accent,
    )

    # Ojos (dos óvalos brillantes tipo hacker)
    eye_r = r * 0.18
    eye_y = cy - r * 0.2
    for ex in [cx - r * 0.25, cx + r * 0.25]:
        # Brillo exterior
        draw.ellipse(
            [ex - eye_r * 1.3, eye_y - eye_r * 1.3, ex + eye_r * 1.3, eye_y + eye_r * 1.3],
            fill=accent_glow,
        )
        # Pupila
        draw.ellipse(
            [ex - eye_r, eye_y - eye_r, ex + eye_r, eye_y + eye_r],
            fill=(13, 17, 23),
        )

    # Nariz
    nose_y = cy + r * 0.1
    draw.polygon(
        [
            (cx, nose_y + r * 0.08),
            (cx - r * 0.08, nose_y - r * 0.05),
            (cx + r * 0.08, nose_y - r * 0.05),
        ],
        fill=accent,
    )

    # Bigotes
    whisker_len = r * 0.4
    whisker_y = nose_y + r * 0.05
    for direction in [-1, 1]:
        bx = cx + direction * r * 0.15
        for dy in [-0.06, 0, 0.06]:
            draw.line(
                [
                    (bx, whisker_y + dy * r),
                    (bx + direction * whisker_len, whisker_y + dy * r + direction * r * 0.05),
                ],
                fill=accent_glow,
                width=max(1, int(size * 0.015)),
            )

    # Hoodie hood (curva sobre la cabeza)
    hood_y = cy - r * 1.0
    draw.arc(
        [cx - r * 1.1, hood_y - r * 0.3, cx + r * 1.1, hood_y + r * 0.8],
        start=0,
        end=180,
        fill=accent,
        width=max(2, int(size * 0.025)),
    )


def generate_icons():
    sizes = [192, 512]
    icons_dir = Path(__file__).parent.parent / "frontend" / "public"

    for size in sizes:
        img = Image.new("RGBA", (size, size), (13, 17, 23, 255))
        draw = ImageDraw.Draw(img)

        cx, cy = size // 2, size // 2

        # Fondo con gradiente sutil (simulado con círculos concéntricos)
        for i in range(10, 0, -1):
            radius = int(size * 0.48 * (i / 10))
            alpha = int(15 * (i / 10))
            draw.ellipse(
                [cx - radius, cy - radius, cx + radius, cy + radius],
                fill=(28, 35, 51, alpha),
            )

        # Círculo de acento medio-transparente
        glow_r = size * 0.47
        draw.ellipse(
            [cx - glow_r, cy - glow_r, cx + glow_r, cy + glow_r],
            outline=(88, 166, 255, 60),
            width=max(2, int(size * 0.01)),
        )

        # Dibujar lynx face
        _draw_lynx_face(draw, cx, cy, size)

        # Nombre "Lynx FC" en la parte inferior (solo en 512)
        if size >= 512:
            # Texto simple
            dot_pos = size * 0.05
            # Pequeño indicador "🐱" simplificado
            pass

        filepath = icons_dir / f"icon-{size}x{size}.png"
        img.save(filepath, "PNG")
        print(f"✅ Icono {size}x{size} guardado en {filepath}")


if __name__ == "__main__":
    from pathlib import Path
    generate_icons()
