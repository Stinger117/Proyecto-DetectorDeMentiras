/*
 SensorManager.h
 ----------------
 Esta clase se encarga de gestionar las lecturas del módulo ECG AD8232.
 - Toma lecturas continuas de la señal analógica (OUTPUT).
 - Monitorea los pines LO+ y LO- para detectar si los electrodos están desconectados.
 - Agrupa un número definido de muestras (lote) a alta frecuencia.
 - Prepara los datos en formato JSON para ser enviados al broker MQTT.
*/

#ifndef SENSOR_MANAGER_H
#define SENSOR_MANAGER_H

#include <Arduino.h>

class SensorManager {
private:
    // Pines
    int _analogPin;  // Pin para la señal de ECG (OUTPUT)
    int _loPlusPin;  // Pin para "Leads Off" +
    int _loMinusPin; // Pin para "Leads Off" -

    // Configuración de lote
    int _batchSize;
    int _delayMs;
    int _index;
    float* _samples;

public:
    // Constructor actualizado para recibir los 3 pines
    SensorManager(int analogPin, int loPlusPin, int loMinusPin, int batchSize, int delayMs);
    ~SensorManager();

    bool available();             // Indica si un lote de datos está listo
    
    // DEVUELVE EL LOTE EN FORMATO JSON, INCLUYENDO LAS TEMPERATURAS
    String getDataBatchJSON(float temp1, float temp2);    
};

#endif