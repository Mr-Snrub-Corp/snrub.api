from io import BytesIO

from PIL import Image

from app.services.image_processing import process_photo
from tests.conftest import generate_png_bytes


class TestProcessPhoto:
    """Unit tests for process_photo function."""

    def test_resize_large_image_to_max_size(self):
        """A 320x320 image should be resized to 160x160."""
        large_image = generate_png_bytes(320, 320)

        result = process_photo(large_image)

        # Verify the output dimensions
        result_image = Image.open(BytesIO(result))
        assert result_image.size == (160, 160)

    def test_already_correct_size_and_format_returns_unchanged(self):
        """A 160x160 8-bit PNG should return the exact same bytes."""
        correct_image = generate_png_bytes(160, 160)

        result = process_photo(correct_image)

        assert result == correct_image

    def test_converts_to_8bit_png(self):
        """An RGBA (32-bit) image should be converted to 8-bit palette PNG."""
        rgba_image = generate_png_bytes(160, 160, mode="RGBA")

        result = process_photo(rgba_image)

        # Verify the output is 8-bit palette mode
        result_image = Image.open(BytesIO(result))
        assert result_image.mode == "P"
