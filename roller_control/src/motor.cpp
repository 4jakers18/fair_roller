#include <Arduino.h>
#include "motor.h"

// TB6612FNG pins
static constexpr int PWM_PIN  = D10;  // PWM/ENABLE
static constexpr int IN1_PIN  = D9;
static constexpr int IN2_PIN  = D8;

// LEDC (ESP32 PWM) settings
static constexpr int PWM_CH    = 1;
static constexpr int PWM_FREQ  = 1000; // 1 kHz
static constexpr int PWM_RES   = 8;     // 8‐bit

static bool motorInitialized = false;
MotorDirection motorDir = CW;

bool initMotor() {
  pinMode(IN1_PIN, OUTPUT);
  pinMode(IN2_PIN, OUTPUT);
  ledcSetup(PWM_CH, PWM_FREQ, PWM_RES);
  ledcAttachPin(PWM_PIN, PWM_CH);

  // Start in coast (high‐Z) by PWM=0 + both inputs LOW
  ledcWrite(PWM_CH, 0);
  digitalWrite(IN1_PIN, LOW);
  digitalWrite(IN2_PIN, LOW);

  motorInitialized = true;
  return true;
}

bool spin(uint8_t speed, uint32_t duration_ms, MotorDirection dir) {
  if (!motorInitialized) return false;

  motorDir = dir;
  if (dir == CW) {
    digitalWrite(IN1_PIN, HIGH);
    digitalWrite(IN2_PIN, LOW);
  } else {
    digitalWrite(IN1_PIN, LOW);
    digitalWrite(IN2_PIN, HIGH);
  }

  // Run at `speed`
  ledcWrite(PWM_CH, speed);

  // Hold for duration
  delay(duration_ms);

  // Coast: PWM→0, inputs→LOW
  ledcWrite(PWM_CH, 0);
  digitalWrite(IN1_PIN, LOW);
  digitalWrite(IN2_PIN, LOW);

  return true;
}

bool brake() {
  if (!motorInitialized) return false;

  // Active brake: short the outputs
  digitalWrite(IN1_PIN, HIGH);
  digitalWrite(IN2_PIN, HIGH);
  // PWM full‐on (optional, but ensures both FETs conduct)
  ledcWrite(PWM_CH, (1 << PWM_RES) - 1);

  return true;
}


bool roll_die(uint8_t speed, uint32_t spin_ms) {
  if (!motorInitialized) return false;
  // 1) Spin CW
  if (!spin(speed, spin_ms, CW)) return false;
  // 2) Spin CCW for 80% of the time
  uint32_t back_ms = (spin_ms * 8) / 10;
  if (!spin(speed, back_ms, CCW)) return false;
  // 3) Brake
  if (!brake()) return false;

  return true;
}
