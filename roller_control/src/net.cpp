// src/net.cpp

#include "net.h"
#include "camera.h"
#include "config.h"
#include "state.h"         // for state, seq, totalRolls
#include <ArduinoJson.h>   // JSON parsing

static WebSocketsClient webSocket;

static void handleWsEvent(WStype_t type, uint8_t* payload, size_t length) {
  switch (type) {
    case WStype_CONNECTED:
      state = CONNECTED;
      Serial.println("✦ WS connected → CONNECTED");
      sendWsMsg("ws_hello");
      break;

    case WStype_TEXT: {
      // Parse JSON in-place from the raw payload
      DynamicJsonDocument doc(512);
      auto err = deserializeJson(doc, payload, length);
      if (err) {
        Serial.printf("⚠️ JSON parse failed: %s\n", err.c_str());
        return;
      }

      // Log the received message
      Serial.print("→ WS msg: ");
      serializeJson(doc, Serial);
      Serial.println();

      const char* cmd = doc["cmd"] | "";
      if (strcmp(cmd, "start") == 0) {
        // Extract dynamic run parameters (with fallbacks)
        totalRolls  = doc["rolls"]        | totalRolls;
        settleMs    = doc["settle_ms"]    | settleMs;
        jpegQuality = doc["jpeg_quality"] | jpegQuality;

        // Map frame_size string to framesize_t
        const char* fs = doc["frame_size"] | "VGA";
        if      (strcmp(fs, "QVGA") == 0) frameSize = FRAMESIZE_QVGA;
        else if (strcmp(fs, "UXGA") == 0) frameSize = FRAMESIZE_UXGA;
        else                               frameSize = FRAMESIZE_VGA;

        // Apply camera settings immediately
        {
          sensor_t *s = esp_camera_sensor_get();
          s->set_framesize(s, frameSize);
          s->set_quality(s, jpegQuality);
        }
        // Reset for a new run
        seq          = 0;
        finishedSent = false;     // ← clear the “finished” flag here
        warmupCount  = DISCARD_FRAMES;   // ← throw away the next x captures
        state        = VERIFY_DIE;
        Serial.println("↪ state=VERIFY_DIE");

      } else if (strcmp(cmd, "pause") == 0) {
        state = PAUSED;
        Serial.println("↪ state=PAUSED");

      } else if (strcmp(cmd, "resume") == 0) {
        state = SPINNING;
        Serial.println("↪ state=SPINNING");

      } else if (strcmp(cmd, "stop") == 0) {
        state = FINISHED;
        Serial.println("↪ state=FINISHED");
      }
      break;
    }

    case WStype_DISCONNECTED:
      state = DISCONNECTED;
      Serial.println("✗ WS disconnected → DISCONNECTED");
      break;

    default:
      // ignore other event types
      break;
  }
}

void initNetwork() {
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  Serial.print("📶 Connecting to Wi-Fi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println(" ✓");

  webSocket.begin(SERVER_HOST, SERVER_PORT, WS_PATH);
  webSocket.onEvent(handleWsEvent);
  webSocket.setReconnectInterval(5000);
}

void wsLoop() {
  webSocket.loop();
}

bool uploadFrame(camera_fb_t* fb, int seq) {
  if (WiFi.status() != WL_CONNECTED) return false;
  HTTPClient http;
  String url = String("http://") + SERVER_HOST + ":" + SERVER_PORT
               + "/upload?seq=" + seq;
  http.begin(url);
  http.addHeader("Content-Type", "image/jpeg");
  int code = http.POST(fb->buf, fb->len);
  Serial.printf("POST %s → %d\n", url.c_str(), code);
  http.end();
  return (code == HTTP_CODE_OK);
}

void sendWsMsg(const String &msg) {
  // WebSocketsClient::sendTXT wants a non-const String&
  String payload = msg;
  webSocket.sendTXT(payload);
}
