// include/config.h
#pragma once

// serial + LED
#define MONITOR_BAUD 115200
#define LED_PIN      D4

// camera/motor timing
#define SETTLE_MS    100
// 
#define DISCARD_FRAMES  5
// Wi-Fi credentials
#include "secrets.h"   // used since this is a public repo <- be sure to make your own from the secrets.h.example

// server info
#define SERVER_HOST  "192.168.68.65" // <- change to your server's IP
#define SERVER_PORT  80
#define WS_PATH      "/ws"
