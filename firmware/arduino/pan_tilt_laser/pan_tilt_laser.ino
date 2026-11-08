/*
  Pan/tilt laser controller (Arduino Uno / Nano) for the precision-weeding prototype.

  Wiring:
    - Pan servo signal   -> D9
    - Tilt servo signal  -> D10
    - Laser driver input -> D3   (via MOSFET/transistor or laser driver module)
    - E-stop button      -> D4 to GND (normally open, optional; pressed = laser off)
    - Servo power from an external 5-6 V supply, grounds tied to the Arduino GND.

  Serial protocol (115200 baud, one command per line, '\n' terminated):
    PAN <deg>          move pan servo  (clamped to PAN_MIN..PAN_MAX)
    TILT <deg>         move tilt servo (clamped to TILT_MIN..TILT_MAX)
    MOVE <pan> <tilt>  move both servos
    LASER ON           request laser on
    LASER OFF          laser off (also clears a max-on-time lockout)
    INDICATOR ON/OFF   alias for LASER ON/OFF (older host code)
    E_STOP             laser off and latched until RESET
    RESET              clear software E-stop latch
    CENTER             move servos to the center position
    STATUS             print current state
    PING               reply PONG (keeps the watchdog alive)

  Angles are fractional degrees, sent to the servos as microsecond pulses
  (~0.1 deg resolution) so the calibration can aim finer than 1 deg.

  Firmware safety (always dominates host commands):
    - Laser starts OFF on boot.
    - Watchdog: laser OFF if no command arrives for WATCHDOG_MS
      (host crashed, cable unplugged, frozen detection loop).
    - Max on-time: laser OFF after MAX_LASER_ON_MS of continuous firing,
      locked out until the host sends LASER OFF.
    - Laser OFF while the E-stop button is pressed or a software E_STOP is latched.
    - Laser OFF while the servos are still travelling to a new position.
*/

#include <Arduino.h>
#include <Servo.h>

constexpr uint8_t PAN_PIN = 9;
constexpr uint8_t TILT_PIN = 10;
constexpr uint8_t LASER_PIN = 13;
constexpr uint8_t ESTOP_PIN = 4;

constexpr int PAN_MIN = 20;
constexpr int PAN_MAX = 160;
constexpr int TILT_MIN = 20;
constexpr int TILT_MAX = 120;

constexpr int PAN_CENTER = 90;
constexpr int TILT_CENTER = 70;

// Pulse widths for 0 and 180 degrees (Servo library defaults).
// Adjust if your servos do not reach their full range.
constexpr int SERVO_MIN_US = 544;
constexpr int SERVO_MAX_US = 2400;

constexpr unsigned long WATCHDOG_MS = 500;
constexpr unsigned long MAX_LASER_ON_MS = 3000;

// Rough servo travel time per degree; the laser stays off while the servos move.
constexpr unsigned long SETTLE_MS_PER_DEG = 3;
constexpr unsigned long MIN_SETTLE_MS = 40;

// Moves smaller than this are treated as tracking jitter and do not re-trigger settling.
constexpr float MOVE_DEADBAND_DEG = 0.2;

Servo panServo;
Servo tiltServo;

float panDeg = PAN_CENTER;
float tiltDeg = TILT_CENTER;

bool laserRequested = false;
bool laserIsOn = false;
bool estopLatched = false;
bool maxOnLockout = false;

unsigned long lastCommandMs = 0;
unsigned long laserOnSinceMs = 0;
unsigned long servoSettledAtMs = 0;

char lineBuf[48];
uint8_t lineLen = 0;

int degToUs(float deg)
{
  return (int)lround(SERVO_MIN_US + deg * (SERVO_MAX_US - SERVO_MIN_US) / 180.0);
}

void setLaser(bool on)
{
  digitalWrite(LASER_PIN, on ? HIGH : LOW);
  if (on && !laserIsOn)
  {
    laserOnSinceMs = millis();
  }
  laserIsOn = on;
}

bool estopPressed()
{
  return digitalRead(ESTOP_PIN) == LOW;
}

void moveServo(Servo &servo, float &current, float target, int lo, int hi)
{
  target = constrain(target, lo, hi);
  float delta = fabs(target - current);

  if (delta < MOVE_DEADBAND_DEG)
  {
    return;
  }

  current = target;
  servo.writeMicroseconds(degToUs(target));

  unsigned long settle = max(MIN_SETTLE_MS, (unsigned long)(delta * SETTLE_MS_PER_DEG));
  servoSettledAtMs = max(servoSettledAtMs, millis() + settle);
}

