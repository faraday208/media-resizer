from PIL import Image
import os
import argparse

def resize_image(input_path, output_path, max_size):
    """
    Resmi oranını koruyarak yeniden boyutlandırır.
    
    Args:
        input_path (str): Girdi resminin yolu
        output_path (str): Çıktı resminin kaydedileceği yol
        max_size (tuple): Maksimum genişlik ve yükseklik (width, height)
    """
    try:
        # Resmi aç
        with Image.open(input_path) as img:
            # Orijinal boyutları al
            width, height = img.size
            
            # Yeni boyutları hesapla
            ratio = min(max_size[0]/width, max_size[1]/height)
            new_size = (int(width * ratio), int(height * ratio))
            
            # Resmi yeniden boyutlandır
            resized_img = img.resize(new_size, Image.Resampling.LANCZOS)
            
            # Çıktı dizinini oluştur (eğer yoksa)
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Resmi kaydet
            resized_img.save(output_path, quality=95, optimize=True)
            
            print(f"Resim başarıyla boyutlandırıldı: {output_path}")
            print(f"Orijinal boyut: {width}x{height}")
            print(f"Yeni boyut: {new_size[0]}x{new_size[1]}")
            
    except Exception as e:
        print(f"Hata oluştu: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description='Resimleri oranını koruyarak yeniden boyutlandırır.')
    parser.add_argument('input', help='Girdi resminin yolu')
    parser.add_argument('output', help='Çıktı resminin kaydedileceği yol')
    parser.add_argument('--max-width', type=int, default=1920, help='Maksimum genişlik (varsayılan: 1920)')
    parser.add_argument('--max-height', type=int, default=1080, help='Maksimum yükseklik (varsayılan: 1080)')
    
    args = parser.parse_args()
    
    resize_image(args.input, args.output, (args.max_width, args.max_height))

if __name__ == "__main__":
    main() 