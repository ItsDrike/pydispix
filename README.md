# PyDisPix

A simple wrapper around [Python Discord Pixels](https://pixels.pythondiscord.com).

Requires Python 3.7+ (3.x where x >= 7).

Requires `requests`, `pillow` and `matplotlib` from pip.

## Example

```py
import pydispix

# Create a client with your token.
client = pydispix.Client('my-auth-token')

# Let pydispix find your token from `TOKEN` environmental variable
client = pydispix.Client()

# Fetch the canvas
canvas = client.get_canvas()

# Show the canvas using PIL
canvas.show()

# Show the canvas using matplotlib, this will include coordinates
canvas.mpl_show()

# Save the canvas to a file
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

We can also display the image with pillow

```py
canvas = client.get_canvas()
canvas.show()
```

Or we can display with `matplotlib` to see it with coordinates

```py
canvas = client.get_canvas()
canvas.mpl_show()
```

## Auto-draw

Load an image:

```py
from PIL import Image

im = Image.open('pretty.png')
ad = pydispix.AutoDrawer.load_image(client, (5, 40), im, scale=0.1)
ad.draw()
```

To prefer fixing existing pixels to placing new ones:

```py
ad = pydispix.AutoDrawer.load(client, '''0
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
pixels.

```py
ad.draw(guard=True, guard_delay=2)
```

Guard delay is the delay between each full iteration of all pixels. We need to wait since
looping without any changes is almost instant in python, and we don't want to put cpu through that
stress for no reason

## Churches

Churches are groups of people collaborating on some image, or set of images on the canvas.
It's basically a big botnet of people. Most popular church is currently the
[Church Of Rick](https://pixel-tasks.scoder12.repl.co/). Churches provide it's members with
tasks to fill certain pixels, and the members finish those tasks and report it back to the church.
This is how you run a single task like this with Church of Rick:

```py
from pydispix.churches import RickChurchClient

client = RickChurchClient(pixels_api_token, rick_church_api_token)
client.run_task()
```

Church of SQLite is also supported, and they don't require an API key, it is free for everyone:

```py
from pydispix.churches import SQLiteChurchClient

client = SQLiteChurchClient(pixels_api_token)
client.run_task()
```

You can also implement your own church according to it's specific API requirements, if you're
interested in doing this, check the [church.py](pydispix/church.py) and how the specific churches
are implemented using it: [churches.py](pydispix/churches.py).

## Progress bars

Every request that has rate limits can now display a progress bar while it's sleeping on cooldown:

```py
pixel = client.get_pixel(0, 0, show_progress=True)
canvas = client.get_canvas(show_progress=True)
client.put_pixel(52, 10, "FFFFFF", show_progress=True)
```

https://user-images.githubusercontent.com/20902250/119607092-418e4200-bde3-11eb-9ac5-4e455ffd47c2.mp4

## Logging

To see logs, you can set the `DEBUG` environment variable, which changes the loglevel from `logging.INFO` to `logging.DEBUG`
You can also do this manually by executing:

```py
import logging

logger = logging.getLogger("pydispix")
logger.setLevel(logging.DEBUG)
```
