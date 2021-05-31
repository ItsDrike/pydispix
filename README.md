# PyDisPix

[![made-with-python](https://img.shields.io/badge/Made%20with-Python%203.8+-ffe900.svg?longCache=true&style=flat-square&colorB=00a1ff&logo=python&logoColor=88889e)](https://www.python.org/)
[![MIT](https://img.shields.io/badge/Licensed%20under-MIT-red.svg?style=flat-square)](./LICENSE)
[![Validation](https://github.com/ItsDrike/pydispix/actions/workflows/validation.yml/badge.svg)](https://github.com/ItsDrike/pydispix/actions/workflows/validation.yml)

A simple wrapper around [Python Discord Pixels](https://pixels.pythondiscord.com).
Check it out on [PyPI](https://pypi.org/project/pydispix/).

## Examples

### Main usage

```py
import pydispix

# Create a client with your token.
client = pydispix.Client('my-auth-token')

# Fetch a specific pixel.
print(client.get_pixel(4, 10))

# Draw a pixel.
client.put_pixel(50, 10, 'cyan')
client.put_pixel(1, 5, pydispix.Color.BLURPLE)
client.put_pixel(100, 4, '93FF00')
client.put_pixel(44, 0, 0xFF0000)
client.put_pixel(8, 54, (255, 255, 255))
```

### Canvas

We can also work with the whole pixels canvas

```py
# Fetch the canvas
canvas = client.get_canvas()

# Show the canvas using matplotlib, this will include coordinates
canvas.show()

# Save the canvas to a file
canvas.save('canvas.png')

# And access pixels from it.
print(canvas[4, 10])
```

### Draw image from png

Load an image:

```py
from PIL import Image

im = Image.open('pretty.png')
ad = pydispix.AutoDrawer.load_image(client, (5, 40), im, scale=0.1)
ad.draw()
```

Auto-draw will avoid colouring already correct pixels, for efficiency.

You can also run this continually with `guard=True` which makes sure that after your image
is drawn, this keeps running to check if it haven't been tampered with, and fixes all non-matching
pixels.

```py
ad.draw(guard=True, guard_delay=2)
```

`guard_delay` is the delay between each full iteration of all pixels. We need to wait since
looping without any changes is almost instant in python, and we don't want to put cpu through that
stress for no reason

### Draw multiple images

You can also draw multiple images one by one

```py
from PIL import Image
from pydispix import Client, AutoDrawer

client = Client("pixels_api_token")

positions = [(52, 14), (120, 54)]
images = [Image("img1.png"), Image("img2.png")]
scales = [0.5, 1]

ad = AutoDrawer.load_images(client, positions, images, scales, one_by_one=True)
ad.draw()
```

This will proceed to start drawing the images in order they were passed. You could also
set `one_by_one` to `False`, which would cause the images to instead be drawn by pixel
from each, i.e. 1st pixel from img1, 1st pixel from img2, 2nd from img1, 2nd from img2, ...

### Collaborate on image drawing

You can share the load of drawing a single image between multiple joined clients.
This will mean each client will only ever work on it's part of given image, both when guarding and drawing it.

```py
from PIL import Image
from pydispix import DistributedClient, DistributedAutoDrawer

# First machine
multi_client = DistributedClient('pixels_api_key', total_tasks=2 ,controlled_tasks=[0])
# Second machine
#multi_client = MultiClient('pixels_api_key2', total_tasks=2 ,controlled_tasks=[1])

image = Image.open('my_img.png')
auto_drawer = DistributedAutoDrawer.load_image(multi_client, (2, 10), image, scale=0.8)
auto_drawer.draw(guard=True)
```

`total_tasks` is the number of clients you will have in total, i.e. the number of workers
for shared tasks. It's how many groups will the shared pixels be split into.

`controlled_tasks` are the groups controlled by this `MultiClient` instance. This is usually
only 1 task, but you can specify multiple tasks and split the code further.

### Churches

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
avoid `client.run_task()` since it doesn't handle any errors specific to the used church,
`client.run_tasks()` will handle these errors cleanly and log the problems if some ocurred.

Note: `client.run_tasks()` only handles known exceptions, there might still be some exceptions that a church
could raise which aren't handled. If you manage to find one make sure to file an issue about it.

Example of safe continual script to keep running church tasks on your machine:

```py
import pickle
import time
from pydispix.churches import RickChurchClient

client = RickChurchClient(pixels_api_token, rick_church_api_token)

exception_amt = 0
while True:
    try:
        client.run_tasks(show_progress=True)
    except Exception as exc:
        print(f"Exception ocurred: {exc} (#{exception_amt})")
        with open(f"exception{exception_amt}.pickle", "wb") as f:
            pickle.dump(exc, f)
        exception_amt += 1
        time.sleep(5)
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

### Other churches

You can also implement your own church according to it's specific API requirements, if you're
interested in doing this, check the [church.py](pydispix/church.py) and how the specific churches
are implemented using it: [churches.py](pydispix/churches.py).

If you do end up implementing it, feel free to also open a pull request and add it, if the church
is popular enough, you have a good chance of it being added to official `pydispix`.

### Progress bars

Every request that has rate limits can now display a progress bar while it's sleeping on cooldown:

```py
pixel = client.get_pixel(0, 0, show_progress=True)
canvas = client.get_canvas(show_progress=True)
client.put_pixel(52, 10, "FFFFFF", show_progress=True)
```

https://user-images.githubusercontent.com/20902250/119607092-418e4200-bde3-11eb-9ac5-4e455ffd47c2.mp4

### Logging

To see logs, you can set the `DEBUG` environment variable, which changes the loglevel from `logging.INFO` to `logging.DEBUG`
You can also do this manually by executing:

```py
import logging

logger = logging.getLogger("pydispix")
logger.setLevel(logging.DEBUG)
```
