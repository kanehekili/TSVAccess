'''
Created on Oct 26, 2025

@author: matze
'''
import requests
from io import BytesIO
from PIL import Image

URL = "http://msi:5001/omocszk"  # Flask route serving PIL image
FB = "/dev/fb0"
W, H = 1920, 1080
BPP = 16  # bits per pixel

line_length = W * (BPP // 8)
fb_size = line_length * H  # total bytes


def render_image():
    # Fetch image directly from Flask
    resp = requests.get(URL, timeout=5)
    img = Image.open(BytesIO(resp.content))

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
    # Ensure exact framebuffer size
    if img.size != (W, H):
        img = img.resize((W, H), Image.Resampling.LANCZOS)

    # Convert RGB888 → RGB565
    rgb = img.convert("RGB").tobytes()
    data = bytearray(fb_size)
    di = 0
    for i in range(0, len(rgb), 3):
        r, g, b = rgb[i], rgb[i+1], rgb[i+2]
        rgb565 = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
        data[di] = rgb565 & 0xFF
        data[di+1] = (rgb565 >> 8) & 0xFF
        di += 2

    with open(FB, "r+b") as f:
        f.write(data)

if __name__ == "__main__":
    img = render_image()
    blit_to_fb(img)
