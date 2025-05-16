#include "net.h"
#include "config.h"        // must define WIFI_SSID, WIFI_PASS, SERVER_HOST, SERVER_PORT, WS_PATH

static WebSocketsClient webSocket;

static void handleWsEvent(WStype_t type, uint8_t* payload, size_t length) {
    switch (type) {
        case WStype_CONNECTED:
            Serial.println("✦ WS connected");
            webSocket.sendTXT("ws_hello");              // kick off handshake
            break;

        case WStype_TEXT:
            Serial.printf("→ WS msg: %s\n", (char*)payload);
            // e.g. parse JSON and set your state machine (cmd_start, photo_ack, etc.)
            break;

        case WStype_DISCONNECTED:
            Serial.println("✗ WS disconnected");
            break;

        default:
            break;
    }
}

void initNetwork() {
    // 1) Wi-Fi
    WiFi.begin(WIFI_SSID, WIFI_PASS);
    Serial.print("📶 Connecting to Wi-Fi");
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.println(" ✓");
    Serial.printf("📶 Wi-Fi connected: %s (%s)\n", WiFi.localIP().toString().c_str(), WiFi.SSID().c_str());

    // 2) WebSocket
    webSocket.begin(SERVER_HOST, SERVER_PORT, WS_PATH);
    webSocket.onEvent(handleWsEvent);
    webSocket.setReconnectInterval(5000);           // try reconnect every 5 s
}

void wsLoop() {
    webSocket.loop();
}

bool uploadFrame(camera_fb_t* fb, int seq) {
    if (WiFi.status() != WL_CONNECTED) {
        Serial.println("⚠️ Wi-Fi lost");
        return false;
    }
    HTTPClient http;
    // JPEG POST /upload?seq=<>&frame=<>
    String url = String("http://") + SERVER_HOST + ":" + SERVER_PORT
                 + "/upload?seq=" + seq;
    http.begin(url);
    http.addHeader("Content-Type", "image/jpeg");
    int code = http.POST(fb->buf, fb->len);
    Serial.printf("POST %s → %d\n", url.c_str(), code);
    http.end();
    return (code == HTTP_CODE_OK);
}
