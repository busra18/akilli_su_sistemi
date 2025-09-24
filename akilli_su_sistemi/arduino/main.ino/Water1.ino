// =======================================
// AKILLI SU TÜKETİMİ - ARDUINO KODU
// =======================================

// --- PIN TANIMLARI ---
const int flowPin = 2;  // Akış sensörü pini
const int irPin = 3;    // IR sensörü pini

// --- DEĞİŞKENLER ---
volatile int pulseCount = 0;    // Flow sensörü pulse sayısı
float calibrationFactor = 4.5;  // Flow sensörü kalibrasyon faktörü (L/dk başına pulse)
float flowRate = 0.0;           // Anlık debi (L/dk)
float cumulativeLiters = 0.0;   // Toplam tüketim (L)

unsigned long oldTime = 0;  // Zaman kontrolü (ms)

// =======================================
// PULSE INTERRUPT FONKSİYONU
// =======================================
// Flow sensöründen pulse geldiğinde sayacı artır
void pulseCounter() {
  pulseCount++;
}

// =======================================
// SETUP
// =======================================
void setup() {
  Serial.begin(9600);                                                     // Seri haberleşmeyi başlat (Python ile uyumlu)
  pinMode(flowPin, INPUT_PULLUP);                                         // Flow sensörü pini input
  pinMode(irPin, INPUT);                                                  // IR sensörü pini input
  attachInterrupt(digitalPinToInterrupt(flowPin), pulseCounter, RISING);  // Pulse interrupt
}

// =======================================
// LOOP
// =======================================
void loop() {
  unsigned long currentTime = millis();  // Mevcut zaman (ms)

  // Her 1 saniyede bir hesaplama yap
  if (currentTime - oldTime >= 1000) {
    detachInterrupt(digitalPinToInterrupt(flowPin));  // Hesaplama sırasında interrupt kapat

    // --- DEBİ HESAPLAMA ---
    flowRate = ((float)pulseCount / calibrationFactor);  // Pulse → L/dk
    cumulativeLiters += (flowRate / 60.0);               // 1 saniyelik litre ekle

    pulseCount = 0;         // Pulse sayacını sıfırla
    oldTime = currentTime;  // Zamanı güncelle

    // --- IR SENSÖRÜ DURUMU ---
    int irState = digitalRead(irPin);  // 0 = yok, 1 = var

    // --- SERİ PORTA VERİ GÖNDER ---
    // Python'un beklediği format: flow,cumulative,ir
    Serial.print(flowRate, 2);  // 2 ondalık basamaklı debi
    Serial.print(",");
    Serial.print(cumulativeLiters, 2);  // 2 ondalık basamaklı toplam litre
    Serial.print(",");
    Serial.println(irState);  // IR durumu

    attachInterrupt(digitalPinToInterrupt(flowPin), pulseCounter, RISING);  // Interrupt tekrar aç
  }
}