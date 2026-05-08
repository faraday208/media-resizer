"""Test fixture'ları — media-resizer."""
import sys
from pathlib import Path

import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _save_jpg(p: Path, size=(1024, 768), color="red") -> None:
    Image.new("RGB", size, color).save(p, "JPEG", quality=85)


@pytest.fixture
def mixed_dataset(tmp_path: Path) -> Path:
    """Karışık boyutlu görseller — bazıları max_size üstü, bazıları altı."""
    _save_jpg(tmp_path / "big_a.jpg", size=(2400, 1600), color="red")
    _save_jpg(tmp_path / "big_b.jpg", size=(1920, 1080), color="green")
    _save_jpg(tmp_path / "small.jpg", size=(800, 600), color="blue")
    sub = tmp_path / "sub"
    sub.mkdir()
    _save_jpg(sub / "big_c.jpg", size=(3000, 2000), color="yellow")
    _save_jpg(sub / "tiny.jpg", size=(400, 300), color="magenta")
    return tmp_path
