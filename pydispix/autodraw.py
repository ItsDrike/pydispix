"""Tool for automatically drawing images."""
import logging
import time

import PIL.Image

from pydispix.canvas import Pixel
from pydispix.client import Client


logger = logging.getLogger('pydispix')


class AutoDrawer:
    """Tool for automatically drawing images."""

    def __init__(
        self,
        client: Client,
        x: int, y: int,
        grid: list[list[Pixel]]
    ):
        """Store the plan."""
        self.client = client
        self.grid = grid
        # Top left coords.
        self.x0 = x
        self.y0 = y
        # Bottom right coords.
        self.x1 = x + len(self.grid[0])
        self.y1 = y + len(self.grid)

    @classmethod
    def load_image(
        cls,
        client: Client,
        xy: tuple[int, int],
        image: PIL.Image.Image,
        scale: float = 1
    ) -> 'AutoDrawer':
        """Draw from the pixels of an image."""
        if image.mode == 'RGBA':
            new_image = PIL.Image.new('RGB', image.size)
            new_image.paste(image, mask=image)
            image = new_image

        width = round(image.width * scale)
        height = round(image.height * scale)
        data = list(image.resize((width, height)).getdata())
        grid = [
            [Pixel(*pixel) for pixel in data[start:start + width]]
            for start in range(0, len(data), width)
        ]
        return cls(client, *xy, grid)

    @classmethod
    def load(cls, client: Client, data: str) -> 'AutoDrawer':
        """Draw from a string that specifies the pixels.
        `data` should be a multi-line string. The first two lines are the x
        and y coordinates of the top left of the image to draw. The second two
        are the width and height of the image. The rest of the lines are the
        pixels of the image, as hex codes (horizontal scanlines, left-to-right
        top-to-bottom).
        """
        lines = data.split('\n')
        x = int(lines.pop(0))
        y = int(lines.pop(0))
        width = int(lines.pop(0))
        height = int(lines.pop(0))
        grid = []
        for _ in range(height):
            row = []
            for _ in range(width):
                row.append(Pixel.from_hex(lines.pop(0)))
            grid.append(row)
        return cls(client, x, y, grid)

    def draw(self, *, guard: bool = False, guard_delay: int = 5, show_progress: bool = True):
        """Draw the pixels of the image."""
        while True:
            canvas = self.client.get_canvas()
            for x in range(self.x0, self.x1):
                for y in range(self.y0, self.y1):
                    dx = x - self.x0
                    dy = y - self.y0
                    color = self.grid[dy][dx]
                    if canvas[x, y] == color:
                        logger.debug(f'Skipping already correct pixel at {x}, {y}.')
                        continue
                    self.client.put_pixel(x, y, color, show_progress=show_progress, retry_on_limit=True)
                    # Putting a pixel can lead to long cooldown, so we update the canvas
                    # by making another request to fetch it
                    canvas = self.client.get_canvas()
            if not guard:
                # Check this here, to act as do-while,
                # (always run first time, only continue if this is met)
                break
            # When we're guarding we need to update canvas even if no pixel was drawn
            # because otherwise we'd be looping over same non-updated canvas forever
            # since this looping with no changes takes a long time, we should also sleep
            # to avoid needless cpu usage
            time.sleep(guard_delay)
            canvas = self.client.get_canvas()
