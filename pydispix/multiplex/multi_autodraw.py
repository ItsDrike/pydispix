import threading
import logging

from pydispix.canvas import Pixel
from pydispix.client import Client
from pydispix.autodraw import AutoDrawer
from pydispix.multiplex.multi_client import MultiClient

logger = logging.getLogger('pydispix')


class MultiAutoDrawer():
    def __init__(
        self,
        multiplexed_client: MultiClient,
        x: int, y: int,
        grid: list[list[Pixel]]
    ):
        """
        Split the image to same sized parts of the image grid.
        This splitting is happening by lines, which means there can't be
        more requested splits preset than there are lines.

        *Note: It would be better to evenly split the matrix, but there's
        no way I'm implementing that, feel free to make a PR.
        """
        self.multiplexed_client = multiplexed_client
        self.grid = grid
        # Top left coords.
        self.x0 = x
        self.y0 = y
        # Bottom right coords.
        self.x1 = x + len(self.grid[0])
        self.y1 = y + len(self.grid)

        self.split_parts = multiplexed_client.multiplex_amt
        self.parts_to_use = multiplexed_client.multiplexed_positions

        pixels = len(self.grids) * len(self.grids[0])

        if pixels < self.parts_to_use:
            return ValueError(
                f"Unable to distribute {pixels} lines to {self.parts_to_use} even chunks, "
                "can't split to more parts than we have total pixels."
            )
        # Get needed clients to do `parts_to_use`
        self.clients = {}
        for client_id in range(self.parts_to_use):
            client = multiplexed_client.get_free_client(retry=True)
            multiplexed_client.clients[client] = False
            self.clients[client_id] = client

    @classmethod
    def load_image(cls, multiplexed_client: MultiClient, *args, **kwargs) -> "MultiAutoDrawer":
        # We have to go through `AutoDrawer` initialization here, and use the parameters from
        # the created instance to initialize out instance. This is the only way to avoid
        # too much code repetition, the initialization is relatively fast, so it shouldn't
        # be a huge issue

        mock_client = object()  # we must pass something as client, but it won't be used in any way
        auto_drawer = AutoDrawer.load_image(mock_client, *args, **kwargs)
        return cls(multiplexed_client, auto_drawer.x0, auto_drawer.y0, auto_drawer.grid)

    @classmethod
    def load(cls, multiplexed_client: MultiClient, *args, **kwargs) -> "MultiAutoDrawer":
        # Similarely to the method above, we need to initialize `AutoDrawer` here
        # to obtain parameters for our initialization

        mock_client = object()  # we must pass something as client, but it won't be used in any way
        auto_drawer = AutoDrawer.load(mock_client, *args, **kwargs)
        return cls(multiplexed_client, auto_drawer.x0, auto_drawer.y0, auto_drawer.grid)

    @staticmethod
    def _task(client: Client, x: int, y: int, color: Pixel, show_progress: bool):
        client.put_pixel(x, y, color, show_progress=show_progress, retry_on_limit=True)

    def draw(self, *, guard: bool = False, guard_delay: int = 5, show_progress: bool = True):
        canvas = self.clients[0].get_canvas()  # choose arbitrary client to fetch canvas, this doesn't take long
        threads = {}
        for x in range(self.x0, self.x1):
            for y in range(self.y0, self.y1):
                dx = x - self.x0
                dy = y - self.y0
                color = self.grid[dy][dx]
                if canvas[x, y] == color:
                    logger.debug(f"Skipping already correct pixel at {x}, {y}")
                    continue

                pixel_no = y * len(self.grid[0]) + x
                client_id = pixel_no % self.split_parts
                if client_id not in self.clients:
                    # Let other instance handle this, we don't a client with this id
                    continue
                client = self.clients[client_id]
                if client_id in threads:
                    t = threads[client_id]
                    t.join()
                    # Update canvas
                    canvas = client.get_canvas()
                    del threads[client_id]

                t = threading.Thread(target=self._task, args=client)
                threads[client_id] = t
                t.start()
