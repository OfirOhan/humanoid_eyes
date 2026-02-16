#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver();

// --- PIN MAPPING ---
#define PIN_EYELID_R_LOWER 0
#define PIN_EYELID_R_UPPER 3
#define PIN_EYES_Y         6
#define PIN_EYES_X         8
#define PIN_EYELID_L_UPPER 11
#define PIN_EYELID_L_LOWER 15

// --- CALIBRATED LIMITS ---
#define L_UPPER_OPEN  250
#define L_UPPER_CLOSE 400
#define L_LOWER_OPEN  370
#define L_LOWER_CLOSE 200

#define R_UPPER_OPEN  380
#define R_UPPER_CLOSE 200
#define R_LOWER_OPEN  220
#define R_LOWER_CLOSE 350

#define VERTICAL_DOWN 150
#define VERTICAL_UP   350
#define VERTICAL_MID  250

#define HORIZONTAL_R  150
#define HORIZONTAL_L  300
#define HORIZONTAL_MID 225

// Global position tracker
int currentPos[16];

void setup() {
  Serial.begin(9600);
  Wire.begin();
  pwm.begin();
  pwm.setPWMFreq(50);

  Serial.println("=== Phone Charger Mode: ON ===");

  // Initialize tracker
  for(int i=0; i<16; i++) currentPos[i] = 0;

  // --- SAFE STARTUP SEQUENCE ---
  // Snap to positions one by one to avoid power spikes
  setAndTrack(PIN_EYES_X, HORIZONTAL_MID);
  delay(200);
  setAndTrack(PIN_EYES_Y, VERTICAL_MID);
  delay(200);

  setAndTrack(PIN_EYELID_L_UPPER, L_UPPER_OPEN);
  delay(100);
  setAndTrack(PIN_EYELID_L_LOWER, L_LOWER_OPEN);
  delay(100);
  setAndTrack(PIN_EYELID_R_UPPER, R_UPPER_OPEN);
  delay(100);
  setAndTrack(PIN_EYELID_R_LOWER, R_LOWER_OPEN);
  delay(200);

  Serial.println("System Ready.");
}

void loop() {
  if (Serial.available() > 0) {
    char command = Serial.read();
    int speed = 8; // Good balance for phone chargers

    if (command == 'H') {
      Serial.println("Happy");
      poseHappy(speed);
    }
    else if (command == 'S') {
      Serial.println("Sad");
      poseSad(speed);
    }
    else if (command == 'A') {
      Serial.println("Angry");
      poseAngry(speed);
    }
    else if (command == 'N') {
      Serial.println("Neutral");
      poseNeutral(speed);
    }
    // --- NEW COMMANDS ---
    else if (command == 'R') {
      Serial.println("Look Right");
      lookRight(speed);
    }
    else if (command == 'L') {
      Serial.println("Look Left");
      lookLeft(speed);
    }
    else if (command == 'M') {
      Serial.println("Look Middle");
      lookCenter(speed);
    }
  }
}

// --- HELPER FUNCTIONS ---

void setAndTrack(int pin, int pos) {
  pwm.setPWM(pin, 0, pos);
  currentPos[pin] = pos;
}

void smoothMoveTo(uint8_t pin, uint16_t targetPos, uint16_t stepDelay) {
  uint16_t startPos = currentPos[pin];

  if (startPos == 0) {
    setAndTrack(pin, targetPos);
    return;
  }

  int diff = targetPos - startPos;
  if (diff == 0) return;

  int stepSize = 6;
  int steps = abs(diff) / stepSize;
  if (steps < 1) steps = 1;

  for (int i = 1; i <= steps; i++) {
    uint16_t newPos = startPos + (diff * i / steps);
    pwm.setPWM(pin, 0, newPos);
    delay(stepDelay);
  }

  pwm.setPWM(pin, 0, targetPos);
  currentPos[pin] = targetPos;
  delay(20);
}

// --- POSES ---

void poseNeutral(int speed) {
  smoothMoveTo(PIN_EYES_X, HORIZONTAL_MID, speed);
  smoothMoveTo(PIN_EYES_Y, VERTICAL_MID, speed);

  // Standard Open Eyes
  smoothMoveTo(PIN_EYELID_R_UPPER, R_UPPER_OPEN, speed);
  smoothMoveTo(PIN_EYELID_L_UPPER, L_UPPER_OPEN, speed);
  smoothMoveTo(PIN_EYELID_R_LOWER, R_LOWER_OPEN, speed);
  smoothMoveTo(PIN_EYELID_L_LOWER, L_LOWER_OPEN, speed);
}

