# PyDisPix

A simple wrapper around [Python Discord Pixels](https://pixels.pythondiscord.com).

Requires Python 3.9+ (3.x where x >= 9).

Requires `requests` and `pillow` from pip.

## Example

```python
import pydispix

# Create a client with your token.
client = pydispix.Client('my-auth-token')

# Let pydispix find your token from `TOKEN` environmental variable
client = pydispix.Client()

# Download and save the canvas.
canvas = client.get_canvas()
canvas.save('canvas.png')

# And access pixels from it.
print(canvas[4, 10])

# Or just fetch a specific pixel.
print(client.get_pixel(4, 10))

# Draw a pixel.
client.put_pixel(50, 10, 'cyan')
client.put_pixel(1, 5, pydispix.Color.BLURPLE)
client.put_pixel(100, 4, '93FF00')
client.put_pixel(44, 0, 0xFF0000)
client.put_pixel(8, 54, (255, 255, 255))
```

## Auto-draw

Load an image:

```python
from PIL import Image

im = Image.open('pretty.png')
ad = pydispix.AutoDraw.load_image(client, (5, 40), im, scale=0.1)
ad.draw()
```

Or specify each pixel:

```python
ad = pydispix.AutoDraw.load(client, '''0
0
3
2
ff0000
00ff00
0000ff
ff0000
00ff00
0000ff''')
ad.draw()
```

Format of the drawing plan:

- Leftmost X coordinate
- Topmost Y coordinate
- Width
- Height
- Each pixel, left-to-right, top-to-bottom.

Auto-draw will avoid colouring already correct pixels, for efficiency.

You can also run this continually with `guard=True` which makes sure that after your image
is drawn, this keeps running to check if it haven't been tampered with, and fixes all non-matching
pixels

```py
ad.draw(guard=True)
```

## Logging

To see logs, you can set the `DEBUG` environment variable, which changes the loglevel from `logging.INFO` to `logging.DEBUG`
You can also do this manually by executing:

```py
import logging

logger = logging.getLogger("pydispix")
logger.setLevel(logging.DEBUG)
```
