#ifndef SENSOR_MANAGER_H

#define SENSOR_MANAGER_H

/*

Esta clase sera utilizada para manejar todas las operaciones de los sensores

Se encarga de la configuración y lectura de todos los sensores físicos

conectados al ESP32, temperatura (DS18B20) y el de ritmo cardíaco (AD8232)

*/

#include <Arduino.h>

class SensorManager
{

public:
    SensorManager(); // Constructor

    void setup();

    float getTemperature();

    int getHeartRate();
};

#endif