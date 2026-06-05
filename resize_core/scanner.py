"""
Resize Scanner — collect_images + Lanczos resize.

Public API:
- collect_images(directory, recursive, allowed_exts) → list[Path]
- resize_dataset(directory, *, max_size, mode, output_dir, ...) → ScanResult
"""
from __future__ import annotations

import os
import shutil
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable, Iterable

from PIL import Image

DEFAULT_IMAGE_EXTS: frozenset[str] = frozenset({
    ".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".tif"
})

ProgressCallback = Callable[[int, int, str], None]


@dataclass
class ResizeResult:
    """Tek dosyanın resize sonucu."""
    valid: bool                       # işlem başarılı mı
    reason: str | None
    filename: str
    path: str                         # absolute orijinal path
    output_path: str = ""
    old_width: int = 0
    old_height: int = 0
    new_width: int = 0
    new_height: int = 0
    skipped: bool = False             # zaten max_size altında, dokunulmadı
    error: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ScanResult:
    source_root: str
    mode: str                         # "copy" | "in-place"
    output_dir: str | None
    max_size: tuple[int, int]
    total_scanned: int
    resized_count: int
    skipped_count: int                # zaten küçük
    error_count: int = 0
    results: list[dict] = field(default_factory=list)

    @property
    def has_resized(self) -> bool:
        return self.resized_count > 0


# Recursive scan'in atlayacağı pipeline klasörleri — reject hedefi ve rapor
# dizini. Reject dir dataset içine düşse bile (relative invalid_dir) bu dosyalar
# tekrar taranıp yeniden işlenmez.
_EXCLUDED_SCAN_DIRS = {"_rejected", "report"}


def collect_images(
    directory: Path | str,
    *,
    recursive: bool = True,
    allowed_exts: Iterable[str] = DEFAULT_IMAGE_EXTS,
) -> list[Path]:
    """Görsel dosyaları topla."""
    root = Path(directory)
    if not root.is_dir():
        return []
    exts = {e.lower() for e in allowed_exts}
    out: list[Path] = []
    if recursive:
        for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
            # Pipeline klasörlerini atla — recursive scan elenen (_rejected) veya
            # raporlanan (report) dosyaları geri yutmasın.
            dirnames[:] = [d for d in dirnames if d not in _EXCLUDED_SCAN_DIRS]
            for fn in filenames:
                p = Path(dirpath) / fn
                if p.suffix.lower() in exts:
                    out.append(p)
    else:
        for entry in root.iterdir():
            if entry.is_file() and entry.suffix.lower() in exts:
                out.append(entry)
    out.sort()
    return out


def resize_one(
    src: Path,
    dst: Path,
    max_size: tuple[int, int],
    *,
    quality: int = 95,
    dry_run: bool = False,
) -> ResizeResult:
    """Tek dosyayı Lanczos ile aspect-preserving resize.
    Eğer dosya zaten max_size altında ise skip (kopyala/dokunma).
    dry_run=True: planı ResizeResult olarak döndür, dosya yazma."""
    try:
        with Image.open(src) as img:
            w, h = img.size
            ratio = min(max_size[0] / w, max_size[1] / h)
            if ratio >= 1.0:
                # Zaten yeterince küçük — skip
                return ResizeResult(
                    valid=True, reason=None,
                    filename=src.name, path=str(src.resolve()),
                    output_path=str(dst.resolve()) if dst != src else "",
                    old_width=w, old_height=h,
                    new_width=w, new_height=h,
                    skipped=True,
                )
            new_w, new_h = int(w * ratio), int(h * ratio)
            if not dry_run:
                resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                dst.parent.mkdir(parents=True, exist_ok=True)
                # JPEG için quality, PNG için optimize
                save_kwargs: dict = {"optimize": True}
                if dst.suffix.lower() in {".jpg", ".jpeg"}:
                    save_kwargs["quality"] = quality
                resized.save(dst, **save_kwargs)
            return ResizeResult(
                valid=True, reason=None,
                filename=src.name, path=str(src.resolve()),
                output_path=str(dst.resolve()),
                old_width=w, old_height=h,
                new_width=new_w, new_height=new_h,
            )
    except Exception as e:
        return ResizeResult(
            valid=False, reason=f"error: {e}",
            filename=src.name, path=str(src.resolve()),
            error=str(e),
        )


def resize_dataset(
    directory: Path | str,
    *,
    max_size: tuple[int, int] = (1920, 1080),
    mode: str = "copy",                  # "copy" | "in-place"
    output_dir: Path | str | None = None,
    quality: int = 95,
    recursive: bool = True,
    allowed_exts: Iterable[str] = DEFAULT_IMAGE_EXTS,
    dry_run: bool = False,
    progress_cb: ProgressCallback | None = None,
) -> ScanResult:
    """Bir dizini Lanczos ile aspect-preserving resize et.

    Mode:
      copy: orijinal kaynakta korunur, output_dir'e yazılır (zorunlu)
      in-place: dosya yerinde değişir (orijinal kaybolur)
    """
    if mode not in ("copy", "in-place"):
        raise ValueError(f"mode must be 'copy' or 'in-place', got {mode!r}")
    if mode == "copy" and output_dir is None:
        raise ValueError("mode='copy' requires output_dir")

    root = Path(directory).resolve()
    out_root = Path(output_dir).resolve() if output_dir else None
    images = collect_images(root, recursive=recursive, allowed_exts=allowed_exts)
    total = len(images)

    if total == 0:
        return ScanResult(
            source_root=str(root), mode=mode,
            output_dir=str(out_root) if out_root else None,
            max_size=max_size,
            total_scanned=0, resized_count=0, skipped_count=0,
        )

    results: list[dict] = []
    resized = skipped = errors = 0

    for idx, src in enumerate(images, 1):
        if mode == "in-place":
            dst = src
        else:
            # Mirror tree under output_dir
            rel = src.relative_to(root)
            dst = out_root / rel if out_root else src

        r = resize_one(src, dst, max_size, quality=quality, dry_run=dry_run)
        results.append(r.to_dict())
        if not r.valid:
            errors += 1
        elif r.skipped:
            skipped += 1
        else:
            resized += 1

        if progress_cb and (idx % 25 == 0 or idx == total):
            progress_cb(idx, total, f"Resize: {idx}/{total}")

    return ScanResult(
        source_root=str(root), mode=mode,
        output_dir=str(out_root) if out_root else None,
        max_size=max_size,
        total_scanned=total,
        resized_count=resized,
        skipped_count=skipped,
        error_count=errors,
        results=results,
    )


def undo_from_report(
    report_path: Path | str,
    *,
    dry_run: bool = False,
) -> dict:
    """Resize undo — sadece 'copy' mode için (output dosyaları siler).
    'in-place' mode için undo yok (orijinal kayıp).
    """
    import json
    with open(report_path, encoding="utf-8") as f:
        report = json.load(f)
    if report.get("tool") != "media-resizer":
        raise ValueError(
            f"Report tool mismatch: expected 'media-resizer', got {report.get('tool')!r}"
        )

    mode = report.get("mode")
    if mode == "in-place":
        return {"removed": 0, "skipped": 0,
                "irreversible_in_place": len(report.get("results", []))}

    removed = skipped = 0
    for r in report.get("results", []):
        out = r.get("output_path") or ""
        if not out or r.get("skipped"):
            skipped += 1
            continue
        out_p = Path(out)
        if not out_p.exists():
            skipped += 1
            continue
        if not dry_run:
            try:
                out_p.unlink()
            except OSError:
                skipped += 1
                continue
        removed += 1

    return {"removed": removed, "skipped": skipped, "irreversible_in_place": 0}
