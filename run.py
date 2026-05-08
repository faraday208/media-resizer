#!/usr/bin/env python3
"""
Media Resizer — CLI

Kullanım örnekleri:
  # Copy mode (orijinal korunur, output_dir'e yazılır)
  python run.py -i ./dataset --max-width 1024 --max-height 1024 -o ./resized

  # In-place (orijinal kaybolur — undo yok)
  python run.py -i ./dataset --mode in-place --max-width 1024

  # Geri al (sadece copy mode için)
  python run.py --undo ./resized/resize_report.json
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from resize_core import (
    DEFAULT_REPORT_NAME,
    resize_dataset,
    undo_from_report,
    write_report,
)


def _print_progress(current: int, total: int, msg: str) -> None:
    if total > 0:
        pct = current * 100 // total
        print(f"\r  {msg} ({pct}%)", end="", flush=True)
    else:
        print(f"\r  {msg}", end="", flush=True)


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Media Resizer — Lanczos batch resize, aspect-preserving",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("-i", "--input", help="Input klasörü")
    p.add_argument("-o", "--output", help="Output klasörü (copy mode için zorunlu)")
    p.add_argument("--mode", choices=["copy", "in-place"], default="copy",
                   help="copy: orijinal korunur (default) | in-place: yer değiştirir")
    p.add_argument("--recursive", action="store_true", default=True,
                   help="Alt klasörleri tara (default)")
    p.add_argument("--no-recursive", action="store_false", dest="recursive")
    p.add_argument("--max-width", type=int, default=1920, help="Max genişlik (default: 1920)")
    p.add_argument("--max-height", type=int, default=1080, help="Max yükseklik (default: 1080)")
    p.add_argument("--quality", type=int, default=95, help="JPEG quality (default: 95)")
    p.add_argument("--limit", type=int, default=0, help="Max dosya")
    p.add_argument("--dry-run", action="store_true",
                   help="(şu an etkisiz — resize her zaman fiziksel)")
    p.add_argument("--yes", action="store_true",
                   help="In-place modda onay sorma")
    p.add_argument("--undo", help="Resize raporundan geri al (sadece copy mode)")
    p.add_argument("--report", help=f"Rapor JSON yolu (default: <output>/{DEFAULT_REPORT_NAME})")
    return p


def _confirm_in_place(*, assume_yes: bool) -> bool:
    if assume_yes:
        return True
    print("\n⚠  In-place mode — orijinal dosyalar üzerine yazılacak. UNDO YOK.")
    answer = input("Devam? [y/N]: ").strip().lower()
    return answer in {"y", "yes", "evet"}


def _run_undo(args: argparse.Namespace) -> int:
    report_path = Path(args.undo)
    if not report_path.exists():
        print(f"Rapor bulunamadı: {report_path}", file=sys.stderr)
        return 1
    print(f"Undo (dry-run={args.dry_run}): {report_path}")
    summary = undo_from_report(report_path, dry_run=args.dry_run)
    print(f"  Removed:                   {summary['removed']}")
    print(f"  Skipped:                   {summary['skipped']}")
    print(f"  Irreversible (in-place):   {summary['irreversible_in_place']}")
    return 0


def _resolve_report_path(args: argparse.Namespace, default_dir: Path) -> Path:
    if args.report:
        return Path(args.report)
    return default_dir / DEFAULT_REPORT_NAME


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    if args.undo:
        if args.input or args.output:
            parser.error("--undo ile -i/-o birlikte kullanılamaz")
        return _run_undo(args)

    if not args.input:
        parser.error("--input gerekli (veya --undo kullan)")

    input_dir = Path(args.input)
    if not input_dir.is_dir():
        print(f"Geçerli dizin değil: {input_dir}", file=sys.stderr)
        return 1

    if args.mode == "copy" and not args.output:
        parser.error("--mode copy için --output gerekli")

    if args.mode == "in-place" and not args.yes:
        if not _confirm_in_place(assume_yes=False):
            print("İptal edildi.")
            return 2

    print(f"\n{'='*70}")
    print(f"Media Resizer")
    print(f"{'='*70}")
    print(f"Input:    {input_dir}")
    print(f"Mode:     {args.mode}")
    if args.mode == "copy":
        print(f"Output:   {args.output}")
    print(f"Max size: {args.max_width}×{args.max_height}")
    print(f"{'='*70}\n")

    sr = resize_dataset(
        input_dir,
        max_size=(args.max_width, args.max_height),
        mode=args.mode,
        output_dir=args.output,
        quality=args.quality,
        recursive=args.recursive,
        progress_cb=_print_progress,
    )
    if args.limit > 0:
        sr.results = sr.results[: args.limit]

    print(f"\n\n{'='*70}\nSONUÇLAR\n{'='*70}")
    print(f"Total scanned: {sr.total_scanned}")
    print(f"Resize edildi: {sr.resized_count}")
    print(f"Atlandı:       {sr.skipped_count} (zaten max_size altında)")
    if sr.error_count:
        print(f"Hata:          {sr.error_count}")

    # Rapor
    default_dir = Path(args.output) if args.output else input_dir
    report_path = _resolve_report_path(args, default_dir)
    write_report(report_path, scan_result=sr, recursive=args.recursive)
    print(f"\nRapor: {report_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
