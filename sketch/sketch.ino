#include <Servo.h>

// === PINS ===
const int laserPin  = 7;
const int redPin    = 9;
const int greenPin  = 10;
const int bluePin   = 11;
const int buzzerPin = 8;
const int ldrPin    = A0;
const int servoPin  = 6;

// === CONFIG ===
int  threshold   = 25;
bool systemActive = false;

// === ALARME ===
bool alarmActive = false;          // true = intrusion non acquittée
unsigned long lastBuzzerToggle = 0;
unsigned long lastLedToggle    = 0;
bool buzzerState = false;
bool ledPhase    = false;

// === SERVO ===
Servo camServo;
int  servoPos  = 90;
int  servoDir  = 1;
int  servoStep = 2;
String servoMode = "auto";
unsigned long lastServoMove = 0;
const int servoDelay = 200;

// === LDR non-bloquant ===
int  ldrReadings[20];
int  ldrIndex        = 0;
unsigned long lastLdrRead = 0;

// ── Couleur LED ──
void setColor(int r, int g, int b) {
  analogWrite(redPin,   255 - r);
  analogWrite(greenPin, 255 - g);
  analogWrite(bluePin,  255 - b);
}

// ── Détection non-bloquante ──
// Retourne true une seule fois quand les 20 échantillons sont prêts
// et que le seuil est dépassé
bool detectIntrusion() {
  if (millis() - lastLdrRead < 30) return false;
  lastLdrRead = millis();

  ldrReadings[ldrIndex++] = analogRead(ldrPin);
  if (ldrIndex < 20) return false;

  ldrIndex = 0;
  int count = 0;
  for (int i = 0; i < 20; i++) {
    if (ldrReadings[i] > threshold) count++;
  }
  return (count > 15);
}

// ── Alarme continue non-bloquante ──
// Appelée à chaque loop() tant que alarmActive == true
void updateAlarm() {
  unsigned long now = millis();

  // LED : alterne rouge / orange toutes les 200 ms
  if (now - lastLedToggle >= 200) {
    lastLedToggle = now;
    ledPhase = !ledPhase;
    if (ledPhase) setColor(255, 0,  0);
    else          setColor(255, 80, 0);
  }

  // Buzzer : bip 120 ms ON / 120 ms OFF
  if (now - lastBuzzerToggle >= 120) {
    lastBuzzerToggle = now;
    buzzerState = !buzzerState;
    if (buzzerState) tone(buzzerPin, 2000);
    else             noTone(buzzerPin);
  }
}

// ── Arrêt alarme ──
void stopAlarm() {
  alarmActive = false;
  noTone(buzzerPin);
  setColor(0, 255, 0);
}

// === COMMANDES SÉRIE ===
void handleCommand(String cmd) {
  cmd.trim();

  if (cmd == "SYSTEM_ON") {
    systemActive = true;
    setColor(0, 255, 0);
    digitalWrite(laserPin, HIGH);
    Serial.println("ACK:SYSTEM_ON");

  } else if (cmd == "SYSTEM_OFF") {
    systemActive = false;
    stopAlarm();
    digitalWrite(laserPin, LOW);
    setColor(0, 0, 0);
    camServo.write(90);
    Serial.println("ACK:SYSTEM_OFF");

  } else if (cmd == "ALARM_ACK") {
    // L'utilisateur a acquitté l'alarme depuis l'interface
    stopAlarm();
    Serial.println("ACK:ALARM_ACK");

  } else if (cmd == "MODE_AUTO") {
    servoMode = "auto";
    Serial.println("ACK:MODE_AUTO");

  } else if (cmd == "MODE_MANUAL") {
    servoMode = "manual";
    Serial.println("ACK:MODE_MANUAL");

  } else if (cmd.startsWith("SERVO:")) {
    int pos = constrain(cmd.substring(6).toInt(), 0, 180);
    servoPos = pos;
    camServo.write(servoPos);
    Serial.print("ACK:SERVO:"); Serial.println(servoPos);

  } else if (cmd == "SERVO_LEFT") {
    servoPos = constrain(servoPos - 15, 0, 180);
    camServo.write(servoPos);
    Serial.print("ACK:SERVO:"); Serial.println(servoPos);

  } else if (cmd == "SERVO_RIGHT") {
    servoPos = constrain(servoPos + 15, 0, 180);
    camServo.write(servoPos);
    Serial.print("ACK:SERVO:"); Serial.println(servoPos);
  }
}

// === SERVO AUTO ===
void updateServoAuto() {
  if (millis() - lastServoMove < servoDelay) return;
  lastServoMove = millis();

  servoPos += servoDir * servoStep;
  if (servoPos >= 90) { 
    servoPos = 90; servoDir = -1; 
  }
  else if (servoPos <= 0) { 
    servoPos = 0; servoDir =  1; 
  }
  camServo.write(servoPos);
}

// === SETUP ===
void setup() {
  pinMode(laserPin,  OUTPUT);
  pinMode(redPin,    OUTPUT);
  pinMode(greenPin,  OUTPUT);
  pinMode(bluePin,   OUTPUT);
  pinMode(buzzerPin, OUTPUT);

  camServo.attach(servoPin);
  camServo.write(servoPos);
  digitalWrite(laserPin, HIGH);

  Serial.begin(9600);
  setColor(0, 255, 0);
}

// === LOOP ===
void loop() {

  // Commandes série
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    handleCommand(cmd);
  }

  if (!systemActive) { delay(50); return; }

  // Alarme active → mise à jour LED + buzzer, rien d'autre
  if (alarmActive) {
    updateAlarm();
    return;  // on ne bouge plus le servo pendant l'alarme
  }

  // Servo auto
  if (servoMode == "auto") updateServoAuto();

  // Détection intrusion
  if (detectIntrusion()) {
    alarmActive = true;
    lastLedToggle    = millis();
    lastBuzzerToggle = millis();
    Serial.println("INTRUSION");
  } else {
    setColor(0, 255, 0);
  }
}