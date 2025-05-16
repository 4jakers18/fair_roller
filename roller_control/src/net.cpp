// src/net.cpp
#include "net.h"
#include "config.h"

static WebSocketsClient webSocket;

static void handleWsEvent(WStype_t type, uint8_t* payload, size_t length) {
  switch (type) {
    case WStype_CONNECTED:
      state = CONNECTED;
      Serial.println("✦ WS connected → CONNECTED");
      sendWsMsg("ws_hello");
      break;

    case WStype_TEXT: {
      String msg = (char*)payload;
      Serial.printf("→ WS msg: %s\n", msg.c_str());
      if (msg.indexOf("\"evt\":\"ready\"") >= 0 ||
          msg.indexOf("\"cmd\":\"start\"") >= 0) {
        state = VERIFY_DIE;
        Serial.println("↪ state=VERIFY_DIE");
      } else if (msg.indexOf("\"cmd\":\"pause\"") >= 0) {
        state = PAUSED;
      } else if (msg.indexOf("\"cmd\":\"resume\"") >= 0) {
        state = SPINNING;
      } else if (msg.indexOf("\"cmd\":\"stop\"") >= 0) {
        state = FINISHED;
      }
      break;
    }

    case WStype_DISCONNECTED:
      state = DISCONNECTED;
      Serial.println("✗ WS disconnected → DISCONNECTED");
      break;

    default:
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
  // WebSocketsClient::sendTXT needs a non-const String&, so make a copy
  String payload = msg;
  webSocket.sendTXT(payload);
}


  if (type != WStype_TEXT) return;
  String msg = (char*)payload;

  // try to parse JSON
  StaticJsonDocument<256> doc;
  auto err = deserializeJson(doc, msg);
  if (!err && doc["cmd"] == "start") {
    // pull out each field, falling back to previous value if missing
    totalRolls  = doc["rolls"]       | totalRolls;
    settleMs    = doc["settle_ms"]   | settleMs;
    jpegQuality = doc["jpeg_quality"]| jpegQuality;
    String fs   = doc["frame_size"]  | String("VGA");
    // map string to enum
    if (fs == "QVGA") frameSize = FRAMESIZE_QVGA;
    else if (fs == "UXGA") frameSize = FRAMESIZE_UXGA;
    else               frameSize = FRAMESIZE_VGA;

    // apply camera changes immediately
    sensor_t *s = esp_camera_sensor_get();
    s->set_framesize(s, frameSize);
    s->set_quality(s, jpegQuality);

    // reset your sequence counter
    seq = 0;
    state = VERIFY_DIE;
  }
  // handle pause/resume/stop as before...
}