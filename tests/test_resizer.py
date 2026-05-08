"""Resize core: collect_images, resize_one, resize_dataset, undo."""
import json
from pathlib import Path

import pytest
from PIL import Image

from resize_core import (
    DEFAULT_IMAGE_EXTS,
    collect_images,
    resize_dataset,
    resize_one,
    undo_from_report,
    write_report,
)


# ---------- collect_images ----------

def test_collect_top_level(mixed_dataset: Path):
    files = collect_images(mixed_dataset, recursive=False)
    names = [p.name for p in files]
    assert "big_a.jpg" in names
    assert "big_c.jpg" not in names


def test_collect_recursive(mixed_dataset: Path):
    files = collect_images(mixed_dataset, recursive=True)
    names = [p.name for p in files]
    assert "big_c.jpg" in names
    assert "tiny.jpg" in names


def test_collect_invalid_dir(tmp_path: Path):
    assert collect_images(tmp_path / "nope") == []


def test_default_image_exts():
    assert ".jpg" in DEFAULT_IMAGE_EXTS
    assert ".png" in DEFAULT_IMAGE_EXTS


# ---------- resize_one ----------

def test_resize_one_downscales_big_image(tmp_path: Path):
    src = tmp_path / "big.jpg"
    Image.new("RGB", (2400, 1600), "red").save(src, "JPEG", quality=85)
    dst = tmp_path / "out.jpg"
    r = resize_one(src, dst, (1024, 1024))
    assert r.valid
    assert not r.skipped
    assert r.new_width == 1024
    assert r.new_height == 682  # aspect-preserving (2400/1600 = 1.5)
    assert dst.exists()
    # Dosyada gerçek boyut
    with Image.open(dst) as im:
        assert im.size == (1024, 682)


def test_resize_one_skips_small_image(tmp_path: Path):
    src = tmp_path / "small.jpg"
    Image.new("RGB", (800, 600), "red").save(src, "JPEG", quality=85)
    dst = tmp_path / "out.jpg"
    r = resize_one(src, dst, (1920, 1080))
    assert r.valid
    assert r.skipped
    # Boyut değişmedi
    assert r.old_width == r.new_width == 800
    # Output yazılmadı (skip)
    assert not dst.exists()


def test_resize_one_handles_corrupted(tmp_path: Path):
    src = tmp_path / "bad.jpg"
    src.write_bytes(b"not a jpg")
    dst = tmp_path / "out.jpg"
    r = resize_one(src, dst, (1024, 1024))
    assert not r.valid
    assert r.error


# ---------- resize_dataset ----------

def test_resize_dataset_copy_mode(mixed_dataset: Path, tmp_path_factory):
    out = tmp_path_factory.mktemp("out")
    sr = resize_dataset(
        mixed_dataset, max_size=(1024, 1024),
        mode="copy", output_dir=out, recursive=True,
    )
    assert sr.total_scanned == 5
    # big_a, big_b, big_c → resized; small, tiny → skipped
    assert sr.resized_count == 3
    assert sr.skipped_count == 2
    # Output mirror tree
    assert (out / "big_a.jpg").exists()
    assert (out / "sub" / "big_c.jpg").exists()
    # small/tiny copy edilmedi (skip)
    assert not (out / "small.jpg").exists()


def test_resize_dataset_in_place_mode(mixed_dataset: Path):
    sr = resize_dataset(
        mixed_dataset, max_size=(1024, 1024),
        mode="in-place", recursive=True,
    )
    assert sr.resized_count == 3
    # big_a artık 1024 max
    with Image.open(mixed_dataset / "big_a.jpg") as im:
        assert max(im.size) <= 1024


def test_resize_dataset_copy_requires_output(mixed_dataset: Path):
    with pytest.raises(ValueError, match="output_dir"):
        resize_dataset(mixed_dataset, mode="copy", output_dir=None)


def test_resize_dataset_invalid_mode(mixed_dataset: Path):
    with pytest.raises(ValueError, match="mode"):
        resize_dataset(mixed_dataset, mode="weird")


def test_resize_dataset_empty_dir(tmp_path: Path):
    sr = resize_dataset(tmp_path, max_size=(1024, 1024),
                        mode="in-place", recursive=True)
    assert sr.total_scanned == 0
    assert sr.results == []


def test_resize_dataset_progress_callback(mixed_dataset: Path):
    calls = []
    def cb(c, t, m): calls.append((c, t, m))
    resize_dataset(mixed_dataset, max_size=(1024, 1024),
                   mode="in-place", progress_cb=cb)
    assert len(calls) >= 1


def test_resize_result_has_absolute_path(mixed_dataset: Path):
    sr = resize_dataset(mixed_dataset, max_size=(1024, 1024),
                        mode="in-place")
    for r in sr.results:
        assert Path(r["path"]).is_absolute()


# ---------- write_report + undo ----------

def test_write_report_includes_actions(mixed_dataset: Path, tmp_path_factory):
    out = tmp_path_factory.mktemp("out")
    sr = resize_dataset(mixed_dataset, max_size=(1024, 1024),
                        mode="copy", output_dir=out, recursive=True)
    report = out / "resize_report.json"
    write_report(report, scan_result=sr, recursive=True)
    data = json.loads(report.read_text())
    assert data["tool"] == "media-resizer"
    assert data["mode"] == "copy"
    assert data["max_size"] == [1024, 1024]
    assert "actions" in data
    assert len(data["actions"]) == 5


def test_undo_removes_copy_outputs(mixed_dataset: Path, tmp_path_factory):
    out = tmp_path_factory.mktemp("out")
    sr = resize_dataset(mixed_dataset, max_size=(1024, 1024),
                        mode="copy", output_dir=out, recursive=True)
    report = out / "resize_report.json"
    write_report(report, scan_result=sr, recursive=True)

    summary = undo_from_report(report)
    assert summary["removed"] == 3  # 3 resize edilmiş, 2 skipped
    # Output dosyaları silindi
    assert not (out / "big_a.jpg").exists()
    # Source yerinde
    assert (mixed_dataset / "big_a.jpg").exists()


def test_undo_in_place_irreversible(mixed_dataset: Path, tmp_path: Path):
    sr = resize_dataset(mixed_dataset, max_size=(1024, 1024),
                        mode="in-place")
    report = tmp_path / "report.json"
    write_report(report, scan_result=sr, recursive=True)

    summary = undo_from_report(report)
    assert summary["removed"] == 0
    assert summary["irreversible_in_place"] == 5  # her dosya


def test_undo_dry_run(mixed_dataset: Path, tmp_path_factory):
    out = tmp_path_factory.mktemp("out")
    sr = resize_dataset(mixed_dataset, max_size=(1024, 1024),
                        mode="copy", output_dir=out, recursive=True)
    report = out / "resize_report.json"
    write_report(report, scan_result=sr, recursive=True)

    summary = undo_from_report(report, dry_run=True)
    assert summary["removed"] == 3
    # Output dosyaları HALA orada
    assert (out / "big_a.jpg").exists()


def test_undo_rejects_wrong_tool(tmp_path: Path):
    report = tmp_path / "fake.json"
    report.write_text(json.dumps({"tool": "other", "results": []}))
    with pytest.raises(ValueError, match="tool mismatch"):
        undo_from_report(report)
