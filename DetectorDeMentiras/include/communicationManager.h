/*
  CommunicationManager.h
  ----------------------
  Esta clase se encarga de manejar toda la comunicación del ESP32:
  - Conexión WiFi.
  - Conexión y envío de datos mediante MQTT al broker.

  En este proyecto, se utiliza para enviar los datos leídos del potenciómetro
  (que simulan una señal analógica) en formato JSON al servidor MQTT.
  Más adelante, esta estructura se puede reutilizar para enviar señales fisiológicas
  en el sistema del detector de mentiras o cualquier otro sensor conectado al ESP32.
*/

#ifndef COMMUNICATION_MANAGER_H
#define COMMUNICATION_MANAGER_H

#include <WiFi.h>
#include <PubSubClient.h>

#define MQTT_MAX_PACKET_SIZE 1024 

class CommunicationManager {
private:
    WiFiClient espClient;
    PubSubClient client;
    const char* mqtt_server;
    int mqtt_port;
    const char* mqtt_user;
    const char* mqtt_pass;
    const char* client_id;

public:
    CommunicationManager(const char* server, int port, const char* user, const char* pass, const char* id);
    void connectWiFi(const char* ssid, const char* password);
    void connectMQTT();
    void publish(const char* topic, const char* payload);
    void loop();
};

#endif
