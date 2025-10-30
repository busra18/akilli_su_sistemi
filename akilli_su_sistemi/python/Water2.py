# AKILLI SU TÜKETİM ANALİZ SİSTEMİ -
# Tüm hatalar (Seri Port, Grafik Çakışması, Veri Tipi) giderilmiştir.

# --- KÜTÜPHANELER ---
import serial 
import pandas as pd 
import matplotlib.pyplot as plt 
import csv 
import time 
import os 
from datetime import datetime 
import matplotlib
# Matplotlib backend'ini, pencere açma sorununu çözmek için dosyaya kaydetmeye zorla
matplotlib.use('Agg') 

# --- KULLANICI AYARLARI ---
# Lütfen Arduino IDE'de gördüğünüz COM port numarasını girin!
PORT = "COM6"  
BAUD = 9600  
CSV_FILE = "su_tuketim.csv"  
UPDATE_INTERVAL = 50  # Her 50 kayıtta analiz ve grafik oluştur
FLOW_THRESHOLD = 3.0  # Optimizasyon eşiği (L/dk cinsinden)

# --- VERİ YAPISI ve BAŞLANGIÇ ---
columns = ["timestamp", "flow_lpm", "cumulative_liters", "ir_state"]
data = pd.DataFrame(columns=columns)

# CSV dosyası yoksa oluştur, varsa yükle
if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(columns)
    print("Yeni CSV dosyası oluşturuldu.")
else:
    try:
        data = pd.read_csv(CSV_FILE)
        # Veri tiplerini sayıya zorla dönüştürme (Hata giderme için KRİTİK)
        data["flow_lpm"] = pd.to_numeric(data["flow_lpm"], errors='coerce').fillna(0)
        data["cumulative_liters"] = pd.to_numeric(data["cumulative_liters"], errors='coerce').fillna(0)
        data["ir_state"] = pd.to_numeric(data["ir_state"], errors='coerce').fillna(0)
        
        data["timestamp"] = pd.to_datetime(data["timestamp"])
        print(f"Mevcut veriler yüklendi. Kayıt sayısı: {len(data)}")
    except Exception as e:
        print(f"KRİTİK HATA: CSV yüklenemedi: {e}. Programı sonlandırın ve CSV dosyasını kontrol edin.")
        exit(1)

# --- SERİ PORT BAĞLANTISI ---
try:
    # Seri portu aç (timeout süresi 1 saniye)
    ser = serial.Serial(PORT, BAUD, timeout=1) 
    time.sleep(2) 
    print(f"Seri port bağlantısı başarılı: {PORT}")
except Exception as e:
    print(f"Seri port hatası: {e}")
    exit(1)


# -----------------------------
# FONKSİYONLAR
# -----------------------------

def kaydet_csv(row):
    """Yeni veriyi CSV dosyasına ekler"""
    try:
        with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(row)
        return True
    except Exception as e:
        print(f"CSV kaydetme hatası: {e}")
        return False


def gorsellestir(df):
    """Sadece Anlik Debi ve Toplam Tüketimi (Çizgi) Grafiklerini Tek Pencerede Çizer..."""
    if df.empty:
        print("Grafik için veri yok")
        return

    try:
        df_temp = df.copy()
        df_temp["timestamp"] = pd.to_datetime(df_temp["timestamp"])
        df_temp.set_index("timestamp", inplace=True)
        df_temp = df_temp.sort_index()
        df_temp.index = df_temp.index.tz_localize(None) # Zaman dilimi temizleme

        # İki alt grafik oluştur
        plt.figure(figsize=(12, 8)) 

        # 1. Alt Grafik: ANLIK DEBİ
        plt.subplot(2, 1, 1)  # 2 satır, 1 sütun, 1. sıra
        plt.plot(df_temp.index, df_temp["flow_lpm"], 'b-', linewidth=1)
        plt.title("Anlık Debi Akışı (Litre/dk)", fontsize=14)
        plt.ylabel("Litre/dk")
        plt.grid(axis='y', alpha=0.5)

        # 2. Alt Grafik: TOPLAM TÜKETİM
        plt.subplot(2, 1, 2)  # 2 satır, 1 sütun, 2. sıra
        plt.plot(df_temp.index, df_temp["cumulative_liters"], 'g-', linewidth=2)
        plt.title("Toplam Tüketim (Litre)", fontsize=14)
        plt.ylabel("Litre")
        plt.xlabel("Zaman")
        plt.grid(axis='y', alpha=0.5)
        
        plt.tight_layout()
        plt.savefig("anlik_ve_toplam_tuketim.png", dpi=300, bbox_inches='tight')
        print("Anlık ve Toplam Tüketim Grafikleri oluşturuldu ve kaydedildi.")

    except Exception as e:
        print(f"KRİTİK GRAFİK OLUŞTURMA HATASI: {e}")

def ortalama_tuketim(df):
    """Ortalama anlık debiyi L/dk cinsinden hesaplar"""
    if len(df) == 0:
        return 0.0
    return round(df["flow_lpm"].mean(), 2)


