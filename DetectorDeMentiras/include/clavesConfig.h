#ifndef CLAVESCONFIG_H
#define CLAVESCONFIG_H

// IMPORTANTE
// Cuando uses el proyecto, copia este archivo y renómbralo a "clavesConfig.h"
// Luego agrega tus propias claves de WiFi y MQTT aquí:
// Configuración WiFi

const char *WIFI_SSID = "Totalplay-2.4G-1530";
const char *WIFI_PASS = "TBaRURSXexXKA3bu";

// Configuración servidor HTTP en caso de uso
const char *SERVER_URL = "http://TU_SERVIDOR/sensor";

// Configuración MQTT
const char *MQTT_SERVER = "broker.emqx.io";
const int MQTT_PORT = 1883;
const char *MQTT_USER = "root";
const char *MQTT_PASS = "root";
#endif 