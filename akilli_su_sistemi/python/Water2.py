import serial  # Arduino ile seri haberleşme yapmak için
import pandas as pd  # Veri çerçevesi ve veri analizi için
import matplotlib.pyplot as plt  # Grafik çizmek için
from datetime import datetime  # Zaman damgası oluşturmak için
import csv  # CSV dosyalarına yazmak için
import time  # Gecikme ve zaman kontrolü için
import os  # Dosya varlığını kontrol etmek için

# -----------------------------
# AYARLAR
# -----------------------------
PORT = "COM3"  # Arduino portu (Linux: /dev/ttyUSB0 olabilir)
BAUD = 9600  # Arduino ile haberleşme hızı (baud rate)
CSV_FILE = "su_tuketim.csv"  # Veri kayıt dosyasının adı
UPDATE_INTERVAL = 50  # Her 50 kayıtta analiz ve grafik oluştur
FLOW_THRESHOLD = 3.0  # Optimizasyon eşiği (L/dk cinsinden)

# -----------------------------
# VERİ ÇERÇEVESİ ve BAŞLANGIÇ
# -----------------------------
columns = ["timestamp", "flow_lpm", "cumulative_liters", "ir_state"]  # DataFrame sütun adları
data = pd.DataFrame(columns=columns)  # Boş DataFrame oluştur

# CSV dosyası yoksa oluştur, varsa yükle
if not os.path.exists(CSV_FILE):
    # Dosya yoksa oluştur ve başlık satırını yaz
    with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)  # CSV yazıcı oluştur
        writer.writerow(columns)  # Sütun başlıklarını yaz
    print("Yeni CSV dosyası oluşturuldu.")
else:
    # Dosya varsa yükle
    try:
        data = pd.read_csv(CSV_FILE)  # CSV dosyasını oku
        data["timestamp"] = pd.to_datetime(data["timestamp"])  # timestamp sütununu datetime yap
        print(f"Mevcut veriler yüklendi. Kayıt sayısı: {len(data)}")
    except Exception as e:
        print(f"CSV yüklenemedi: {e}")  # Hata mesajı yaz

# -----------------------------
# SERİ PORT BAĞLANTISI
# -----------------------------
try:
    ser = serial.Serial(PORT, BAUD, timeout=1)  # Seri portu aç ve 1 saniye timeout ayarla
    time.sleep(2)  # Arduino'nun başlatması için 2 saniye bekle
    print(f"Seri port bağlantısı başarılı: {PORT}")
except Exception as e:
    print(f"Seri port hatası: {e}")  # Bağlantı hatası mesajı
    exit(1)  # Hata varsa programı durdur


# -----------------------------
# FONKSİYONLAR
# -----------------------------

def kaydet_csv(row):
    """Yeni veriyi CSV dosyasına ekler"""
    try:
        with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:  # CSV dosyasını ekleme modunda aç
            writer = csv.writer(f)  # CSV yazıcı oluştur
            writer.writerow(row)  # Yeni satırı yaz
        return True
    except Exception as e:
        print(f"CSV kaydetme hatası: {e}")  # Hata varsa mesaj yaz
        return False


def gorsellestir(df):
    """Günlük, haftalık ve aylık grafikler oluşturur ve kaydeder"""
    if df.empty:
        print("Grafik için veri yok")  # Veri yoksa mesaj yaz
        return

    try:
        df_temp = df.copy()  # Orijinal DataFrame'i kopyala
        df_temp["timestamp"] = pd.to_datetime(df_temp["timestamp"])  # timestamp'i datetime yap
        df_temp.set_index("timestamp", inplace=True)  # timestamp'i index yap
        df_temp = df_temp.sort_index()  # Zaman sırasına göre sırala

        # Grafik alanı oluştur
        plt.figure(figsize=(15, 10))

        # 1. Günlük tüketim
        plt.subplot(3, 1, 1)  # Üç alt grafikten birinci
        gunluk = df_temp["cumulative_liters"].resample("D").max().diff().fillna(0)  # Günlük tüketim hesapla
        if not gunluk.empty:
            gunluk.plot(kind="bar", color='skyblue', edgecolor='black')  # Çubuk grafik çiz
            plt.title("Günlük Su Tüketimi", fontsize=14, fontweight='bold')
            plt.ylabel("Litre")
            plt.xticks(rotation=45)  # X ekseni etiketlerini döndür
            plt.grid(axis='y', alpha=0.3)  # Y eksenine grid ekle

        # 2. Haftalık tüketim
        plt.subplot(3, 1, 2)  # Üç alt grafikten ikinci
        haftalik = df_temp["cumulative_liters"].resample("W").max().diff().fillna(0)  # Haftalık tüketim
        if not haftalik.empty:
            haftalik.plot(kind="bar", color='lightgreen', edgecolor='black')
            plt.title("Haftalık Su Tüketimi", fontsize=14, fontweight='bold')
            plt.ylabel("Litre")
            plt.xticks(rotation=45)
            plt.grid(axis='y', alpha=0.3)

        # 3. Aylık tüketim
        plt.subplot(3, 1, 3)  # Üç alt grafikten üçüncü
        aylik = df_temp["cumulative_liters"].resample("M").max().diff().fillna(0)  # Aylık tüketim
        if not aylik.empty:
            aylik.plot(kind="bar", color='lightcoral', edgecolor='black')
            plt.title("Aylık Su Tüketimi", fontsize=14, fontweight='bold')
            plt.ylabel("Litre")
            plt.xticks(rotation=45)
            plt.grid(axis='y', alpha=0.3)

        plt.tight_layout()  # Grafikler arası boşluğu düzenle
        plt.savefig("su_tuketim_grafikleri.png", dpi=300, bbox_inches='tight')  # Kaydet
        plt.show()  # Grafikleri göster
        print("Grafikler oluşturuldu ve kaydedildi.")

    except Exception as e:
        print(f"Grafik oluşturma hatası: {e}")  # Hata mesajı


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
        waste_data = df[df["ir_state"] == 0].copy()  # IR=0 olan verileri al
        if waste_data.empty:
            return 0.0

        waste_data["timestamp"] = pd.to_datetime(waste_data["timestamp"])  # timestamp'i datetime yap
        waste_data = waste_data.sort_values("timestamp")  # Zaman sırasına göre sırala
        waste_data["time_diff"] = waste_data["timestamp"].diff().dt.total_seconds().fillna(0) / 60.0  # Dakikaya çevir

        waste_data["waste_liters"] = waste_data["flow_lpm"] * waste_data["time_diff"]  # Litreye çevir
        total_waste = waste_data["waste_liters"].sum()  # Toplamı al

        return round(total_waste, 2)
    except Exception as e:
        print(f"Gereksiz tüketim hesaplama hatası: {e}")
        return 0.0


