import time
import board
import neopixel

# === НАСТРОЙКИ ===
PIXEL_PIN = board.D18        # GPIO18 (Pin 12)
NUM_PIXELS = 30              # Количество светодиодов
BRIGHTNESS = 0.3             # 0.0 - 1.0
ORDER = neopixel.GRB

pixels = neopixel.NeoPixel(
    PIXEL_PIN,
    NUM_PIXELS,
    brightness=BRIGHTNESS,
    auto_write=False,
    pixel_order=ORDER
)

def color_wipe(color, delay=0.02):
    for i in range(NUM_PIXELS):
        pixels[i] = color
        pixels.show()
        time.sleep(delay)

def rainbow_cycle(wait=0.01):
    for j in range(255):
        for i in range(NUM_PIXELS):
            rc_index = (i * 256 // NUM_PIXELS) + j
            pixels[i] = wheel(rc_index & 255)
        pixels.show()
        time.sleep(wait)

def wheel(pos):
    if pos < 85:
        return (255 - pos * 3, pos * 3, 0)
    elif pos < 170:
        pos -= 85
        return (0, 255 - pos * 3, pos * 3)
    else:
        pos -= 170
        return (pos * 3, 0, 255 - pos * 3)

try:
    while True:
        color_wipe((255, 0, 0))
        color_wipe((0, 255, 0))
        color_wipe((0, 0, 255))
        rainbow_cycle()
except KeyboardInterrupt:
    pixels.fill((0, 0, 0))
    pixels.show()