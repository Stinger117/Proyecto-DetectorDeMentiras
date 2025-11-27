#ifndef CLAVESCONFIG_H
#define CLAVESCONFIG_H

// IMPORTANTE
// Cuando uses el proyecto, copia este archivo y renómbralo a "clavesConfig.h"
// Luego agrega tus propias claves de WiFi y MQTT aquí:
// Configuración WiFi

const char *WIFI_SSID = "TU_RED_WIFI";
const char *WIFI_PASS = "TU_PASSWORD_WIFI";

// Configuración servidor HTTP en caso de uso
const char *SERVER_URL = "http://TU_SERVIDOR/sensor";

// Configuración MQTT
const char *MQTT_SERVER = "broker.ejemplo.com";
const int MQTT_PORT = 1883;
const char *MQTT_USER = "usuario";
const char *MQTT_PASS = "password";
#endif