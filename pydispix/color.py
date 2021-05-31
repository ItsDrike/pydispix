import enum
import re
from typing import Tuple, Union

from pydispix.canvas import Pixel


class Color(enum.Enum):
    """A set of common colour codes."""
    BLACK = '000000'
    RED = 'FF0000'
    GREEN = '00FF00'
    BLUE = '0000FF'
    YELLOW = 'FFFF00'
    PINK = MAGENTA = 'FF00FF'
    CYAN = LIGHT_BLUE = '00FFFF'
    WHITE = 'FFFFFF'

    BLURPLE = DISCORD_BLURPLE = '5B55F2'
    DISCORD_RED = 'ED4245'
    DISCORD_GREEN = '57F287'
    DISCORD_YELLOW = 'FEE752'
    DISCORD_PINK = 'EB458E'
    DISCORD_BLACK = '23272A'


ResolvableColor = Union[int, str, Tuple[int, int, int], Color, Pixel]


def parse_color(value: ResolvableColor) -> str:
    """Parse a colour to a hex string.
    Accepts integers, strings and instances of the Colour enum.
    """
    if isinstance(value, int):
        if value >= 0 and value <= 0xFFFFFF:
            return f'{value:0>6x}'
    elif isinstance(value, str):
        neat_value = value.lstrip('#').upper()
        if re.match('[0-9A-F]{6}', neat_value):
            return neat_value
        if value.upper() in Colour.__members__:
            return Colour.__members__[value.upper()].value
    elif isinstance(value, Color):
        return value.value
    elif isinstance(value, Pixel):
        # Remove leading "#".
        return str(value)[1:]
    elif isinstance(value, tuple):
        if len(value) == 3:
            for col_byte in value:
                if not isinstance(col_byte, int):
                    raise TypeError(f"Expected tuple of 3 integers, found {col_byte.__class__.__name__}")
                if col_byte < 0 or col_byte > 255:
                    raise ValueError(f"Colors in rgb tuple must follow 0 <= x <= 255, got {col_byte}")

        return f"{value[0]:0>2x}{value[1]:0>2x}{value[2]:0>2x}"

    raise ValueError(f'Invalid colour "{value}".')


Colour = Color
parse_colour = parse_color