void poseHappy(int speed) {
  smoothMoveTo(PIN_EYES_Y, 320, speed);
  smoothMoveTo(PIN_EYES_X, HORIZONTAL_MID, speed);

  smoothMoveTo(PIN_EYELID_R_UPPER, R_UPPER_OPEN, speed);
  smoothMoveTo(PIN_EYELID_L_UPPER, L_UPPER_OPEN, speed);

  // Lower lids squeeze
  smoothMoveTo(PIN_EYELID_L_LOWER, 340, speed);
  smoothMoveTo(PIN_EYELID_R_LOWER, 250, speed);
}

void poseSad(int speed) {
  smoothMoveTo(PIN_EYES_Y, 180, speed);
  smoothMoveTo(PIN_EYES_X, HORIZONTAL_MID, speed);

  // Droopy upper lids
  smoothMoveTo(PIN_EYELID_L_UPPER, 350, speed);
  smoothMoveTo(PIN_EYELID_R_UPPER, 260, speed);

  smoothMoveTo(PIN_EYELID_L_LOWER, L_LOWER_OPEN, speed);
  smoothMoveTo(PIN_EYELID_R_LOWER, R_LOWER_OPEN, speed);
}

void poseAngry(int speed) {
  smoothMoveTo(PIN_EYES_Y, VERTICAL_MID, speed);
  smoothMoveTo(PIN_EYES_X, HORIZONTAL_MID, speed);

  // Squint
  smoothMoveTo(PIN_EYELID_L_UPPER, 360, speed);
  smoothMoveTo(PIN_EYELID_R_UPPER, 240, speed);
  smoothMoveTo(PIN_EYELID_L_LOWER, 260, speed);
  smoothMoveTo(PIN_EYELID_R_LOWER, 310, speed);
}

// --- DIRECTIONAL LOOKS ---
// These reset the eyelids to neutral so you can see the eyes move

void lookRight(int speed) {
  smoothMoveTo(PIN_EYES_X, HORIZONTAL_R, speed); // Move Right
  smoothMoveTo(PIN_EYES_Y, VERTICAL_MID, speed); // Center Y

  // Ensure eyes are open (Neutral state)
  smoothMoveTo(PIN_EYELID_R_UPPER, R_UPPER_OPEN, speed);
  smoothMoveTo(PIN_EYELID_L_UPPER, L_UPPER_OPEN, speed);
  smoothMoveTo(PIN_EYELID_R_LOWER, R_LOWER_OPEN, speed);
  smoothMoveTo(PIN_EYELID_L_LOWER, L_LOWER_OPEN, speed);
}

void lookLeft(int speed) {
  smoothMoveTo(PIN_EYES_X, HORIZONTAL_L, speed); // Move Left
  smoothMoveTo(PIN_EYES_Y, VERTICAL_MID, speed); // Center Y

  // Ensure eyes are open
  smoothMoveTo(PIN_EYELID_R_UPPER, R_UPPER_OPEN, speed);
  smoothMoveTo(PIN_EYELID_L_UPPER, L_UPPER_OPEN, speed);
  smoothMoveTo(PIN_EYELID_R_LOWER, R_LOWER_OPEN, speed);
  smoothMoveTo(PIN_EYELID_L_LOWER, L_LOWER_OPEN, speed);
}

void lookCenter(int speed) {
  smoothMoveTo(PIN_EYES_X, HORIZONTAL_MID, speed); // Move Center
  smoothMoveTo(PIN_EYES_Y, VERTICAL_MID, speed);   // Center Y

  // Ensure eyes are open
  smoothMoveTo(PIN_EYELID_R_UPPER, R_UPPER_OPEN, speed);
  smoothMoveTo(PIN_EYELID_L_UPPER, L_UPPER_OPEN, speed);
  smoothMoveTo(PIN_EYELID_R_LOWER, R_LOWER_OPEN, speed);
  smoothMoveTo(PIN_EYELID_L_LOWER, L_LOWER_OPEN, speed);
}