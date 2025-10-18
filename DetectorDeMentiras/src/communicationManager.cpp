#include <WiFi.h>

#include <PubSubClient.h>

#include "CommunicationManager.h"

#include "clavesConfig.h" // Importamos nuestras claves

// Declaraciones de WiFi y MQTT

WiFiClient espClient;

PubSubClient client(espClient);

// Reconexion

void reconnect();

CommunicationManager::CommunicationManager() {}

void CommunicationManager::setup()
{

    Serial.println();

    Serial.print("Conectando a la red WiFi: ");

    Serial.println(WIFI_SSID);

    WiFi.begin(WIFI_SSID, WIFI_PASS);

    // Esperamos a que la conexión WiFi se establezca

    while (WiFi.status() != WL_CONNECTED)
    {

        delay(500);

        Serial.print(".");
    }

    Serial.println("\nWiFi conectado");

    Serial.print("Dirección IP: ");

    Serial.println(WiFi.localIP());

    // Configuramos el servidor MQTT

    client.setServer(MQTT_SERVER, MQTT_PORT);
}

void CommunicationManager::loop()
{

    // Si no estamos conectados, intentamos reconectar

    if (!client.connected())
    {

        reconnect();
    }

    client.loop();
}

void CommunicationManager::publishData(const char *payload)
{

    if (client.connected())
    {

        client.publish(MQTT_TOPIC, payload);

        Serial.print("Mensaje publicado en el topic '");

        Serial.print(MQTT_TOPIC);

        Serial.print("': ");

        Serial.println(payload);
    }
    else
    {

        Serial.println("No se pudo publicar. Cliente MQTT no conectado.");
    }
}

// Funcion para Reconexion

void reconnect()
{

    while (!client.connected())
    {

        Serial.print("Intentando conexión MQTT...");

        String clientId = "ESP32Client-";

        clientId += String(random(0xffff), HEX);

        if (client.connect(clientId.c_str(), MQTT_USER, MQTT_PASS))
        {

            Serial.println("¡Conectado al broker MQTT!");

            // Aquí podrías suscribirte a topics si fuera necesario

            // client.subscribe("otro_topic");
        }
        else
        {

            Serial.print("falló, rc=");

            Serial.print(client.state());

            Serial.println(" -> Intentando de nuevo en 5 segundos");

            delay(5000);
        }
    }
}