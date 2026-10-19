"""Generate the Venus-8 custom multiresolution Windows icon from vector-style Pillow drawing.

The icon is an original simplified analog synthesizer: timber sides, black
control panel, copper knobs, amber LEDs and an ivory piano keyboard.
"""
from pathlib import Path
import math

from PIL import Image, ImageDraw, ImageFont


def draw_icon(size=512):
    scale = size / 512.0
    im = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((7, 32, 505, 478), radius=48,
                        fill="#0b1117", outline="#f39b4e", width=8)
    for x1, x2 in [(15, 59), (452, 496)]:
        d.rounded_rectangle((x1, 41, x2, 467), radius=17, fill="#8c4b28")
        for x in range(x1+5, x2, 7):
            d.line((x, 45, x, 461), fill="#aa6436", width=2)
    d.rounded_rectangle((64, 44, 448, 278), radius=12,
                        fill="#171b20", outline="#4f5458", width=3)
    d.rectangle((75, 57, 434, 92), fill="#2b2521")
    d.rounded_rectangle((89, 62, 271, 86), radius=9, fill="#cb7137")
    # Little lit status indicators.
    for x in (341, 369, 397, 425):
        d.ellipse((x-6, 68, x+6, 80), fill="#fca14d")
    # Two rows of physical silver/black rotary knobs.
    for y in (142, 219):
        for x in (121, 211, 301, 391):
            d.ellipse((x-31, y-30, x+31, y+32), fill="#07090c",
                      outline="#b97a4a", width=5)
            d.ellipse((x-23, y-24, x+23, y+23), fill="#353940",
                      outline="#7c858a", width=4)
            d.ellipse((x-15, y-16, x+15, y+14), fill="#181e26")
            d.line((x, y, x-9, y-17), fill="#ffaf5a", width=6)
    # Large piano keyboard recognizable even at taskbar 16px.
    d.rounded_rectangle((63, 293, 448, 462), radius=7, fill="#111215")
    n=13
    step=372/n
    for i in range(n):
        l=69+i*step
        d.rectangle((round(l), 301, round(l+step-2), 453),
                    fill="#f2e8d6", outline="#737174", width=1)
    # Black keys sit above the white keys.
    for i in range(n-1):
        if i % 7 in (2, 6):
            continue
        left=69+(i+1)*step-step*.26
        d.rounded_rectangle((round(left), 300, round(left+step*.53), 395),
                            radius=3, fill="#10161e", outline="#41444a", width=2)
    d.line((68, 453, 442, 453), fill="#f2a351", width=4)
    return im.resize((size, size), Image.Resampling.LANCZOS)


def main():
    out=Path("assets")
    out.mkdir(parents=True,exist_ok=True)
    image=draw_icon()
    image.save(out/"venus-8.png")
    image.save(out/"venus-8.ico", format="ICO",
               sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),
                      (128,128),(256,256)])
    print("Created",out/"venus-8.ico")


if __name__=="__main__":
    main()
