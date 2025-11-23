from flask import Flask, Response, render_template, jsonify
from flask_cors import CORS
import threading
import paho.mqtt.client as mqtt
import json
import numpy as np
from flask_socketio import SocketIO
from scipy.signal import iirnotch, butter, filtfilt, find_peaks

app = Flask(__name__)
socketio = SocketIO(app)

MQTT_BROKER = "broker.emqx.io"
MQTT_PORT = 1883
MQTT_TOPIC = "iot2/proyecto/sensor"
MQTT_USER = "administrador"
MQTT_PASS = "JRJGJ05"

FS = 333
SAMPLES_30_SEC = FS * 30
SAMPLES_60_SEC = FS * 60

ecg_filtered = []
calculation_done = False

latest_metrics = {
    "bpm": 0,
    "sdnn": 0,
    "rmssd": 0,
    "pnn50": 0,
    "temp_1": 0,
    "temp_2": 0,
    "status": "Esperando datos...",
    "progress": 0
}

# -----------------------------
# FILTROS
# -----------------------------
b_notch, a_notch = iirnotch(60, 30, FS)
b_lp, a_lp = butter(4, 100 / (FS/2), btype='low')

def filter_batch(samples):
    if len(samples) == 0:
        return []
    x = np.array(samples, dtype=float)
    try:
        x = filtfilt(b_notch, a_notch, x)
        x = filtfilt(b_lp, a_lp, x)
    except:
        pass
    return x.tolist()

# -----------------------------
# CÁLCULO HRV
# -----------------------------
def calculate_hrv_metrics(signal_data):
    global latest_metrics
    data_np = np.array(signal_data)

    distance = int(0.5 * FS)
    height = np.mean(data_np)
    peaks, _ = find_peaks(data_np, distance=distance, height=height)

    if len(peaks) < 2:
        return

    peaks_time_ms = (peaks / FS) * 1000
    rr_intervals = np.diff(peaks_time_ms)

    mean_rr = np.mean(rr_intervals)
    bpm = 60000 / mean_rr
    sdnn = np.std(rr_intervals, ddof=1)
    diff_rr = np.diff(rr_intervals)
    rmssd = np.sqrt(np.mean(diff_rr**2))
    nn50 = np.sum(np.abs(diff_rr) > 50)
    pnn50 = (nn50 / len(diff_rr)) * 100 if len(diff_rr) > 0 else 0

    latest_metrics.update({
        "bpm": round(bpm, 2),
        "sdnn": round(sdnn, 2),
        "rmssd": round(rmssd, 2),
        "pnn50": round(pnn50, 2),
        "status": "Actualizado"
    })

    print("\n" + "="*40)
    print("NUEVOS RESULTADOS CALCULADOS:")
    print(f"-Frecuencia Cardiana: {bpm:.2f}")
    print(f"-SDNN: {sdnn:.2f}")
    print(f"-RMSSD: {rmssd:.2f}")   
    print(f"-PNN50: {pnn50:.2f}")
    print(f"-Temperatura 1: {latest_metrics['temp_1']} °C")
    print(f"-Temperatura 2: {latest_metrics['temp_2']} °C")
    print("="*40 + "\n")


# -----------------------------
# MQTT
# -----------------------------
def on_connect(client, userdata, flags, rc):
    print("MQTT conectado")
    client.subscribe(MQTT_TOPIC)

def on_message(client, userdata, msg):
    global ecg_filtered, calculation_done

    try:
        payload = json.loads(msg.payload.decode())

        raw_samples = payload.get("DatosECG", [])
        latest_metrics["temp_1"] = payload.get("DatosTemp1", 0)
        latest_metrics["temp_2"] = payload.get("DatosTemp2", 0)

        clean_samples = filter_batch(raw_samples)
        ecg_filtered.extend(clean_samples)

        current_len = len(ecg_filtered)
        latest_metrics["progress"] = int((current_len / SAMPLES_30_SEC) * 100)

        if current_len >= SAMPLES_30_SEC and not calculation_done:
            threading.Thread(target=calculate_hrv_metrics, args=(ecg_filtered[:SAMPLES_30_SEC],)).start()
            calculation_done = True

        if current_len >= SAMPLES_60_SEC:
            ecg_filtered = []
            calculation_done = False
            latest_metrics["status"] = "Reiniciando ciclo..."

    except Exception as e:
        print("Error MQTT:", e)

def init_mqtt():
    client = mqtt.Client()
    client.username_pw_set(MQTT_USER, MQTT_PASS)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_forever()

threading.Thread(target=init_mqtt, daemon=True).start()

# -------------------------------------
# RUTA PRINCIPAL
# -------------------------------------
@app.route('/')
def index():
    return render_template('index.html')


# -------------------------------------
# RUTAS API QUE NECESITA EL FRONTEND
# -------------------------------------

@app.route('/api/metrics')
def api_metrics():
    return jsonify(latest_metrics)

@app.route('/api/signal')
def api_signal():
    return jsonify({"clean_samples": ecg_filtered[-2000:]})


# -------------------------------------
# MAIN
# -------------------------------------
if __name__ == '__main__':
    print("Servidor web iniciado en http://0.0.0.0:5000")
    socketio.run(app, host='0.0.0.0', port=5000)
