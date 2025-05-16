// include/net.h
#pragma once

#include <Arduino.h>
#include <WiFi.h>
#include <WebSocketsClient.h>
#include <HTTPClient.h>
#include "camera.h"    // for camera_fb_t

/// Call in setup(): connects to Wi-Fi and opens the WS link
void initNetwork();

/// Call in loop(): pumps the WebSocket client
void wsLoop();

/// @returns true if HTTP POST returned 200
bool uploadFrame(camera_fb_t* fb, int seq);
