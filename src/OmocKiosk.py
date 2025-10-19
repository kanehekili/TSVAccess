'''
Created on Oct 13, 2025
We can't test that on a framebuffer on msi - use a pi!
@author: matze
'''
import requests,subprocess
from weasyprint import HTML, CSS
from pdf2image import convert_from_bytes
from PIL import Image

URL = "http://msi:5001/config"
FB = "/dev/fb0"
W, H = 1920, 1080
BPP = 16  # bits per pixel

line_length = W * (BPP // 8)
fb_size = line_length * H  # total bytes

css = CSS(string=f"""
@page {{ size: {W}px {H}px; margin: 0; }}
body {{ width: {W}px; height: {H}px; }}
""")

def killCursor():
    subprocess.run(
    ["setterm", "-cursor", "off"],
    stdout=open("/dev/tty1", "w"),
    stderr=subprocess.DEVNULL
)

def render_image():
    # Fetch HTML
    html = requests.get(URL, timeout=5).text

    # HTML → PDF
    pdf_bytes = HTML(string=html, base_url=URL).write_pdf(
        stylesheets=[css],
        media_type='screen'
    )

    # PDF → PIL image
    img = convert_from_bytes(pdf_bytes, single_file=True)[0]

    # Fit to screen
    img.thumbnail((W, H), Image.Resampling.LANCZOS)

    if img.size != (W, H):
        bg = Image.new("RGB", (W, H))
        x = (W - img.width) // 2
        y = (H - img.height) // 2
        bg.paste(img, (x, y))
        img = bg

    return img

def blit_to_fb(img):
    # Ensure 1920x1080
    if img.size != (W, H):
        img = img.resize((W, H), Image.Resampling.LANCZOS)

    # Convert to raw RGB
    rgb = img.convert("RGB").tobytes()

    # Convert RGB888 → RGB565
    data = bytearray(fb_size)  # exact fb size
    di = 0
    for i in range(0, len(rgb), 3):
        r, g, b = rgb[i], rgb[i+1], rgb[i+2]
        rgb565 = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
        data[di] = rgb565 & 0xFF
        data[di+1] = (rgb565 >> 8) & 0xFF
        di += 2

    # Write to framebuffer
    with open("/dev/fb0", "r+b") as f:
        f.write(data)


if __name__ == "__main__":
    killCursor()
    img = render_image()
    blit_to_fb(img)
