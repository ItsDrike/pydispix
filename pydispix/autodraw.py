"""Tool for automatically drawing images."""
import logging
import time
from typing import Iterator

import PIL.Image

from pydispix.canvas import Pixel, Canvas
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
        resized = image.resize((width, height), PIL.Image.BILINEAR)
        data = list(resized.getdata())
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

    def _iter_coords(self) -> Iterator[tuple[int, int]]:
        """Iterate over the coordinates of the image."""
        for x in range(self.x0, self.x1):
            for y in range(self.y0, self.y1):
                yield x, y

    def draw_pixel(self, canvas: Canvas, x: int, y: int, show_progress: bool = True) -> bool:
        """
        Draw a pixel if not already drawn.

        Returns True if the pixel was not already drawn.
        """
        color = self.grid[y - self.y0][x - self.x0]
        if canvas[x, y] == color:
            logger.debug(f'Skipping already correct pixel at {x}, {y}.')
            return False
        self.client.put_pixel(x, y, color, show_progress=show_progress)
        return True

    def draw(self, guard: bool = False, guard_delay: int = 5, show_progres: bool = True):
        """Draw the pixels of the image, attempting each pixel max. once."""
        while True:
            canvas = self.client.get_canvas()
            for x, y in self._iter_coords():
                if self.draw_pixel(canvas, x, y, show_progress=show_progres):
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
