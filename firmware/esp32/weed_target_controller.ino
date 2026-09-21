/*
  Safe pan/tilt controller for the precision-weeding prototype.

  IMPORTANT:
  - Treatment output is OFF after boot.
  - A hardware emergency stop and physical interlock should be wired
    independently of the ML computer.
  - During development, connect TREATMENT_PIN to a safe indicator/LED
    circuit, not a hazardous actuator.
*/

#include <Arduino.h>
#include <Servo.h>

Servo panServo;
Servo tiltServo;

constexpr int PAN_PIN = 18;
constexpr int TILT_PIN = 19;
constexpr int TREATMENT_PIN = 23;
constexpr int ESTOP_PIN = 27;
constexpr int INTERLOCK_PIN = 26;

constexpr int PAN_MIN = 20;
constexpr int PAN_MAX = 160;
constexpr int TILT_MIN = 20;
constexpr int TILT_MAX = 120;

bool treatmentCommand = false;

void treatmentOff() {
  treatmentCommand = false;
  digitalWrite(TREATMENT_PIN, LOW);
}

bool hardwareSafe() {
  bool estopActive = digitalRead(ESTOP_PIN) == LOW;
  bool enclosureClosed = digitalRead(INTERLOCK_PIN) == HIGH;
  return !estopActive && enclosureClosed;
}

void applyTreatmentState() {
  if (treatmentCommand && hardwareSafe()) {
    digitalWrite(TREATMENT_PIN, HIGH);
  } else {
    digitalWrite(TREATMENT_PIN, LOW);
  }
}

void handleCommand(String line) {
  line.trim();

  if (line.startsWith("PAN ")) {
    float value = line.substring(4).toFloat();
    value = constrain(value, PAN_MIN, PAN_MAX);
    panServo.write((int)value);
    return;
  }

  if (line.startsWith("TILT ")) {
    float value = line.substring(5).toFloat();
    value = constrain(value, TILT_MIN, TILT_MAX);
    tiltServo.write((int)value);
    return;
  }

  if (line == "TREAT ON") {
    // Software command alone is not enough; hardwareSafe() is checked.
    treatmentCommand = true;
    applyTreatmentState();
    return;
  }

  if (line == "TREAT OFF") {
    treatmentOff();
    return;
  }

  if (line == "E_STOP") {
    treatmentOff();
    return;
  }

  if (line == "RESET") {
    treatmentOff();
    return;
  }

  if (line == "STATUS") {
    Serial.print("SAFE=");
    Serial.print(hardwareSafe() ? "1" : "0");
    Serial.print(" TREAT=");
    Serial.println(treatmentCommand ? "1" : "0");
  }
}

void setup() {
  Serial.begin(115200);

  pinMode(TREATMENT_PIN, OUTPUT);
  pinMode(ESTOP_PIN, INPUT_PULLUP);
  pinMode(INTERLOCK_PIN, INPUT_PULLUP);

  treatmentOff();

  panServo.attach(PAN_PIN);
  tiltServo.attach(TILT_PIN);

  panServo.write(90);
  tiltServo.write(70);
}

void loop() {
  if (Serial.available()) {
    String line = Serial.readStringUntil('\n');
    handleCommand(line);
  }

  // Hardware safety continuously dominates software command state.
  applyTreatmentState();
  delay(5);
}
