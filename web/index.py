from flask import Flask, render_template, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO
import threading
import json

import paho.mqtt.client as mqtt
import numpy as np
from scipy.signal import iirnotch, butter, filtfilt, find_peaks

# --------------------------------------------------------------------------
# CONFIGURACIÓN FLASK + SOCKET.IO
# --------------------------------------------------------------------------

app = Flask(__name__)
CORS(app)

# Usa 'threading' para que funcione sin eventlet
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")
# También podría ser: socketio = SocketIO(app, cors_allowed_origins="*")

# --------------------------------------------------------------------------
# CONFIGURACIÓN MQTT
# --------------------------------------------------------------------------

MQTT_BROKER = "broker.emqx.io"
MQTT_PORT   = 1883
MQTT_TOPIC  = "iot2/proyecto/sensor"
MQTT_USER   = "administrador"
MQTT_PASS   = "JRJGJ05"

# --------------------------------------------------------------------------
# PARÁMETROS DE SEÑAL
# --------------------------------------------------------------------------

FS = 333                 # Hz
WINDOW_SEC = 60          # ventana HRV
SAMPLES_WINDOW = FS * WINDOW_SEC

# buffer ECG filtrado
ecg_filtered = []

# Métricas compartidas con el frontend
latest_metrics = {
    "bpm":    None,
    "sdnn":   None,
    "rmssd":  None,
    "pnn50":  None,
    "temp_1": None,
    "temp_2": None,
    "status": "Esperando datos...",
    "progress": 0
}

# --------------------------------------------------------------------------
# FILTROS
# --------------------------------------------------------------------------

b_notch, a_notch = iirnotch(60.0, 30.0, FS)              # Notch 60 Hz
b_lp, a_lp       = butter(4, 100.0 / (FS / 2.0), 'low')  # LP 100 Hz


def filter_batch(samples):
    """Aplica notch + lowpass y normaliza a ~[-1, 1]."""
    if not samples:
        return []

    x = np.array(samples, dtype=float)

    try:
        x = filtfilt(b_notch, a_notch, x)
        x = filtfilt(b_lp, a_lp, x)
    except Exception as e:
        print("Error filtrando lote:", e)
        return x.tolist()

    x = x - np.mean(x)
    max_abs = np.max(np.abs(x))
    if max_abs > 0:
        x = x / max_abs

    return x.tolist()

# --------------------------------------------------------------------------
# CÁLCULO HRV (cada ~60 s)
# --------------------------------------------------------------------------


def calculate_hrv_metrics(signal_data):
    global latest_metrics

    if not signal_data or len(signal_data) < FS * 5:
        latest_metrics["status"] = "Señal insuficiente para HRV"
        socketio.emit('new_decision', latest_metrics)
        return

    socketio.emit('update_status', {"data": "Calculando HRV..."})

    data_np = np.array(signal_data, dtype=float)

    distance = int(0.5 * FS)  # mínimo ~0.5 s entre picos
    height   = np.mean(data_np)
    peaks, _ = find_peaks(data_np, distance=distance, height=height)

    if len(peaks) < 2:
        latest_metrics["status"] = "Pocos picos para calcular HRV"
        socketio.emit('new_decision', latest_metrics)
        socketio.emit('update_status', {"data": "Pocos picos detectados"})
        return

    peaks_time_ms = (peaks / FS) * 1000.0
    rr_intervals  = np.diff(peaks_time_ms)

    if len(rr_intervals) < 2:
        latest_metrics["status"] = "Pocos intervalos RR"
        socketio.emit('new_decision', latest_metrics)
        return

    mean_rr = np.mean(rr_intervals)
    if mean_rr <= 0:
        latest_metrics["status"] = "RR medio no válido"
        socketio.emit('new_decision', latest_metrics)
        return

    bpm  = 60000.0 / mean_rr
    sdnn = np.std(rr_intervals, ddof=1)

    diff_rr = np.diff(rr_intervals)
    if len(diff_rr) > 0:
        rmssd = np.sqrt(np.mean(diff_rr ** 2))
        nn50  = np.sum(np.abs(diff_rr) > 50.0)
        pnn50 = (nn50 / len(diff_rr)) * 100.0
    else:
        rmssd = 0.0
        pnn50 = 0.0

    latest_metrics.update({
        "bpm":   round(float(bpm),   2),
        "sdnn":  round(float(sdnn),  2),
        "rmssd": round(float(rmssd), 2),
        "pnn50": round(float(pnn50), 2),
        "status": "Métricas actualizadas"
    })

    print("\n" + "=" * 40)
    print("NUEVAS MÉTRICAS (ventana de ~60s):")
    print(f"- BPM:   {bpm:.2f}")
    print(f"- SDNN:  {sdnn:.2f} ms")
    print(f"- RMSSD: {rmssd:.2f} ms")
    print(f"- PNN50: {pnn50:.2f} %")
    print(f"- Temp1: {latest_metrics['temp_1']}")
    print(f"- Temp2: {latest_metrics['temp_2']}")
    print("=" * 40 + "\n")

    socketio.emit('new_decision', latest_metrics)
    socketio.emit('update_status', {"data": "Métricas HRV actualizadas"})

