# WATER3.PY - ANLIK DEBİ GRAFİĞİ HATA AYIKLAMA SÜRÜMÜ
# Sadece anlık debi (flow_lpm) grafiği çizilir.

# --- KÜTÜPHANELER ---
import serial 
import pandas as pd 
import matplotlib.pyplot as plt 
import csv 
import time 
from datetime import datetime
import matplotlib
import os

# Matplotlib backend'ini dosyaya kaydetmeye zorla
matplotlib.use('Agg') 

# --- KULLANICI AYARLARI ---
PORT = "COM6"  # Arduino portunuz
BAUD = 9600  
CSV_FILE = "su_tuketim.csv"  
UPDATE_INTERVAL = 50 
FLOW_THRESHOLD = 3.0 

# --- VERİ YAPISI ve BAŞLANGIÇ ---
columns = ["timestamp", "flow_lpm", "cumulative_liters", "ir_state"]
data = pd.DataFrame(columns=columns)

# CSV dosyası yükleme (Water2.py ile aynı)
if not os.path.exists(CSV_FILE):
    # (CSV Oluşturma kodları...)
    with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(columns)
    print("Yeni CSV dosyası oluşturuldu.")
else:
    try:
        data = pd.read_csv(CSV_FILE)
        # Veri tipini sayıya zorla dönüştürme (KRİTİK)
        data["flow_lpm"] = pd.to_numeric(data["flow_lpm"], errors='coerce').fillna(0)
        data["cumulative_liters"] = pd.to_numeric(data["cumulative_liters"], errors='coerce').fillna(0)
        data["ir_state"] = pd.to_numeric(data["ir_state"], errors='coerce').fillna(0)
        
        data["timestamp"] = pd.to_datetime(data["timestamp"])
        print(f"Mevcut veriler yüklendi. Kayıt sayısı: {len(data)}")
    except Exception as e:
        print(f"KRİTİK HATA: CSV yüklenemedi: {e}")
        exit(1)

# --- SERİ PORT BAĞLANTISI (Aynı kalır) ---
try:
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
    """Yeni veriyi CSV dosyasına ekler (Water2.py ile aynı)"""
    try:
        with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(row)
        return True
    except Exception as e:
        print(f"CSV kaydetme hatası: {e}")
        return False


def gorsellestir_anlik(df):
    """SADECE ANLIK DEBİ GRAFİĞİNİ ÇİZER"""
    if df.empty:
        print("Grafik için veri yok")
        return

    try:
        df_temp = df.copy()
        df_temp["timestamp"] = pd.to_datetime(df_temp["timestamp"])
        df_temp.set_index("timestamp", inplace=True)
        
        # Grafik alanı oluştur (Sadece tek bir grafik)
        plt.figure(figsize=(12, 6)) 

        # Anlık Debi Çizgi Grafiği
        plt.plot(df_temp.index, df_temp["flow_lpm"], 'b-', linewidth=1)
        
        plt.title("ANLIK DEBİ AKIŞI (Litre/dk) - Tüm Kayıtlar", fontsize=16, fontweight='bold')
        plt.xlabel("Zaman")
        plt.ylabel("Litre/dk")
        plt.grid(axis='both', alpha=0.5)

        plt.tight_layout()
        plt.savefig("anlik_debi_kontrol.png", dpi=300, bbox_inches='tight')
        print("SADECE ANLIK DEBİ Grafiği oluşturuldu ve anlik_debi_kontrol.png dosyasına kaydedildi.")

    except Exception as e:
        print(f"KRİTİK ANLIK GRAFİK HATASI: {e}")

# -----------------------------
# ANA DÖNGÜ
# -----------------------------
# ... (Sadece anlık grafiği çağıracak şekilde basitleştirildi)

print("\n" + "=" * 50)
print("ANLIK DEBİ KONTROL SİSTEMİ BAŞLATILDI")
print("=" * 50)

try:
    kayit_sayaci = len(data)

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

                    # Her 50 kayıtta anlık grafiği çizmeye zorla
                    if kayit_sayaci % 50 == 0:
                        print(f"\n--- ANLIK GRAFİK ÇİZİMİ BAŞLATILIYOR (Kayıt: {kayit_sayaci}) ---")
                        gorsellestir_anlik(data)
                        print("--- GRAFİK OLUŞTURMA TAMAMLANDI ---\n")

        except Exception as e:
            # Sadece kritik hataları yakalar
            pass 

except KeyboardInterrupt:
    print("\nProgram sonlandırılıyor...")
    if not data.empty:
        gorsellestir_anlik(data) # Son bir kez çiz
        
    ser.close() 
    print("Seri port kapatıldı.")

except Exception as e:
    print(f"Kritik hata: {e}")
    ser.close()
