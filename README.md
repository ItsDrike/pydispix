# DPYPX

A simple wrapper around [Python Discord Pixels](https://pixels.pythondiscord.com).

Requires Python 3.9+ (3.x where x >= 9).

Requires `pillow` and `aiohttp` from pip.

## Example

```python
import dpypx

# Create a client with your token.
client = dpypx.Client('my-auth-token')

# You can also set a save file to store ratelimit data between reboots.
client = dpypx.Client('my-auth-token', ratelimit_save_file='ratelimits.json')

# Download and save the canvas.
canvas = await client.get_canvas()
canvas.save('canvas.png')

# And access pixels from it.
print(canvas[4, 10])

# Or just fetch specific pixels.
print(await client.get_pixel(4, 10))

# Draw a pixel.
await client.put_pixel(50, 10, 'cyan')
await client.put_pixel(1, 5, dpypx.Colour.BLURPLE)
await client.put_pixel(100, 4, '93FF00')
await client.put_pixel(44, 0, 0xFF0000)

# Close the connection.
await client.close()
```

## Auto-draw

Load an image:

```python
from PIL import Image

im = Image.open('pretty.png')
ad = dpypx.AutoDrawer.load_image(client, (5, 40), im, scale=0.1)
await ad.draw()
```

Or specify each pixel:

```python
ad = dpypx.AutoDraw.load(client, '''0
0
3
2
ff0000
00ff00
0000ff
ff0000
00ff00
0000ff''')
await ad.draw()
```

Format of the drawing plan:

- Leftmost X coordinate
- Topmost Y coordinate
- Width
- Height
- Each pixel, left-to-right, top-to-bottom.

Auto-draw will avoid colouring already correct pixels, for efficiency.

## Logging

To see logs:

```python
import logging

logging.basicConfig(level=logging.INFO)
```

Too see more logs:
```python
logging.basicConfig(level=logging.DEBUG)
```

To see fewer logs:
```python
logging.basicConfig(level=logging.WARNING)
```
