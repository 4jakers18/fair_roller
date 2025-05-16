// src/main.cpp

#include <Arduino.h>
#include "camera.h"   // initCamera(), captureFrame()
#include "motor.h"    // initMotor(), startSpin(), stopSpin(), waitForSpeed()
#include "net.h"      // initNetwork(), wsLoop(), uploadFrame()
#include "config.h"   // pin defs, WiFi creds, server URLs, timing

// LED helper (assumes LED_PIN in config.h)
static void setLED(bool on) {
  digitalWrite(LED_PIN, on ? HIGH : LOW);
}

// Run states
enum RunState {
  DISCONNECTED,
  CONNECTED,
  VERIFY_DIE,
  SPINNING,
  PAUSED,
  FINISHED
};
static RunState state = DISCONNECTED;

void setup() {
  // Serial for debug
  Serial.begin(MONITOR_BAUD);

  // Status LED
  pinMode(LED_PIN, OUTPUT);
  setLED(false);

  // Init modules
  initCamera();     // camera.h
  // initMotor();      // motor.h
  initNetwork();    // net.h  (starts Wi-Fi + WebSocket client)
}

void loop() {
  // Always pump network (WebSocket heartbeats, incoming cmds)
  wsLoop();

  switch (state) {
    case DISCONNECTED:
      // LED breathe / retry WS inside wsLoop()
      break;

    case CONNECTED:
      // Waiting for cmd_start from server
      break;

    case VERIFY_DIE:
    {
      // 1) take test photo
      auto frame = captureFrame();
      // 2) upload & await photo_ack
      if (uploadFrame(frame, /*seq*/0)) {
        state = SPINNING;
      } else {
        state = CONNECTED;
      }
      break;
    }

    case SPINNING:
      // Perform one spin‐capture cycle
      // startSpin();
      // waitForSpeed();
      // stopSpin();
      // delay(SETTLE_MS);
      Serial.println("Spinning...");
      {
        auto frame = captureFrame();
        if (uploadFrame(frame, /*seq*/1)) {
          // tell server step_ok internally
        } else {
          // handle retry or abort
        }
      }
      // Here you’d check if roll count done or server sent cmd_stop
      break;

    case PAUSED:
      // Motor off, waiting for cmd_resume or cmd_stop
      break;

    case FINISHED:
      // Indicate done, LED off
      setLED(false);
      // Wait for next cmd_start
      break;
  }
}
