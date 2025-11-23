#ifndef CLAVESCONFIG_H
#define CLAVESCONFIG_H

// Configuración WiFi
const char *WIFI_SSID = "Totalplay-7E26";
const char *WIFI_PASS = "7E26986E7T3EcTW4";

// Configuración servidor HTTP en caso de uso
const char *SERVER_URL = "http://192.168.0.9:5000/sensor";

// Configuración MQTT   
const char *MQTT_SERVER = "broker.emqx.io";
const int MQTT_PORT = 1883;
const char *MQTT_USER = "administrador";
const char *MQTT_PASS = "JRJGJ05";
const char *MQTT_TOPIC = "iot2/proyecto/sensor";
#endif