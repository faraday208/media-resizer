# media-resizer

> Medya dosyalarını Lanczos algoritmasıyla aspect-preserving toplu resize.
> Copy (orijinal korunur) veya in-place mode. Copy için undo destekli.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![uv](https://img.shields.io/badge/built%20with-uv-261230)](https://github.com/astral-sh/uv)

`media-dataset-prep` pipeline'ının **05. adımı**. Standalone kullanılabilir.

---

## 🎯 Ne yapıyor?

Bir klasördeki tüm görselleri **Lanczos** ile aspect-ratio koruyarak yeniden boyutlandırır:

| Özellik | Açıklama |
|---|---|
| **Aspect-preserving** | Width/height oranı korunur (`min(max_w/w, max_h/h)`) |
| **Skip-if-smaller** | Zaten max_size altında olan dosyalar dokunulmaz |
| **Copy mode** | Orijinal kaynakta kalır, output'a yazılır (mirror tree) |
| **In-place mode** | Orijinal üzerine yazılır (UNDO YOK — onay sorar) |
| **JPEG quality** | `--quality` (default 95) |
| **PNG optimize** | `optimize=True` ile sıkıştırma |

---

## 🚀 Kurulum

```bash
git clone https://github.com/faraday208/media-resizer
cd media-resizer
uv sync
```

`media-dataset-prep` workspace altında: `make install`

---

## 🛠️ Kullanım — CLI

### Copy mode (önerilen — orijinal korunur)

```bash
uv run python run.py -i ./dataset \
    --max-width 1024 --max-height 1024 \
    -o ./resized
```

### In-place (orijinal üzerine yaz, undo yok)

```bash
uv run python run.py -i ./dataset \
    --mode in-place \
    --max-width 1024 --max-height 1024 \
    --yes
```

### JPEG quality + recursive

```bash
uv run python run.py -i ./dataset \
    --max-width 2048 --max-height 2048 \
    --quality 90 \
    -o ./resized
```

### Geri al (sadece copy mode)

```bash
uv run python run.py --undo ./resized/resize_report.json
```

---

## 📋 Operation modes — özet

| Mod | Komut | Etki | Undo |
|---|---|---|---|
| **Copy** (default) | `--mode copy --output D` | Orijinal yerinde, D'ye resize'lı | ✓ (output sil) |
| **In-place** | `--mode in-place` | Üzerine yazılır | ✗ irreversible |
| **Undo** (copy) | `--undo REPORT` | Output dosyaları silinir | – |

---

## 🚩 Tüm CLI flag'leri

| Flag | Tip | Default | Açıklama |
|---|---|---|---|
| `-i, --input` | str | – | Input klasörü (zorunlu, `--undo` hariç) |
| `-o, --output` | str | – | Output klasörü (copy mode için zorunlu) |
| `--mode` | `copy\|in-place` | `copy` | İşlem modu |
| `--recursive` / `--no-recursive` | flag | True | Alt klasör tarama |
| `--max-width` | int | 1920 | Max genişlik |
| `--max-height` | int | 1080 | Max yükseklik |
| `--quality` | int | 95 | JPEG quality (1-100) |
| `--limit N` | int | 0 | Max dosya |
| `--yes` | flag | False | In-place'de onay sorma |
| `--undo` | str | – | Resize raporundan geri al |
| `--report` | str | `<output>/resize_report.json` | Rapor JSON yolu |

---

## ⚙️ Config

Tool config dosyası kullanmıyor; tüm parametreler CLI flag'leri.

---

## 🔌 In-process (library) kullanım

```python
from resize_core import resize_dataset, undo_from_report, write_report

sr = resize_dataset(
    "./dataset",
    max_size=(1024, 1024),
    mode="copy",
    output_dir="./resized",
    quality=95,
    recursive=True,
)
print(f"{sr.resized_count} resize edildi, {sr.skipped_count} atlandı")

write_report("./resized/resize_report.json", scan_result=sr, recursive=True)
# undo_from_report("./resized/resize_report.json")
```

---

## 📄 Rapor formatı

```jsonc
{
  "version": "1",
  "tool": "media-resizer",
  "source_root": "/abs/path",
  "recursive": true,
  "mode": "copy",
  "output_dir": "/abs/.../resized",
  "max_size": [1024, 1024],
  "summary": {"total_scanned": 100, "resized": 75, "skipped": 24, "errors": 1},
  "actions": [
    {"original": "/abs/.../big.jpg",
     "output_path": "/abs/.../resized/big.jpg",
     "old_size": [2400, 1600], "new_size": [1024, 682],
     "skipped": false, "reason": "resized"}
  ],
  "results": [...]
}
```

---

## 🧪 Test

```bash
uv sync --group dev
uv run pytest
```

19 test: collect_images + resize_one + resize_dataset + undo + write_report.

---

## ⚠️ Limitations

- **In-place mode irreversible** — `--undo` sadece copy mode için
- **Skip-if-smaller** sabit kural — upscale yapmaz
- Tek thread (Pillow CPU-bound)
- HEIC/HEIF için `pillow-heif` ekstra

---

## 🏷️ Sürüm

**v1.0.0** — clean release. `image-resizer` → `media-resizer`. Tek-dosya 51 satırlık script (tek görsel) → `resize_core/` paketi (toplu + recursive). argparse + standart flag'ler, sidecar JSON §4, undo, 19 test.

---

## 📜 Lisans

[MIT](LICENSE)
