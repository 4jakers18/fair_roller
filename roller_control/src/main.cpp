#include <Arduino.h>
#include "state.h"
#include "camera.h"
#include "net.h"
#include "config.h"
#include "motor.h"


RunState state = DISCONNECTED;

int    seq           = 0;
int    totalRolls    = 10;
bool   finishedSent  = false;
int    warmupCount   = 0;

static constexpr uint8_t  MOTOR_SPEED = 200;
static constexpr uint32_t SPIN_MS     = 500;

// LED / PWM settings
static constexpr int LEDC_CHANNEL  = 2;
static constexpr int LEDC_FREQ     = 500;          // 500 Hz for breathing
static constexpr int LEDC_RES      = 8;            // 8-bit
static int           ledBrightness = 0;
static int           ledFadeAmount = 4;           // change per loop


static void setLED(bool on) {
  // full brightness or off
  ledcWrite(LEDC_CHANNEL, on ? 128 : 0);
}


void setup() {
  Serial.begin(MONITOR_BAUD);

  // Camera, network, motor
  initCamera();
  initNetwork();
  initMotor();

  // LED PWM for breathing/solid
  ledcSetup(LEDC_CHANNEL, LEDC_FREQ, LEDC_RES);
  ledcAttachPin(LED_PIN, LEDC_CHANNEL);
  setLED(true);

  // Initialize state
  state = DISCONNECTED;
}

//  Main Loop 

void loop() {
  wsLoop();  
  uint32_t now = millis();

  switch (state) {

    case DISCONNECTED:
      // breathing LED
      ledBrightness += ledFadeAmount;
      if (ledBrightness <= 0 || ledBrightness >= 255) {
        ledFadeAmount = -ledFadeAmount;
        ledBrightness = constrain(ledBrightness, 0, 255);
      }
      ledcWrite(LEDC_CHANNEL, ledBrightness);
      break;

    case CONNECTED:
      // solid on
      setLED(true);
      break;

    case VERIFY_DIE: {
      if (warmupCount > 0) {
        auto f = captureFrame();
        if (f) esp_camera_fb_return(f);
        Serial.printf("🛑 Discard warm-up frame, %d left\n", warmupCount);
        warmupCount--;
        delay(100);
        break;
      }
      // capture & upload test photo
      uint32_t t0 = millis();
      auto frame = captureFrame();
      uint32_t t1 = millis();
      if (!frame) {
        Serial.printf("❌ VERIFY_DIE: no frame (%ums)\n", t1 - t0);
        delay(100);
        break;
      }
      Serial.printf("✅ VERIFY_DIE: %u bytes in %u ms\n", frame->len, t1 - t0);

      uint32_t t2 = millis();
      bool ok = uploadFrame(frame, 0);
      uint32_t t3 = millis();
      Serial.printf("→ uploadFrame(0) %s in %u ms\n", ok?"OK":"FAIL", t3 - t2);
      esp_camera_fb_return(frame);

      if (ok) {
        seq = 1;
        state = SPINNING;
        Serial.println("↪ state=SPINNING");
      } else {
        state = CONNECTED;
        Serial.println("↪ state=CONNECTED");
      }
      break;
    }

    case SPINNING: {
      setLED(true);
      Serial.printf("🔄 SPINNING %d/%d\n", seq, totalRolls);

      // spin → coast
      spin(MOTOR_SPEED, SPIN_MS, CW);

      delay(settleMs);
      auto frame = captureFrame();
      if (frame) {
        if (uploadFrame(frame, seq)) {
          sendWsMsg("{\"evt\":\"step_ok\",\"seq\":" + String(seq) + "}");
          seq++;
          if (seq >= totalRolls) {
            state = FINISHED;
          }
        } else {
          Serial.println("⚠️ uploadFrame failed");
        }
        esp_camera_fb_return(frame);
      } else {
        Serial.println("❌ captureFrame failed");
      }
      break;
    }

    case PAUSED:
      // actively brake and hold
      brake();
      break;

    case FINISHED:
      setLED(true);
      brake();
      if (!finishedSent) {
        sendWsMsg("{\"evt\":\"finished\"}");
        Serial.println("✅ FINISHED");
        finishedSent = true;
      }
      break;
  }

  delay(10);
}
