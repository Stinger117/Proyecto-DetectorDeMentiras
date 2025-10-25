/*
  CommunicationManager.cpp
  ------------------------
  Esta clase se encarga de manejar la comunicación del ESP32 con la red WiFi y el broker MQTT.
  - Conecta el dispositivo a una red WiFi usando las credenciales proporcionadas.
  - Establece y mantiene la conexión con el servidor MQTT.
  - Publica los datos adquiridos por el sensor (por ejemplo, del potenciómetro) en el tema configurado.
  - Se utiliza para enviar los lotes de muestras al servidor en tiempo real, a una frecuencia aproximada de 200 Hz.
  En el futuro, servirá como base para integrar más sensores o manejar distintos canales de comunicación.
*/

#include "CommunicationManager.h"

CommunicationManager::CommunicationManager(const char* server, int port, const char* user, const char* pass, const char* id)
  : mqtt_server(server), mqtt_port(port), mqtt_user(user), mqtt_pass(pass), client_id(id), client(espClient) {
    client.setBufferSize(MQTT_MAX_PACKET_SIZE);
}

void CommunicationManager::connectWiFi(const char* ssid, const char* password) {
    Serial.print("Conectando a WiFi");
    WiFi.begin(ssid, password);

    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }

    Serial.println("\nWiFi conectado!");
    Serial.print("Dirección IP: ");
    Serial.println(WiFi.localIP());
}

void CommunicationManager::connectMQTT() {
    client.setServer(mqtt_server, mqtt_port);
    Serial.print("Intentando conexión MQTT...");

    while (!client.connected()) {
        if (client.connect(client_id, mqtt_user, mqtt_pass)) {
            Serial.println("Conectado!");
        } else {
            Serial.print("Fallo, rc=");
            Serial.print(client.state());
            Serial.println(" reintentando en 3 segundos...");
            delay(3000);
        }
    }
}

void CommunicationManager::publish(const char* topic, const char* payload) {
    if (!client.connected()) {
        connectMQTT();
    }

    bool ok = client.publish(topic, payload);
    if (ok) {
        Serial.println("Lote enviado al MQTT correctamente");
    } else {
        Serial.println("Error al publicar lote. Tamaño de mensaje o broker");
    }
}

void CommunicationManager::loop() {
    if (!client.connected()) {
        connectMQTT();
    }
    client.loop();
}
