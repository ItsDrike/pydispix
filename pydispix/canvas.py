
import PIL.Image


class Pixel:
    """A single pixel of the canvas."""
    def __init__(self, red: int, green: int, blue: int):
        """Store the pixel."""
        self.red = red
        self.green = green
        self.blue = blue

    @classmethod
    def from_hex(cls, hex: str) -> "Pixel":
        """Load a pixel colour from a hex string."""
        hex = hex.removeprefix('#')
        return cls(*(int(hex[i:i + 2], 16) for i in range(0, 6, 2)))

    @property
    def triple(self) -> tuple[int, int, int]:
        """Get the pixel as an RGB triple."""
        return self.red, self.green, self.blue

    @property
    def hex_str(self) -> str:
        """Get the pixel as a hex string."""
        return f'#{self.red:0>2x}{self.green:0>2x}{self.blue:0>2x}'

    @property
    def hex_int(self) -> int:
        """Get the pixel as a 3-byte int."""
        return self.red << 16 | self.green << 8 | self.blue

    def __str__(self) -> str:
        """Get the pixel as a hex string."""
        return self.hex_str

    def __int__(self) -> int:
        """Get the pixel as a 3-byte int."""
        return self.hex_int

    def __eq__(self, other: "Pixel") -> bool:
        """Check if this pixel holds the same value as another."""
        return self.triple == other.triple

    def __repr__(self):
        return f"<Pixel(triple={self.triple}, hex={self.hex_str})>"


class Canvas:
    """container for all the pixels on a canvas."""
    def __init__(self, size: tuple[int, int], data: bytes):
        """Parse the raw canvas data."""
        self.width, self.height = size

        pixels = []
        for start_idx in range(0, len(data), 3):
            pixels.append(Pixel(*data[start_idx:start_idx + 3]))

        self.grid = [
            pixels[row * self.width:(row + 1) * self.width]
            for row in range(self.height)
        ]
        self.raw = data
        self.image = PIL.Image.frombytes('RGB', size, data)

    def __getitem__(self, xy: tuple[int, int]):
        """Get a pixel by coordinates."""
        x, y = xy
        return self.grid[y][x]

    def show(self):
        """Display the image."""
        self.image.show()

    def save(self, path: str):
        """Save the image to a given file."""
        self.image.save(path)
