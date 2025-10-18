#ifndef COMMUNICATION_MANAGER_H

#define COMMUNICATION_MANAGER_H

/*

Sera el responsable de establecer y mantener la conexión WiFi, gestionar

el cliente MQTT (conectar, suscribir, publicar) y transmitir los datos al broker.

*/

#include <Arduino.h>

class CommunicationManager
{

public:
    CommunicationManager(); // Constructor

    void setup();

    void loop(); // Para mantener las conexiones activas

    void publishData(const char *payload);
};

#endif