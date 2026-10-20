"""Writes the app's color sets into Assets.xcassets (light, dark, and Increase Contrast variants)."""
import json, os, sys

catalog = sys.argv[1]

def comp(hexv, alpha=1.0):
    r, g, b = hexv[0:2], hexv[2:4], hexv[4:6]
    return {"color-space": "srgb", "components": {"red": f"0x{r}", "green": f"0x{g}", "blue": f"0x{b}", "alpha": f"{alpha:.3f}"}}

def colorset(name, light, dark=None, light_hc=None, dark_hc=None):
    colors = [{"idiom": "universal", "color": comp(*light)}]
    if light_hc:
        colors.append({"idiom": "universal", "appearances": [{"appearance": "contrast", "value": "high"}], "color": comp(*light_hc)})
    if dark:
        colors.append({"idiom": "universal", "appearances": [{"appearance": "luminosity", "value": "dark"}], "color": comp(*dark)})
    if dark_hc:
        colors.append({"idiom": "universal", "appearances": [{"appearance": "luminosity", "value": "dark"}, {"appearance": "contrast", "value": "high"}], "color": comp(*dark_hc)})
    path = os.path.join(catalog, f"{name}.colorset")
    os.makedirs(path, exist_ok=True)
    with open(os.path.join(path, "Contents.json"), "w") as f:
        json.dump({"colors": colors, "info": {"author": "xcode", "version": 1}}, f, indent=2)

def c(h, a=1.0): return (h, a)

# Brand
colorset("NorthwesternPurple", c("4E2A84"))
colorset("NorthwesternPurpleDark", c("3D2068"))
colorset("NorthwesternPurpleTint", c("EADDFF"), c("3A2A55"))

# Verdict hues (icons, borders, marks)
colorset("VerdictReal", c("16A34A"))
colorset("VerdictTampered", c("D97706"))
colorset("VerdictAI", c("DC2626"))

# Verdict text: AA on their tinted backgrounds, stronger under Increase Contrast
colorset("VerdictRealText", c("166534"), c("4ADE80"), c("14532D"), c("BBF7D0"))
colorset("VerdictTamperedText", c("92400E"), c("FBBF24"), c("78350F"), c("FDE68A"))
colorset("VerdictAIText", c("B91C1C"), c("F87171"), c("7F1D1D"), c("FECACA"))

# Verdict backgrounds: tint drops away under Increase Contrast
colorset("VerdictRealBackground", c("ECFDF5"), c("064E3B", 0.35), c("FFFFFF"), c("1C1C1E"))
colorset("VerdictTamperedBackground", c("FFFBEB"), c("78350F", 0.35), c("FFFFFF"), c("1C1C1E"))
colorset("VerdictAIBackground", c("FEF2F2"), c("7F1D1D", 0.35), c("FFFFFF"), c("1C1C1E"))

# Photo overlays: fixed, read the same on any image
colorset("HotspotStroke", c("EF4444"))
colorset("HotspotLabel", c("B91C1C"))
colorset("CleanBadge", c("15803D"))
