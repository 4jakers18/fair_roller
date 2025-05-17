#pragma once
#include <stdint.h>

/// Motor spin direction
enum MotorDirection {
  CW,   ///< Clockwise
  CCW   ///< Counter‐clockwise
};

/// Last direction used by spin()
extern MotorDirection motorDir;

/// Initialize the motor pins & PWM channel (call once in setup()).
/// Returns true if initialization succeeded.
bool initMotor();

/// Spin at `speed` (0–255) in `dir` for `duration_ms` ms, then coast.
/// Returns true on success.
bool spin(uint8_t speed, uint32_t duration_ms, MotorDirection dir);

/// Actively brake: PWM full‐on, IN1=IN2=HIGH to short the motor leads.
/// Returns true on success.
bool brake();

/// High‐level helper: perform a “roll die” cycle:
///   1) spin CW at `speed` for `spin_ms`
///   2) Reverse brake. 
/// Returns true on success.
bool roll_die(uint8_t speed, uint32_t spin_ms);
