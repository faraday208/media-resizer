# Resim Boyutlandırıcı

Bu Python programı, resimleri oranını koruyarak yeniden boyutlandırmanızı sağlar.

## Kurulum

1. Gerekli bağımlılıkları yükleyin:
```bash
pip install -r requirements.txt
```

## Kullanım

Programı şu şekilde kullanabilirsiniz:

```bash
python image_resizer.py input.jpg output.jpg --max-width 1920 --max-height 1080
```

### Parametreler

- `input`: Girdi resminin yolu (zorunlu)
- `output`: Çıktı resminin kaydedileceği yol (zorunlu)
- `--max-width`: Maksimum genişlik (varsayılan: 1920)
- `--max-height`: Maksimum yükseklik (varsayılan: 1080)

## Özellikler

- Resim oranını korur
- Yüksek kaliteli yeniden boyutlandırma (Lanczos algoritması)
- Otomatik çıktı dizini oluşturma
- Optimize edilmiş çıktı dosyaları 