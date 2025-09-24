// ---------------------------------------------------
// Su Tüketimi Ölçüm Sistemi (Arduino / ESP32)
// ---------------------------------------------------
// Sensörler:
//   - YF-S302 Su Akış Sensörü (pulse çıkışlı debimetre)
//   - IR Sensörü (insan var/yok)
// Çıkış formatı (Python için):
//   flow,cumulative,ir
//
// Örn: 1.25,12.50,1
// ---------------------------------------------------

volatile int pulseCount = 0;    // Akış sensöründen gelen pulse sayısı
float calibrationFactor = 7.5;  // YF-S302 için yaklaşık katsayı (pulse → litre/dk)
float flowRate = 0.0;           // Anlık debi (L/dk)
float totalLiters = 0.0;        // Toplam tüketim (L)
unsigned long oldTime = 0;      // Zaman ölçümü için (ms)

const int flowPin = 2;  // YF-S302 sinyal pini (interrupt destekli pin)
const int irPin = 4;    // IR sensörü pini (dijital giriş)

// ----------------------------
// Kurulum
// ----------------------------
void setup() {
  Serial.begin(9600);              // Baud hızı (Python ile aynı olmalı)
  pinMode(flowPin, INPUT_PULLUP);  // Akış sensörü pini
  pinMode(irPin, INPUT);           // IR sensörü pini

  // Akış sensöründen pulse geldiğinde pulseCounter() çalıştır
  attachInterrupt(digitalPinToInterrupt(flowPin), pulseCounter, FALLING);

  oldTime = millis();  // Başlangıç zamanı kaydet
}

// ----------------------------
// Ana döngü
// ----------------------------
void loop() {
  unsigned long currentTime = millis();

  // Her 1 saniyede bir hesap yap
  if (currentTime - oldTime > 1000) {
    // Geçen süreyi dakika cinsine çevir (ms → dakika)
    float timeDiff = (currentTime - oldTime) / 60000.0;

    // Anlık debi (L/dk) = (pulse sayısı / kalibrasyon katsayısı) / geçen süre (dakika)
    flowRate = (pulseCount / calibrationFactor) / timeDiff;

    // Toplam tüketim (litre) = pulse sayısı / kalibrasyon katsayısı
    totalLiters += (pulseCount / calibrationFactor);

    // IR sensöründen oku (1 = insan var, 0 = yok)
    int irState = digitalRead(irPin);

    // Python’un beklediği formatta seri porta yaz
    // Format: flow,cumulative,ir
    Serial.print(flowRate, 2);  // virgülden sonra 2 basamak
    Serial.print(",");
    Serial.print(totalLiters, 2);
    Serial.print(",");
    Serial.println(irState);

    // Hesap için değerleri sıfırla
    pulseCount = 0;
    oldTime = currentTime;
  }
}

// ----------------------------
// Interrupt Fonksiyonu
// ----------------------------
// Akış sensöründen her pulse geldiğinde bu çalışır
void pulseCounter() {
  pulseCount++;
}