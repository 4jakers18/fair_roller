// include/config.h
#pragma once

// serial + LED
#define MONITOR_BAUD 115200
#define LED_PIN      4

// camera/motor timing
#define SETTLE_MS    100

// Wi-Fi credentials
#include "secrets.h"   // used since this is a public repo <- be sure to make your own from the secrets.h.example

// server info
#define SERVER_HOST  "192.168.0.42" // Address of the server <- change to your server's IP
#define SERVER_PORT  80
#define WS_PATH      "/ws"
