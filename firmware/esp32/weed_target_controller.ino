/*
  Safe pan/tilt controller for the precision-weeding prototype.

  Reference submission mode:
    - PAN / TILT control
    - SAFE INDICATOR
    - E-stop input
    - Physical interlock input

  No hazardous treatment command is implemented.

  The indicator output must only be connected to a safe
  LED/indicator circuit.
*/

#include <Arduino.h>
#include <Servo.h>

Servo panServo;
Servo tiltServo;

constexpr int PAN_PIN = 18;
constexpr int TILT_PIN = 19;

constexpr int INDICATOR_PIN = 23;

constexpr int ESTOP_PIN = 27;
constexpr int INTERLOCK_PIN = 26;

constexpr int PAN_MIN = 20;
constexpr int PAN_MAX = 160;

constexpr int TILT_MIN = 20;
constexpr int TILT_MAX = 120;

bool indicatorCommand = false;

void indicatorOff()
{
  indicatorCommand = false;
  digitalWrite(
      INDICATOR_PIN,
      LOW);
}

bool hardwareSafe()
{
  bool estopActive =
      digitalRead(ESTOP_PIN) == LOW;

  bool enclosureClosed =
      digitalRead(INTERLOCK_PIN) == HIGH;

  return (
      !estopActive && enclosureClosed);
}

void applyIndicatorState()
{
  if (
      indicatorCommand && hardwareSafe())
  {
    digitalWrite(
        INDICATOR_PIN,
        HIGH);
  }
  else
  {
    digitalWrite(
        INDICATOR_PIN,
        LOW);
  }
}

void handleCommand(
    String line)
{
  line.trim();

  if (line.startsWith("PAN "))
  {
    float value =
        line.substring(4).toFloat();

    value = constrain(
        value,
        PAN_MIN,
        PAN_MAX);

    panServo.write(
        (int)value);

    return;
  }

  if (line.startsWith("TILT "))
  {
    float value =
        line.substring(5).toFloat();

    value = constrain(
        value,
        TILT_MIN,
        TILT_MAX);

    tiltServo.write(
        (int)value);

    return;
  }

  if (line == "INDICATOR ON")
  {
    indicatorCommand = true;
    applyIndicatorState();
    return;
  }

  if (line == "INDICATOR OFF")
  {
    indicatorOff();
    return;
  }

  if (line == "E_STOP")
  {
    indicatorOff();
    return;
  }

  if (line == "RESET")
  {
    indicatorOff();
    return;
  }

  if (line == "STATUS")
  {
    Serial.print("SAFE=");
    Serial.print(
        hardwareSafe()
            ? "1"
            : "0");

    Serial.print(
        " INDICATOR=");

    Serial.println(
        indicatorCommand
            ? "1"
            : "0");
  }
}

void setup()
{
  Serial.begin(115200);

  pinMode(
      INDICATOR_PIN,
      OUTPUT);

  pinMode(
      ESTOP_PIN,
      INPUT_PULLUP);

  pinMode(
      INTERLOCK_PIN,
      INPUT_PULLUP);

  indicatorOff();

  panServo.attach(PAN_PIN);
  tiltServo.attach(TILT_PIN);

  panServo.write(90);
  tiltServo.write(70);
}

void loop()
{
  if (Serial.available())
  {
    String line =
        Serial.readStringUntil('\n');

    handleCommand(line);
  }

  // Hardware safety continuously
  // dominates software state.
  applyIndicatorState();

  delay(5);
}