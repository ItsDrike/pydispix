import logging
from typing import Iterator, List, Optional, Tuple

from pydispix.autodraw import AutoDrawer
from pydispix.client import Client
from pydispix.color import Pixel

logger = logging.getLogger('pydispix')


class DistributedClient(Client):
    def __init__(
        self,
        token: Optional[str] = None,
        base_url: str = "https://pixels.pythondiscord.com/",
        *,
        total_tasks: int,
        controlled_tasks: List[int],
    ):
        """
        Add possibility to split tasks across multiple clients.

        `total_tasks` is the number of tasks our requests will be split to.

        `controlled_tasks` is the list of indices, defining which tasks are controlled here
        for example, with `total_tasks` = 10:
            First `MultiClient` (this machine): `controlled_tasks` = [0,1,2,3,4]
            Second `MultiClient` (collaborator): `controlled_tasks` = [5,6,7,8,9]

            Together, when running at the same time, and the tasks are split evenly.
            You usually want `total_tasks` to be equal to the number of your machines,
            since there is no real reason to give machines more than 1 controlled task,
            but as seen from the example, it is possible, if needed.
        """
        super().__init__(token, base_url)

        self.total_tasks = total_tasks
        self.controlled_tasks = controlled_tasks


class DistributedAutoDrawer(AutoDrawer):
    def __init__(self, client: DistributedClient, x: int, y: int, grid: List[List[Pixel]]):
        super().__init__(client, x, y, grid)
        # Redefine client for proper type highlights
        self.client: DistributedClient = client

    def _iter_coords(self) -> Iterator[Tuple[int, int]]:
        iter_coords = super()._iter_coords()
        width, _ = self.client.get_dimensions()
        for x, y in iter_coords:
            pixel_no = y * width + x
            task_no = pixel_no % self.client.total_tasks
            if task_no in self.client.controlled_tasks:
                yield x, y
            else:
                logger.debug(f"Skipping uncontrolled pixel ({x}, {y} - leaving for task {task_no}")