# --------------------------------------------------------------------------
# MQTT
# --------------------------------------------------------------------------


def on_connect(client, userdata, flags, rc):
    print("MQTT conectado, código:", rc)
    client.subscribe(MQTT_TOPIC)
    print("Suscrito al topic:", MQTT_TOPIC)
    socketio.emit('update_status', {"data": "Conectado al broker MQTT"})


def on_message(client, userdata, msg):
    global ecg_filtered, latest_metrics

    try:
        payload = json.loads(msg.payload.decode('utf-8'))
        # print("MQTT payload:", payload)

        raw_samples = (
            payload.get("DatosECG")
            or payload.get("ecg")
            or payload.get("ECG")
            or payload.get("signal")
            or []
        )

        temp1 = (
            payload.get("DatosTemp1")
            or payload.get("temp1")
            or payload.get("temp_1")
        )
        temp2 = (
            payload.get("DatosTemp2")
            or payload.get("temp2")
            or payload.get("temp_2")
        )

        # Actualizar temperaturas
        try:
            if temp1 is not None:
                latest_metrics["temp_1"] = round(float(temp1), 2)
            if temp2 is not None:
                latest_metrics["temp_2"] = round(float(temp2), 2)
        except ValueError:
            pass

        # Filtrar señal
        clean_samples = filter_batch(raw_samples)

        if clean_samples:
            ecg_filtered.extend(clean_samples)

            # último valor para gráfica en tiempo real
            last_sample = float(clean_samples[-1])
            socketio.emit('update_chart', {"value": last_sample})

        # Progreso 0–100 %
        current_len = len(ecg_filtered)
        progress = int(max(0, min(100, (current_len / SAMPLES_WINDOW) * 100)))
        latest_metrics["progress"] = progress

        # Enviamos métricas parciales (temps + progreso)
        socketio.emit('new_decision', latest_metrics)

        # Cuando llegamos a ~60s calculamos HRV
        if current_len >= SAMPLES_WINDOW:
            print("Ventana de ~60s alcanzada, calculando HRV...")
            window = ecg_filtered[-SAMPLES_WINDOW:]
            calculate_hrv_metrics(window)

            # reiniciar buffer
            ecg_filtered = []
            latest_metrics["progress"] = 0
            latest_metrics["status"] = "Iniciando nueva ventana de 60s"
            socketio.emit('new_decision', latest_metrics)

    except Exception as e:
        print("Error en on_message MQTT:", e)


def init_mqtt():
    """Hilo en segundo plano para MQTT."""
    try:
        # paho-mqtt >= 2.0 (muestra un DeprecationWarning pero funciona)
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
    except AttributeError:
        client = mqtt.Client()

    if MQTT_USER and MQTT_PASS:
        client.username_pw_set(MQTT_USER, MQTT_PASS)

    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_forever()

# --------------------------------------------------------------------------
# RUTAS HTTP
# --------------------------------------------------------------------------


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/metrics')
def api_metrics():
    return jsonify(latest_metrics)


@app.route('/api/signal')
def api_signal():
    return jsonify({"clean_samples": ecg_filtered[-2000:]})

# --------------------------------------------------------------------------
# MAIN
# --------------------------------------------------------------------------

if __name__ == '__main__':
    threading.Thread(target=init_mqtt, daemon=True).start()
    print("Servidor web en http://0.0.0.0:5000")
    socketio.run(app, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)
