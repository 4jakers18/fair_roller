// src/camera.cpp
#include "camera.h"
#include <Arduino.h>


bool initCamera() {
  camera_config_t config;
  config.ledc_channel    = LEDC_CHANNEL_0;
  config.ledc_timer      = LEDC_TIMER_0;
  config.pin_d0          = Y2_GPIO_NUM;
  config.pin_d1          = Y3_GPIO_NUM;
  config.pin_d2          = Y4_GPIO_NUM;
  config.pin_d3          = Y5_GPIO_NUM;
  config.pin_d4          = Y6_GPIO_NUM;
  config.pin_d5          = Y7_GPIO_NUM;
  config.pin_d6          = Y8_GPIO_NUM;
  config.pin_d7          = Y9_GPIO_NUM;
  config.pin_xclk        = XCLK_GPIO_NUM;
  config.pin_pclk        = PCLK_GPIO_NUM;
  config.pin_vsync       = VSYNC_GPIO_NUM;
  config.pin_href        = HREF_GPIO_NUM;
  config.pin_sscb_sda    = SIOD_GPIO_NUM;
  config.pin_sscb_scl    = SIOC_GPIO_NUM;
  config.pin_pwdn        = PWDN_GPIO_NUM;
  config.pin_reset       = RESET_GPIO_NUM;
  config.xclk_freq_hz    = 20000000;            // 20 MHz XCLK
  config.pixel_format    = PIXFORMAT_JPEG;      // we want JPEGs

  // Frame parameters
  config.frame_size      = FRAMESIZE_VGA;       // 640×480
  config.jpeg_quality    = 12;                  // 0–63 lower = better
  config.fb_count        = 2;                   // use 2 frame buffers (needs PSRAM)

  // Tell driver to use PSRAM for buffers
  config.grab_mode       = CAMERA_GRAB_LATEST;

  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed: 0x%X\n", err);
    return false;
  }
  Serial.println("Camera initialized");
  return true;
}

camera_fb_t* captureFrame() {
  // grab a frame
  camera_fb_t* fb = esp_camera_fb_get();
  if (!fb) {
    Serial.println("Frame buffer get failed");
    return nullptr;
  }
  return fb;
}
