from io import BytesIO

from PIL import Image


def process_photo(photo_data: bytes, max_size: tuple[int, int] = (160, 160), bit_depth: int = 8) -> bytes:
    """Resize and convert uploaded image to PNG format."""
    image = Image.open(BytesIO(photo_data))
    width = image.width
    resampling = Image.Resampling.LANCZOS if width > max_size[0] else Image.Resampling.BICUBIC
    resized = image.resize(max_size, resample=resampling)
    converted = resized.convert("P") if bit_depth == 8 else resized
    buffer = BytesIO()
    converted.save(buffer, format="PNG")
    return buffer.getvalue()
