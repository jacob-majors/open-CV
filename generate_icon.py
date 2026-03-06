"""Generates the Open CV app icon as resources/icon.png"""
import math
from PIL import Image, ImageDraw, ImageFilter

SIZE = 512
OUT = "resources/icon.png"


def draw_icon(size=SIZE):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    s = size

    # Background circle — dark charcoal
    margin = s * 0.04
    d.ellipse([margin, margin, s - margin, s - margin], fill="#1e1e1e")

    # Outer ring — green
    ring = s * 0.03
    d.ellipse(
        [margin, margin, s - margin, s - margin],
        outline="#3d9f5e", width=int(ring),
    )

    # Eye whites — big almond shape
    cx, cy = s / 2, s / 2
    eye_w = s * 0.72
    eye_h = s * 0.38
    eye_top = cy - eye_h / 2
    eye_bot = cy + eye_h / 2
    eye_left = cx - eye_w / 2
    eye_right = cx + eye_w / 2

    # Draw eye as a pointed oval using polygon approximation
    points = []
    steps = 120
    for i in range(steps):
        t = 2 * math.pi * i / steps
        # Squish vertically at the ends to make it almond-shaped
        x = cx + (eye_w / 2) * math.cos(t)
        # taper height towards the edges
        taper = 1 - abs(math.cos(t)) ** 2.5
        y = cy + (eye_h / 2) * math.sin(t) * taper
        points.append((x, y))

    d.polygon(points, fill="#e8e8e8")

    # Iris — teal/green circle
    iris_r = s * 0.18
    d.ellipse(
        [cx - iris_r, cy - iris_r, cx + iris_r, cy + iris_r],
        fill="#2d7a52",
    )

    # Pupil — dark
    pupil_r = s * 0.10
    d.ellipse(
        [cx - pupil_r, cy - pupil_r, cx + pupil_r, cy + pupil_r],
        fill="#111111",
    )

    # Aperture blades on pupil
    blade_count = 6
    blade_outer = s * 0.095
    blade_inner = s * 0.04
    for i in range(blade_count):
        angle = 2 * math.pi * i / blade_count
        ox = cx + blade_outer * math.cos(angle)
        oy = cy + blade_outer * math.sin(angle)
        a1 = angle + math.pi / blade_count
        a2 = angle - math.pi / blade_count
        p1 = (cx + blade_inner * math.cos(a1), cy + blade_inner * math.sin(a1))
        p2 = (cx + blade_inner * math.cos(a2), cy + blade_inner * math.sin(a2))
        d.polygon([(ox, oy), p1, p2], fill="#3d9f5e")

    # Lens reflection dot
    ref_x = cx - iris_r * 0.45
    ref_y = cy - iris_r * 0.45
    ref_r = s * 0.025
    d.ellipse(
        [ref_x - ref_r, ref_y - ref_r, ref_x + ref_r, ref_y + ref_r],
        fill=(255, 255, 255, 180),
    )

    # Slight blur for smoothness
    img = img.filter(ImageFilter.SMOOTH)
    return img


if __name__ == "__main__":
    import os
    os.makedirs("resources", exist_ok=True)

    icon = draw_icon(SIZE)
    icon.save(OUT)
    print(f"Saved {OUT}")

    # Also save smaller sizes for tray
    for sz in [64, 128, 256]:
        resized = draw_icon(sz)
        path = f"resources/icon_{sz}.png"
        resized.save(path)
        print(f"Saved {path}")