void printStatus()
{
  Serial.print(F("PAN="));
  Serial.print(panDeg, 2);
  Serial.print(F(" TILT="));
  Serial.print(tiltDeg, 2);
  Serial.print(F(" LASER="));
  Serial.print(laserIsOn ? 1 : 0);
  Serial.print(F(" REQ="));
  Serial.print(laserRequested ? 1 : 0);
  Serial.print(F(" ESTOP="));
  Serial.print((estopLatched || estopPressed()) ? 1 : 0);
  Serial.print(F(" LOCKOUT="));
  Serial.println(maxOnLockout ? 1 : 0);
}

void handleCommand(char *line)
{
  if (strncmp(line, "PAN ", 4) == 0)
  {
    moveServo(panServo, panDeg, atof(line + 4), PAN_MIN, PAN_MAX);
  }
  else if (strncmp(line, "TILT ", 5) == 0)
  {
    moveServo(tiltServo, tiltDeg, atof(line + 5), TILT_MIN, TILT_MAX);
  }
  else if (strncmp(line, "MOVE ", 5) == 0)
  {
    char *rest = line + 5;
    char *end = nullptr;
    float pan = strtod(rest, &end);
    float tilt = atof(end);
    moveServo(panServo, panDeg, pan, PAN_MIN, PAN_MAX);
    moveServo(tiltServo, tiltDeg, tilt, TILT_MIN, TILT_MAX);
  }
  else if (strcmp(line, "LASER ON") == 0 || strcmp(line, "INDICATOR ON") == 0)
  {
    laserRequested = true;
  }
  else if (strcmp(line, "LASER OFF") == 0 || strcmp(line, "INDICATOR OFF") == 0)
  {
    laserRequested = false;
    maxOnLockout = false;
  }
  else if (strcmp(line, "E_STOP") == 0)
  {
    estopLatched = true;
    laserRequested = false;
  }
  else if (strcmp(line, "RESET") == 0)
  {
    estopLatched = false;
    maxOnLockout = false;
    laserRequested = false;
  }
  else if (strcmp(line, "CENTER") == 0)
  {
    moveServo(panServo, panDeg, PAN_CENTER, PAN_MIN, PAN_MAX);
    moveServo(tiltServo, tiltDeg, TILT_CENTER, TILT_MIN, TILT_MAX);
  }
  else if (strcmp(line, "STATUS") == 0)
  {
    printStatus();
  }
  else if (strcmp(line, "PING") == 0)
  {
    Serial.println(F("PONG"));
  }
  else
  {
    Serial.print(F("ERR "));
    Serial.println(line);
  }
}

void readSerial()
{
  while (Serial.available())
  {
    char c = (char)Serial.read();

    if (c == '\r')
    {
      continue;
    }

    if (c == '\n')
    {
      lineBuf[lineLen] = '\0';
      if (lineLen > 0)
      {
        lastCommandMs = millis();
        handleCommand(lineBuf);
      }
      lineLen = 0;
    }
    else if (lineLen < sizeof(lineBuf) - 1)
    {
      lineBuf[lineLen++] = c;
    }
    else
    {
      // Overlong line: drop it.
      lineLen = 0;
    }
  }
}

void setup()
{
  // Laser pin goes LOW before anything else.
  pinMode(LASER_PIN, OUTPUT);
  digitalWrite(LASER_PIN, LOW);

  pinMode(ESTOP_PIN, INPUT_PULLUP);

  Serial.begin(115200);

  panServo.attach(PAN_PIN, SERVO_MIN_US, SERVO_MAX_US);
  tiltServo.attach(TILT_PIN, SERVO_MIN_US, SERVO_MAX_US);
  panServo.writeMicroseconds(degToUs(PAN_CENTER));
  tiltServo.writeMicroseconds(degToUs(TILT_CENTER));

  servoSettledAtMs = millis() + 500;
  lastCommandMs = millis();

  Serial.println(F("READY pan_tilt_laser"));
}

void loop()
{
  readSerial();

  unsigned long now = millis();

  if (estopPressed())
  {
    laserRequested = false;
  }

  if (now - lastCommandMs > WATCHDOG_MS)
  {
    laserRequested = false;
  }

  if (laserIsOn && now - laserOnSinceMs > MAX_LASER_ON_MS)
  {
    maxOnLockout = true;
  }

  bool servosSettled = (long)(now - servoSettledAtMs) >= 0;

  bool fire = laserRequested && servosSettled && !estopLatched && !estopPressed() && !maxOnLockout;

  setLaser(fire);
}
