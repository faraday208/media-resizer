"""Reporter — sidecar JSON (tool-conventions §4 uyumlu)."""
from __future__ import annotations

import json
from pathlib import Path

from .scanner import ScanResult

REPORT_VERSION = "1"
REPORT_TOOL = "media-resizer"
DEFAULT_REPORT_NAME = "resize_report.json"


def write_report(
    report_path: Path | str,
    *,
    scan_result: ScanResult,
    recursive: bool,
    dry_run: bool = False,
) -> Path:
    summary = {
        "total_scanned": scan_result.total_scanned,
        "resized": scan_result.resized_count,
        "skipped": scan_result.skipped_count,        # zaten küçük
        "errors": scan_result.error_count,
    }
    payload = {
        "version": REPORT_VERSION,
        "tool": REPORT_TOOL,
        "source_root": scan_result.source_root,
        "recursive": recursive,
        "mode": scan_result.mode,                    # "copy" | "in-place"
        "output_dir": scan_result.output_dir,
        "max_size": list(scan_result.max_size),
        "dry_run": dry_run,
        "summary": summary,
        # actions[]: convention §4 — her resize bir action
        "actions": [
            {
                "original": r["path"],
                "output_path": r.get("output_path") or "",
                "old_size": [r.get("old_width", 0), r.get("old_height", 0)],
                "new_size": [r.get("new_width", 0), r.get("new_height", 0)],
                "skipped": r.get("skipped", False),
                "reason": r.get("reason") or ("skipped: zaten max_size altında"
                                              if r.get("skipped") else "resized"),
            }
            for r in scan_result.results
        ],
        "results": scan_result.results,
    }
    out = Path(report_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    return out
