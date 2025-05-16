#include <Arduino.h>
#include "state.h"    
#include "camera.h"
#include "net.h"
#include "config.h"
#include "state.h"   

RunState state = DISCONNECTED;  // <-- the one-and-only definition

// sequence counter
int seq = 0;
int totalRolls    = 10;      // from server



// LED helper (assumes LED_PIN in config.h)
static void setLED(bool on) {
  digitalWrite(LED_PIN, on ? HIGH : LOW);
}

// LED heartbeat
static uint32_t lastBlink = 0;
static bool     ledOn     = false;

void setup() {
  Serial.begin(MONITOR_BAUD);
  pinMode(LED_PIN, OUTPUT);
  setLED(false);
  initCamera();
  initNetwork();
}

void loop() {
  wsLoop();  // pumps WS + invokes your handleWsEvent()

  uint32_t now = millis();
  switch (state) {
    case DISCONNECTED:
      if (now - lastBlink > 500) {
        lastBlink = now;
        ledOn = !ledOn;
        setLED(ledOn);
      }
      break;

    case CONNECTED:
      setLED(true);
      break;

case VERIFY_DIE: {
  // 1) Time the capture
  uint32_t t0 = millis();
  camera_fb_t *frame = captureFrame();
  uint32_t t1 = millis();

  if (!frame) {
    Serial.printf("❌ VERIFY_DIE: captureFrame() returned NULL (took %u ms)\n", t1 - t0);
    // Optionally retry or fall back
    delay(100);
    break;
  } 

  Serial.printf("✅ VERIFY_DIE: got frame (%u bytes) in %u ms\n", frame->len, t1 - t0);

  // 2) Time the upload
  uint32_t t2 = millis();
  bool ok = uploadFrame(frame, 0);
  uint32_t t3 = millis();
  Serial.printf("→ uploadFrame(seq=0) returned %s in %u ms\n",
                ok ? "OK" : "FAIL", t3 - t2);

  // 3) Free the buffer
  esp_camera_fb_return(frame);

  // 4) Advance state
  if (ok) {
    seq = 1;
    state = SPINNING;
    Serial.println("↪ state=SPINNING");
  } else {
    state = CONNECTED;
    Serial.println("↪ state=CONNECTED (retry VERIFY_DIE later)");
  }
  break;
}



    case SPINNING: {
      Serial.println("Spinning...");
      auto frame = captureFrame();
      if (frame) {
        delay(settleMs); 
        bool ok = uploadFrame(frame, seq);
        esp_camera_fb_return(frame);
        if (ok) {
          sendWsMsg("{\"evt\":\"step_ok\",\"seq\":" + String(seq) + "}");
          if (++seq >= totalRolls) {
            state = FINISHED;
          }
        }
      }
      break;
    }

    case PAUSED:
      // maybe flash LED slower here
      break;

    case FINISHED:
      setLED(false);
      sendWsMsg("{\"evt\":\"finished\"}");
      // wait for next cmd_start
      break;
  }

  delay(10);
}

