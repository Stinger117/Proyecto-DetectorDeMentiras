/*
  main.cpp
  --------
  Archivo principal del proyecto "Detector de Mentiras" basado en ESP32.

  Este programa integra las clases:
  - SensorManager: que obtiene los datos analógicos del potenciómetro (simulando una señal fisiológica).
  - CommunicationManager: que maneja la conexión WiFi y la transmisión de datos mediante MQTT.

  Flujo general:
  1. Se inicializa el sistema y se conecta a la red WiFi y al broker MQTT.
  2. El ESP32 toma muestras del potenciómetro cada 5 ms (~200 Hz).
  3. Cuando se reúne un lote de datos, se envía en formato JSON al servidor MQTT.
  4. Este envío permitirá analizar la señal más adelante para detectar cambios fisiológicos
     relacionados con el "Detector de Mentiras".

  En el futuro, este archivo servirá como base para integrar sensores adicionales,
  algoritmos de análisis de señal y visualización en tiempo real.
*/

#include <Arduino.h>
#include "SensorManager.h"
#include "CommunicationManager.h"
#include "clavesConfig.h"

SensorManager sensor(34, 128, 5);
CommunicationManager comm(MQTT_SERVER, MQTT_PORT, MQTT_USER, MQTT_PASS, "ESP32_ECG");

void setup() {
    Serial.begin(115200);
    Serial.println("Iniciando Detector de Mentiras");

    comm.connectWiFi(WIFI_SSID, WIFI_PASS);
    comm.connectMQTT();

    Serial.println("Sistema listo.");
}

void loop() {
    comm.loop();

    if (sensor.available()) {
        String lote = sensor.getDataBatchJSON();
        comm.publish(MQTT_TOPIC, lote.c_str());
        Serial.println("Lote enviado al MQTT.");
    }
}