def optimizasyon_analizi(df):
    """Tüketim optimizasyonu analizi yapar ve rapor döndürür"""
    if len(df) < 10:
        return "Yeterli veri yok. Analiz için en az 10 kayıt gerekli."

    ort_debi = ortalama_tuketim(df)  # Ortalama debi
    if ort_debi > FLOW_THRESHOLD:
        debi_uyari = f"Yüksek debi: Ortalama {ort_debi} L/dk (Eşik {FLOW_THRESHOLD} L/dk)"
    else:
        debi_uyari = f"Debi normal: Ortalama {ort_debi} L/dk"

    waste = gereksiz_tuketim_hesapla(df)  # Gereksiz tüketim
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
    kayit_sayaci = 0  # Kaydedilen veri sayacı

    while True:
        try:
            # Seri porttan veri oku
            line = ser.readline().decode('utf-8', errors='ignore').strip()

            if line and "," in line:  # Satır boş değil ve virgül içeriyorsa
                parts = line.split(",")
                if len(parts) >= 3:
                    flow = float(parts[0].strip())  # Anlık debi (L/dk)
                    cumulative = float(parts[1].strip())  # Toplam tüketim (L)
                    ir = int(parts[2].strip())  # IR durumu (0/1)
                    ts = datetime.now()  # Zaman damgası

                    new_row = [ts, flow, cumulative, ir]  # Yeni satır oluştur

                    # CSV ve DataFrame'e kaydet
                    if kaydet_csv(new_row):
                        data.loc[len(data)] = new_row
                        kayit_sayaci += 1

                        # Her 10 kayıtta anlık durumu göster
                        if kayit_sayaci % 10 == 0:
                            print(anlik_gorunum(data))

                    # Her UPDATE_INTERVAL kayıtta analiz yap
                    if kayit_sayaci % UPDATE_INTERVAL == 0 and kayit_sayaci > 0:
                        print("\n" + "=" * 40)
                        print(f"Analiz zamanı! (Kayıt: {kayit_sayaci})")
                        print("=" * 40)

                        print(optimizasyon_analizi(data))  # Analiz raporu yazdır
                        gorsellestir(data)  # Grafik oluştur
                        print("Analiz tamamlandı. Veri kaydı devam ediyor...")
                        print("=" * 40 + "\n")

        except ValueError as e:
            print(f"Veri dönüşüm hatası: {e} | Satır: {line}")  # Veri format hatası
        except Exception as e:
            print(f"Beklenmeyen hata: {e}")  # Genel hata

except KeyboardInterrupt:
    print("\nProgram sonlandırılıyor...")

    if not data.empty:
        print("\nSon durum raporu:")
        print("=" * 30)
        print(optimizasyon_analizi(data))  # Son analiz
        print(f"Toplam kayıt: {len(data)}")
        print(f"Son toplam tüketim: {data['cumulative_liters'].iloc[-1]:.2f} L")

        gorsellestir(data)  # Son grafikleri kaydet ve göster

    ser.close()  # Seri portu kapat
    print("Seri port kapatıldı.")
    print("Program sonlandı.")

except Exception as e:
    print(f"Kritik hata: {e}")
    ser.close()