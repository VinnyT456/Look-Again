import sys, numpy as np
from PIL import Image
src, imageset, iconset, preview = sys.argv[1:5]
img = Image.open(src).convert("RGB")
a = np.asarray(img).astype(float)
H, W, _ = a.shape
bg = np.array([225, 212, 249.0])

# Soft alpha matte from distance to the lavender background.
d = np.sqrt(((a - bg) ** 2).sum(-1))
alpha = np.clip((d - 10) / 45, 0, 1)
safe = np.maximum(alpha, 1e-3)[..., None]
fg = np.clip((a - (1 - alpha[..., None]) * bg) / safe, 0, 255)

# Lighten the purple ring + handle (outside the teal lens) for dark surfaces.
cx, cy, r = 657, 493, 368
yy, xx = np.mgrid[0:H, 0:W]
outside = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) > r
ring = np.array([84, 38, 134.0])
purple = np.clip(1 - np.sqrt(((fg - ring) ** 2).sum(-1)) / 90, 0, 1) * outside
light_ring = np.array([184, 160, 236.0])
fg_dark = fg * (1 - purple[..., None]) + light_ring * purple[..., None]

def comp(fgc, bgc):
    return (fgc * alpha[..., None] + np.array(bgc, float) * (1 - alpha[..., None])).clip(0, 255).astype(np.uint8)

light = img
dark = Image.fromarray(comp(fg_dark, [34, 22, 58]))
for name, im in [("FaceCheckMagnifier", light), ("FaceCheckMagnifier-dark", dark)]:
    for scale, px in [(1, 112), (2, 224), (3, 336)]:
        suffix = "" if scale == 1 else f"@{scale}x"
        im.resize((px, px), Image.LANCZOS).save(f"{imageset}/{name}{suffix}.png", optimize=True)

# App icon variants (1024, no alpha for light/tinted; dark may be transparent).
img.resize((1024, 1024), Image.LANCZOS).save(f"{iconset}/AppIcon.png", optimize=True)
rgba = np.dstack([fg_dark, alpha * 255]).clip(0, 255).astype(np.uint8)
Image.fromarray(rgba, "RGBA").resize((1024, 1024), Image.LANCZOS).save(f"{iconset}/AppIcon-Dark.png", optimize=True)
# Tinted: luminance only, so give the lens a darker value than the ring.
lens = (~outside)[..., None]
fg_tint = np.where(lens, fg_dark * 0.55, fg_dark)
gray = Image.fromarray(comp(fg_tint, [0, 0, 0])).convert("L")
gray.resize((1024, 1024), Image.LANCZOS).save(f"{iconset}/AppIcon-Tinted.png", optimize=True)

# Preview sheet: light tile, dark tile, dark icon over gray, tinted.
tiles = [light, dark,
         Image.alpha_composite(Image.new("RGBA", (W, H), (60, 60, 64, 255)), Image.fromarray(rgba, "RGBA")).convert("RGB"),
         gray.convert("RGB")]
sheet = Image.new("RGB", (800, 200), "white")
for i, t in enumerate(tiles):
    sheet.paste(t.resize((200, 200)), (200 * i, 0))
sheet.save(preview)