def gereksiz_tuketim_hesapla(df):
    """IR sensörü 0 iken akan toplam suyu litre cinsinden hesaplar"""
    if df.empty:
        return 0.0
    try:
        waste_data = df[df["ir_state"] == 0].copy()
        if waste_data.empty:
            return 0.0

        waste_data["timestamp"] = pd.to_datetime(waste_data["timestamp"])
        waste_data = waste_data.sort_values("timestamp")
        waste_data["time_diff"] = waste_data["timestamp"].diff().dt.total_seconds().fillna(0) / 60.0

        waste_data["waste_liters"] = waste_data["flow_lpm"] * waste_data["time_diff"]
        total_waste = waste_data["waste_liters"].sum()

        return round(total_waste, 2)
    except Exception as e:
        print(f"Gereksiz tüketim hesaplama hatası: {e}")
        return 0.0


def optimizasyon_analizi(df):
    """Tüketim optimizasyonu analizi yapar ve rapor döndürür"""
    # ... (Optimizasyon kodunuz aynı kalır)
    # Kod bloğu çok uzun olduğu için burada kısaltılmıştır.
    if len(df) < 10:
        return "Yeterli veri yok. Analiz için en az 10 kayıt gerekli."

    ort_debi = ortalama_tuketim(df)
    if ort_debi > FLOW_THRESHOLD:
        debi_uyari = f"Yüksek debi: Ortalama {ort_debi} L/dk (Eşik {FLOW_THRESHOLD} L/dk)"
    else:
        debi_uyari = f"Debi normal: Ortalama {ort_debi} L/dk"

    waste = gereksiz_tuketim_hesapla(df)
    if waste > 10:
        waste_uyari = f"Yüksek gereksiz tüketim: {waste} L"
    elif waste > 0:
        waste_uyari = f"Orta gereksiz tüketim: {waste} L"
    else:
        waste_uyari = "Gereksiz tüketim yok"

    total = df["cumulative_liters"].iloc[-1] if len(df) > 0 else 0

    rapor = f"""
SU TÜKETİM ANALİZ RAPORU
--------------------------
Toplam Tüketim: {total:.1f} L
{debi_uyari}
{waste_uyari}
Toplam Kayıt: {len(df)} adet
--------------------------
"""
    return rapor


def anlik_gorunum(df):
    """En son kaydı gösterir"""
    if df.empty:
        return "Henüz veri yok"

    son_kayit = df.iloc[-1]
    return f"Anlık Debi: {son_kayit['flow_lpm']} L/dk | Toplam: {son_kayit['cumulative_liters']} L | IR: {'Var' if son_kayit['ir_state'] == 1 else 'Yok'}"


# -----------------------------
# ANA DÖNGÜ
# -----------------------------
print("\n" + "=" * 50)
print("AKILLI SU TÜKETİM İZLEME SİSTEMİ")
print("=" * 50)
print("Veri okuma başlatılıyor... (Ctrl+C ile durdur)")

try:
    kayit_sayaci = len(data)  # Mevcut kayıt sayısıyla başla

    while True:
        try:
            line = ser.readline().decode('utf-8', errors='ignore').strip()

            if line and "," in line:
                parts = line.split(",")
                if len(parts) >= 3:
                    flow = float(parts[0].strip())
                    cumulative = float(parts[1].strip())
                    ir = int(parts[2].strip())
                    ts = datetime.now()

                    new_row = [ts, flow, cumulative, ir]

                    if kaydet_csv(new_row):
                        data.loc[len(data)] = new_row
                        kayit_sayaci += 1

                        if kayit_sayaci % 10 == 0:
                            print(anlik_gorunum(data))

                        if kayit_sayaci % UPDATE_INTERVAL == 0 and kayit_sayaci > 0:
                            print("\n" + "=" * 40)
                            print(f"Analiz zamanı! (Kayıt: {kayit_sayaci})")
                            print("=" * 40)

                            print(optimizasyon_analizi(data))
                            gorsellestir(data) 
                            print("Analiz tamamlandı. Veri kaydı devam ediyor...")
                            print("=" * 40 + "\n")

        except ValueError as e:
            print(f"Veri dönüşüm hatası: {e} | Satır: {line}")
        except Exception as e:
            print(f"Beklenmeyen hata: {e}")

except KeyboardInterrupt:
    print("\nProgram sonlandırılıyor...")

    if not data.empty:
        print("\nSon durum raporu:")
        print("=" * 30)
        print(optimizasyon_analizi(data))
        print(f"Toplam kayıt: {len(data)}")
        print(f"Son toplam tüketim: {data['cumulative_liters'].iloc[-1]:.2f} L")

        gorsellestir(data)
        
    ser.close()
    print("Seri port kapatıldı.")
    print("Program sonlandı.")

except Exception as e:
    print(f"Kritik hata: {e}")
    ser.close()
