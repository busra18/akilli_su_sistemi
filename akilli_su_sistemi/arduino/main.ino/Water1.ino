# Gerekli kütüphaneleri yüklüyoruz
import serial  # Arduino'dan seri port verisi almak için
import pandas as pd  # Verileri tablo (DataFrame) halinde tutmak için
import matplotlib.pyplot as plt  # Grafik çizmek için
from datetime import datetime  # Zaman damgası eklemek için
import csv  # CSV dosyası kaydı için
import time  # Bekleme işlemleri için

# --- KULLANICI AYARLARI ---
PORT = "COM6"  # Arduino'nun bağlı olduğu port (Windows: COM3, Linux: /dev/ttyUSB0)
BAUD = 9600  # Arduino ile aynı baud rate kullanılmalı
CSV_FILE = "su_tuketim.csv"  # Verilerin kaydedileceği dosya adı

# --- VERİ YAPISI ---
columns = ["timestamp", "flow_lpm", "cumulative_liters", "ir_state"]  # CSV ve DataFrame sütunları
data = pd.DataFrame(columns=columns)  # Boş DataFrame oluştur
new_rows = []  # Döngüde gelen verileri geçici tutmak için liste

# --- CSV BAŞLIK YAZ ---
# Program başlarken CSV dosyası oluşturulur ve sütun isimleri yazılır
with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(columns)

# --- SERİ PORT BAĞLANTI ---
try:
    ser = serial.Serial(PORT, BAUD, timeout=1)  # Seri portu aç
    time.sleep(2)  # Arduino açıldıktan sonra hazır olması için bekle
    print(f"Bağlantı başarılı: {PORT}")
except Exception as e:
    print(f"Seri port hatası: {e}")  # Hata varsa ekrana yazdır
    raise SystemExit(1)  # Programı güvenli şekilde kapat


# --- CSV'YE SATIR KAYDETME ---
def kaydet_csv(row):
    """Yeni satırı CSV dosyasına ekler."""
    try:
        with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(row)
    except Exception as e:
        print(f"CSV yazma hatası: {e}")


# --- GÖRSELLEŞTİRME ---
def gorsellestir(df, save_prefix="su_tuketim_grafik"):
    """Grafikleri oluşturur ve PNG dosyası olarak kaydeder."""
    if df.empty:  # Eğer veri yoksa grafik çizilmez
        print("Grafik için veri yok")
        return

    try:
        # DataFrame kopyalanır ve zaman bilgisi hazırlanır
        dfc = df.copy()
        dfc["timestamp"] = pd.to_datetime(dfc["timestamp"])
        dfc = dfc.sort_values("timestamp")
        dfc.set_index("timestamp", inplace=True)

        # Grafik alanı
        plt.figure(figsize=(12, 8))

        # 1. Grafik: Anlık Debi
        plt.subplot(3, 1, 1)
        plt.plot(dfc.index, dfc["flow_lpm"], 'b-', linewidth=1)
        plt.title("Anlık Debi (L/dk)")
        plt.grid(True)

        # 2. Grafik: Toplam Tüketim
        plt.subplot(3, 1, 2)
        plt.plot(dfc.index, dfc["cumulative_liters"], 'g-', linewidth=2)
        plt.title("Toplam Tüketim (L)")
        plt.grid(True)

        # 3. Grafik: IR Sensör Durumu
        plt.subplot(3, 1, 3)
        plt.step(dfc.index, dfc["ir_state"], 'r-', where='post')
        plt.title("IR Sensör Durumu (0 = Yok, 1 = Var)")
        plt.ylim(-0.5, 1.5)
        plt.grid(True)

        # Grafikleri kaydet
        plt.tight_layout()
        filename = f"{save_prefix}{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
        plt.savefig(filename, dpi=150)  # PNG olarak kaydet
        plt.close()  # Belleği boşalt
        print(f"Grafik kaydedildi: {filename}")

    except Exception as e:
        print(f"Grafik hatası: {e}")


# --- ANA DÖNGÜ ---
print("Veri okuma başlatıldı... (Ctrl+C ile durdur)")

try:
    while True:
        try:
            raw = ser.readline()  # Seri porttan bir satır oku
            if not raw:
                continue  # Veri gelmediyse döngüye devam et

            line = raw.decode('utf-8', errors='ignore').strip()  # Byte → string

            if line:  # Satır boş değilse
                parts = line.split(',')  # Virgülle ayır
                if len(parts) >= 3:  # Beklenen format: flow,cumulative,ir
                    # Verileri sayıya dönüştür
                    flow = float(parts[0])
                    cumulative = float(parts[1])
                    ir_state = int(parts[2])
                    timestamp = datetime.now()

                    new_row = [timestamp, flow, cumulative, ir_state]

                    # CSV'ye yaz
                    kaydet_csv(new_row)

                    # Geçici listeye ekle
                    new_rows.append(new_row)

                    # Her 20 satırda bir DataFrame'e aktar
                    if len(new_rows) >= 20:
                        temp_df = pd.DataFrame(new_rows, columns=columns)
                        data = pd.concat([data, temp_df], ignore_index=True)
                        new_rows = []  # Listeyi temizle

                        # Konsola özet bilgi yazdır
                        print(f"Kayıt sayısı: {len(data)}")
                        print(f"Son debi: {flow} L/dk")
                        print(f"Toplam tüketim: {cumulative} L")
                        print(f"IR durumu: {'Var' if ir_state else 'Yok'}")
                        print("-" * 30)

                        # Her 100 kayıtta grafik çiz
                        if len(data) % 100 == 0:
                            gorsellestir(data)

        except ValueError as e:  # Dönüşüm hatası olursa
            print(f"Veri dönüşüm hatası: {e} | Satır: {line}")
        except Exception as e:  # Diğer beklenmeyen hatalar
            print(f"Beklenmeyen hata: {e} | Satır: {line}")

except KeyboardInterrupt:  # Kullanıcı Ctrl+C yaparsa
    print("\nProgram sonlandırılıyor...")

    # Kalan satırları DataFrame'e ekle
    if new_rows:
        temp_df = pd.DataFrame(new_rows, columns=columns)
        data = pd.concat([data, temp_df], ignore_index=True)

    # Son grafik kaydet
    if not data.empty:
        gorsellestir(data, "son_durum")
        print(f"Toplam kayıt: {len(data)}")
        print(f"Son toplam tüketim: {data['cumulative_liters'].iloc[-1]:.2f} L")

    ser.close()  # Seri portu kapat
    print("Seri port kapatıldı.")
