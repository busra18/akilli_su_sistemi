
// SU TÜKETİMİ ÖLÇÜM SİSTEMİ 
 // --------------------------------------------------
// Bu kod: Akış ölçer, IR sensörü okur, veriyi OLED'de gösterir
 // ve Python ile analiz için Seri Porta temiz formatta çıktı verir.

// --- KÜTÜPHANELER --
#include <Wire.h>
 #include <U8g2lib.h> // OLED ekran için (daha önce kurduk)
 // --- PIN TANIMLARI --
const int flowPin = 2;  // YF-S302 sinyal pini (D2)
 const int irPin = 4;    // IR sensörü pini (D4 - İnsan var/yok)
 const int redLedPin = 6;     // Kırmızı LED pini (D6) - Akış YOK
 const int greenLedPin = 7;   // Yeşil LED pini (D7) - Akış VAR
 const int flowThreshold = 1; // Akış tespiti için minimum darbe/saniye eşiği
 // --- OLED TANIMLAMA (U8G2 Kütüphanesi ile) --
// Adres 0x3C, SH1106 veya SSD1306 128x64 için en uygun kurulum
 U8G2_SSD1306_128X64_NONAME_F_HW_I2C u8g2(U8G2_R0, U8X8_PIN_NONE); 
// --- DEĞİŞKENLER --
volatile int pulseCount = 0;    // Akış sensöründen gelen pulse sayısı
 float calibrationFactor = 7.5;  // YF-S302 için yaklaşık katsayı (pulse → litre/dk)
float flowRate = 0.0;           // Anlık debi (L/dk)
 float totalLiters = 0.0;        // Toplam tüketim (L)
 unsigned long oldTime = 0;      // Zaman ölçümü için (ms)
 // ---------------------------
// PULSE INTERRUPT FONKSİYONU
 // ---------------------------
void pulseCounter() {
 pulseCount++;
 }
 // ---------------------------
// Kurulum
 // ---------------------------
void setup() {
 Serial.begin(9600);              
// Pin ayarları
 pinMode(flowPin, INPUT_PULLUP);  
pinMode(irPin, INPUT);           
pinMode(redLedPin, OUTPUT);
 pinMode(greenLedPin, OUTPUT);
 // LED'leri başlangıçta KAPAT (Kırmızı yanık olmalı, akış yok)
 digitalWrite(redLedPin, HIGH); 
digitalWrite(greenLedPin, LOW);
// Interrupt başlat
 attachInterrupt(digitalPinToInterrupt(flowPin), pulseCounter, FALLING);
 // OLED başlat
 u8g2.begin();
 u8g2.clearDisplay();
 oldTime = millis();  
}
 // ---------------------------
// Ana döngü
 // ---------------------------
void loop() {
 unsigned long currentTime = millis();
 // Her 1 saniyede bir hesap yap
 if (currentTime - oldTime > 1000) {
 // Hesaplama ve Sıfırlama
 int pulses = pulseCount;
 pulseCount = 0;
 // Geçen süreyi dakika cinsine çevir (ms → dakika)
 float timeDiff = (currentTime - oldTime) / 60000.0;
 // Anlık debi (L/dk) = (pulse sayısı / kalibrasyon katsayısı) / geçen süre (dakika)
 flowRate = (pulses / calibrationFactor) / timeDiff;
// Toplam tüketim (litre)
 // NOT: totalLiters += (pulse sayısı / kalibrasyon katsayısı)
 totalLiters += ((float)pulses / calibrationFactor);
 // IR sensöründen oku 
int irState = digitalRead(irPin);
 // --- 1. LED Kontrolü --
if (pulses >= flowThreshold) {
 digitalWrite(greenLedPin, HIGH); 
digitalWrite(redLedPin, LOW);
 } else {
 digitalWrite(greenLedPin, LOW);
 digitalWrite(redLedPin, HIGH); 
}
 // --- 2. OLED Güncelleme --
updateDisplayU8g2(pulses, irState);
 // --- 3. Python Çıktısı (Seri Port) --
// Format: flow,cumulative,ir
 Serial.print(flowRate, 2);  
Serial.print(",");
 Serial.print(totalLiters, 2);
 Serial.print(",");
 Serial.println(irState);
// Zamanı güncelle
 oldTime = currentTime;
 }
 }
 // ---------------------------
// OLED Güncelleme Fonksiyonu
 // ---------------------------
void updateDisplayU8g2(int pulses, int irState) {
 u8g2.firstPage(); 
do {
 u8g2.setFont(u8g2_font_unifont_tf);
 u8g2.setCursor(0, 10);
 u8g2.print("AKIS: ");
 u8g2.print(flowRate > 0 ? "AKTIF" : "YOK");
 u8g2.setCursor(0, 25);
 u8g2.print("IR: ");
 u8g2.print(irState == HIGH ? "VAR" : "YOK"); // IR sensörünün durumunu yazdır
 // Anlık Akış Hızı
 u8g2.setFont(u8g2_font_fub14_tf); 
u8g2.setCursor(0, 50);
 u8g2.print(flowRate, 2); // 2 ondalık basamak
 u8g2.print(" L/DK");
// Toplam Tüketim
 u8g2.setFont(u8g2_font_unifont_tf);
 u8g2.setCursor(0, 64);
 u8g2.print("TOPLAM: ");
 u8g2.print(totalLiters, 2);
 u8g2.print(" L");
 } while ( u8g2.nextPage() );
 }
