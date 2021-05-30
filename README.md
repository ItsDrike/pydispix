# PyDisPix

A simple wrapper around [Python Discord Pixels](https://pixels.pythondiscord.com).

Requires Python 3.8+ (3.x where x >= 8).

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
client.run_task(show_progress=True)
```

Church of SQLite is also supported, and they don't require an API key, it is free for everyone:

```py
from pydispix.churches import SQLiteChurchClient

client = SQLiteChurchClient(pixels_api_token)
client.run_task()
```

### Continually running church tasks

If you wish to keep running church tasks continually in a loop, make sure to use `client.run_tasks()`,
don't use `client.run_task()` since it doesn't have any error handling. Churches often raise errors
in certain situations, and using `client.run_tasks()` will ensure they're handled cleanly.

Note: `client.run_tasks()` only handles known exceptions, there might still be some exceptions that a
church could raise which aren't handled. If you manage to find one make sure to file an issue about it.

Example of safe continual script to keep running church tasks on your machine:

```py
import pickle
from pydispix.churches import RickChurchClient

client = RickChurchClient(pixels_api_token, rick_church_api_token)

exception_amt = 0
while True:
    try:
        client.run_tasks(show_progress=True)
    except KeyboardInterrupt as exc:
        print(exceptions)
        raise exc
    except Exception as exc:
        print(f"Exception ocurred: {exc} (#{exception_amt})")
        with open(f"exception{exception_amt}.pickle", "wb") as f:
            pickle.dump(exc, f)
        exception_amt += 1
```

There is still exception handling here, but it shouldn't capture any, it's only here since you'll
likely not be there to monitor the process all the time, so even in the rare case that something 
were to occur, the program will keep running and the exception will stored with pickle.

If you see that this happened (if you find `exceptionX.pickle` files in your working directory),
load the pickled exception and examine what exactly happened. Upload the traceback with the issue.

```py
import pickle

with open("exception0.pickle", "rb") as f:
  exc = pickle.load(f)

raise exc
```

**Important: do not upload the pickle file anywhere, it contains the request, which includes your
API keys, uploading the pickled file would inevitable lead to leaked API key.**

### Custom churches

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
