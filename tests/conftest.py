from io import BytesIO

from PIL import Image


def generate_png_bytes(width: int = 1, height: int = 1, mode: str = "P") -> bytes:
    """Generate a valid PNG image of specified size and mode."""
    # Use appropriate color for the mode
    if mode == "RGBA":
        color = (100, 100, 100, 255)
    elif mode == "P":
        color = 0  # Palette index
    else:
        color = (100, 100, 100)
    img = Image.new(mode, (width, height), color=color)
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()
