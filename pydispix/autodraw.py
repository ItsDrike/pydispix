"""Tool for automatically drawing images."""
import logging
import time
from typing import Iterator, List, Optional, Tuple

import PIL.Image

from pydispix.canvas import Canvas, Pixel
from pydispix.client import Client
from pydispix.errors import OutOfBoundaries

logger = logging.getLogger('pydispix')


class AutoDrawer:
    """Tool for automatically drawing images."""

    def __init__(
        self,
        client: Client,
        x: int, y: int,
        grid: List[List[Pixel]]
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

        # Make sure we're within canvas boundaries
        canvas_width, canvas_height = canvas_size = self.client.get_dimensions()
        image_width, image_height = image_size = len(self.grid[0]), len(self.grid)
        if image_width > canvas_width or image_height > canvas_height:
            raise OutOfBoundaries(f"Can't draw picture bigger than the canvas ({image_size} > {canvas_size})")

    @staticmethod
    def _grid_from_img(
        image: PIL.Image.Image,
        scale: float = 1
    ):
        if image.mode == 'RGBA':
            new_image = PIL.Image.new('RGB', image.size)
            new_image.paste(image, mask=image)
            image = new_image

        width = round(image.width * scale)
        height = round(image.height * scale)

        if scale != 1:
            image = image.resize((width, height), PIL.Image.BILINEAR)

        data = list(image.getdata())
        grid = [
            [Pixel(r, g, b) for r, g, b in data[start:start + width]]
            for start in range(0, len(data), width)
        ]
        return grid

    @classmethod
    def load_image(
        cls,
        client: Client,
        xy: Tuple[int, int],
        image: PIL.Image.Image,
        scale: float = 1
    ) -> 'AutoDrawer':
        """Draw from the pixels of an image."""
        grid = cls._grid_from_img(image, scale)
        return cls(client, *xy, grid)

    def _iter_coords(self) -> Iterator[Tuple[int, int]]:
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

    def draw(self, guard: bool = False, guard_delay: int = 5, show_progress: bool = True):
        """Draw the pixels of the image, attempting each pixel max. once."""
        canvas = self.client.get_canvas()
        while True:
            for x, y in self._iter_coords():
                if self.draw_pixel(canvas, x, y, show_progress=show_progress):
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


class MultiAutoDrawer:
    """Tool for automatically drawing set of images"""
    def __init__(
        self,
        client: Client,
        positions: List[Tuple[int, int]],
        grids: List[List[List[Pixel]]],
        one_by_one: bool = True
    ):
        self.client = client
        self.drawers = [
            AutoDrawer(client, *position, grid)
            for position, grid in zip(positions, grids)
        ]
        self.positions_generator = self._one_by_one_positions if one_by_one else self._per_pixel_positions

    @classmethod
    def load_images(
        cls,
        client: Client,
        positions: List[Tuple[int, int]],
        images: List[PIL.Image.Image],
        scales: Optional[List[int]] = None,
        one_by_one: bool = True
    ) -> "MultiAutoDrawer":
        """Draw from pixels on the images."""
        if scales is None:
            # Default all scales to 1
            scales = [1 for _ in images]

        grids = [
            AutoDrawer._grid_from_img(image, scale)
            for image, scale in zip(images, scales)
        ]

        return cls(client, positions, grids, one_by_one)

    def _one_by_one_positions(self) -> Iterator[Tuple[AutoDrawer, Tuple[int, int]]]:
        """
        Return iterator of the pixels to check for the passed set of grids (images).
        This will one by one through the individual images. This allows for prioritizing
        certain images over others.
        """
        coord_generators = [drawer._iter_coords() for drawer in self.drawers]
        for drawer, coord_generator in zip(self.drawers, coord_generators):
            for x, y in coord_generator:
                yield drawer, (x, y)

    def _per_pixel_positions(self) -> Iterator[Tuple[AutoDrawer, Tuple[int, int]]]:
        """
        This is similar to `_one_by_one_positions`, except instead of iterating one by one,
        we are instead iterating through individual pixels, i.e. all 1st pixels from
        all images, all 2nd pixels, etc.
        """
        coord_generators = [drawer._iter_coords() for drawer in self.drawers]

        # Keep track of which drawers are already depleted
        depleted = {drawer: False for drawer in self.drawers}
        # Keep running as long as we have any non-depleted drawers
        while any(is_depleted is False for is_depleted in depleted.values()):
            for drawer, coord_generator in zip(self.drawers, coord_generators):
                try:
                    x, y = next(coord_generator)
                except StopIteration:
                    # If we already depleted pixels from this drawer, just ignore
                    # it and move on to another one
                    depleted[drawer] = True
                    continue
                yield drawer, (x, y)

    def draw(
        self,
        guard: bool = False,
        guard_delay: int = 5,
        show_progress: bool = True,
    ):
        canvas = self.client.get_canvas()

        while True:
            for drawer, (x, y) in self.positions_generator():
                if drawer.draw_pixel(canvas, x, y, show_progress=show_progress):
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
