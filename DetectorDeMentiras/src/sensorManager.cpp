#include "SensorManager.h"



SensorManager::SensorManager() {}



// Esperar a tener los datos de los sensores para colocar el codigo

void SensorManager::setup() {

    Serial.println("Inicializando SensorManager (modo simulación)...");

}



// Datos de simulacion de temperatura

float SensorManager::getTemperature() {

    // Simula una temperatura de piel entre 31.0 y 33.0 °C

    return 32.0 + (random(-10, 10) / 10.0);

}



// Datos de simulacion de ritmo cardiaco

int SensorManager::getHeartRate() {

    return random(60, 120);

}  