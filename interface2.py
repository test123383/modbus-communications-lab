import os
import json
import time
import logging
import threading
import struct
import socket
from datetime import datetime
import customtkinter as ctk

# Import Paho MQTT et gestion propre des versions d'API
try:
    import paho.mqtt.client as mqtt
    try:
        from paho.mqtt import CallbackAPIVersion
        MQTT_API_VERSION = CallbackAPIVersion.VERSION1
    except ImportError:
        MQTT_API_VERSION = None
except ImportError:
    raise ImportError("La bibliothèque 'paho-mqtt' est requise. Installez-la avec : pip install paho-mqtt")

# Import PyModbus
try:
    from pymodbus.client import ModbusTcpClient
    from pymodbus.exceptions import ConnectionException, ModbusException, ModbusIOException
except ImportError:
    from pymodbus.client.sync import ModbusTcpClient
    from pymodbus.exceptions import ConnectionException, ModbusException, ModbusIOException

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

REGISTERS_MAP = {
    "DATAKOM": {"V": 20480, "I": 20492, "F": 20528, "E": 20648},
    "XMETER":  {"V": 7001,  "I": 7013,  "F": 7061,  "E": 7099},
    "JANITZA": {"V": 19000, "I": 19012, "F": 19050, "E": 19054}
}

# ==============================================================================
# MQTT GATEWAY PUBLISHER
# ==============================================================================
class MqttGatewayPublisher:
    def __init__(self, broker_ip="127.0.0.1", port=1883, client_id="Edge_Modbus_Gateway"):
        self.broker_ip = broker_ip
        self.port = port
        if MQTT_API_VERSION is not None:
            self.client = mqtt.Client(callback_api_version=MQTT_API_VERSION, client_id=client_id)
        else:
            self.client = mqtt.Client(client_id=client_id)
        self.connected = False

    def connect(self):
        try:
            self.client.connect_async(self.broker_ip, self.port, keepalive=60)
            self.client.loop_start()
            self.connected = True
            logging.info(f"Connecté au broker MQTT {self.broker_ip}:{self.port}")
        except Exception as e:
            logging.error(f"Échec de configuration MQTT : {e}")
            self.connected = False

    def publish_metrics(self, device_name, data_dict):
        if not self.connected: return
        topic = f"gateway/metrics/{device_name}"
        payload = json.dumps(data_dict)
        self.client.publish(topic, payload, qos=1)

    def publish_event(self, device_name, status_message):
        if not self.connected: return
        topic = f"gateway/events/{device_name}"
        payload = json.dumps({
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "device": device_name,
            "event": status_message
        })
        self.client.publish(topic, payload, qos=1)

    def disconnect(self):
        self.client.loop_stop()
        self.client.disconnect()


# ==============================================================================
# MODBUS PROTOCOL WORKER
# ==============================================================================
class ModbusWorker(threading.Thread):
    def __init__(self, device_config, status_callback, data_callback, event_callback):
        super().__init__(daemon=True)
        self.config = device_config
        self.status_callback = status_callback
        self.data_callback = data_callback
        self.event_callback = event_callback  
        self.dev_type = device_config.get("type", "DATAKOM")
        self.running = True

    def _decode_int16_swapped(self, regs, base_addr, target_addr, coef=1.0):
        idx = target_addr - base_addr
        if idx < 0 or idx >= len(regs): return 0.0
        raw = regs[idx]
        swapped = ((raw & 0x00FF) << 8) | ((raw & 0xFF00) >> 8)
        if swapped & 0x8000: swapped -= 0x10000
        return round(swapped * coef, 2)

    def _decode_float32(self, regs, base_addr, target_addr):
        idx = target_addr - base_addr
        if idx < 0 or (idx + 1) >= len(regs): return 0.0
        try:
            packed = struct.pack('>HH', regs[idx], regs[idx+1])
            return round(struct.unpack('>f', packed)[0], 2)
        except Exception: return 0.0

    def run(self):
        maps = REGISTERS_MAP.get(self.dev_type, REGISTERS_MAP["DATAKOM"])
        self.event_callback(self.config['name'], f"Worker démarré (port {self.config['port']})")
        
        consecutive_failures = 0

        while self.running:
            self.status_callback(self.config['name'], "Connecting")
            client = ModbusTcpClient(self.config['ip'], port=self.config['port'], timeout=2.5)
            
            if not client.connect():
                self.status_callback(self.config['name'], "REFUSED")
                self.event_callback(self.config['name'], "Socket refusé (Service Down / Refused)")
                time.sleep(2)
                continue

            while self.running:
                try:
                    uid = self.config['slave_id']
                    kwargs = {'slave': uid} if hasattr(client, 'read_holding_registers') and int(os.environ.get("PYMODBUS_VERSION", 3)) < 3 else {'unit': uid}
                    
                    req_start = time.time()
                    if self.dev_type == "DATAKOM":
                        res1 = client.read_holding_registers(maps["V"], 6, **kwargs)
                        res2 = client.read_holding_registers(maps["F"], 1, **kwargs)
                        
                        if res1.isError(): raise res1
                        if res2.isError(): raise res2
                        
                        v1 = self._decode_int16_swapped(res1.registers, maps["V"], 20480)
                        freq = self._decode_int16_swapped(res2.registers, maps["F"], 20528, 0.01)
                    else:
                        res_v = client.read_holding_registers(maps["V"], 2, **kwargs)
                        res_f = client.read_holding_registers(maps["F"], 2, **kwargs)
                        
                        if res_v.isError(): raise res_v
                        if res_f.isError(): raise res_f
                        
                        v1 = self._decode_float32(res_v.registers, maps["V"], maps["V"])
                        freq = self._decode_float32(res_f.registers, maps["F"], maps["F"])

                    if not self.running: break
                    self.status_callback(self.config['name'], "ONLINE")
                    consecutive_failures = 0
                    
                    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                    metrics = {"time_requested": timestamp, "V1": v1, "Freq": freq}

                    self.data_callback(self.config['name'], metrics)
                    time.sleep(1)
                    
                except (ModbusIOException, ModbusException, Exception) as e:
                    if not self.running: break
                    err_msg = str(e).lower()
                    duration = time.time() - req_start
                    consecutive_failures += 1
                    
                    if duration >= 1.4:
                        self.status_callback(self.config['name'], "TIMEOUT")
                        self.event_callback(self.config['name'], f"Timeout de réponse ({round(duration, 2)}s)")
                    elif any(x in err_msg for x in ["closed", "reset", "pipe", "broken", "empty", "0 bytes"]):
                        if consecutive_failures >= 2:
                            self.status_callback(self.config['name'], "SILENT")
                            self.event_callback(self.config['name'], "Silence de l'équipement")
                        else:
                            self.status_callback(self.config['name'], "DATA LOSS")
                            self.event_callback(self.config['name'], "Perte de trame détectée (Drop)")
                    else:
                        # Remplacement de UNSTABLE par DISCONNECTED
                        self.status_callback(self.config['name'], "DISCONNECTED")
                        self.event_callback(self.config['name'], "Connexion interrompue / Close Post-Conn")
                    
                    time.sleep(1)
                    if consecutive_failures > 5 or "disconnected" in self.config['name'].lower():
                        break
                    
            client.close()
            time.sleep(1)
        
        self.event_callback(self.config['name'], "Worker arrêté")

    def stop(self):
        self.running = False


# ==============================================================================
# GRAPHICAL USER INTERFACE
# ==============================================================================
class GatewayUI(ctk.CTk):
    def __init__(self, devices, start_all_cb, stop_all_cb, connect_cb, disconnect_cb):
        super().__init__()
        self.title("Industrial Multiprotocol Gateway (Modbus TCP ➡️ MQTT)")
        self.geometry("950x750")
        self.configure(fg_color="#1E1E2E")
        self.device_rows = {}
        self.current_scale_level = 0

        self.fonts = {
            "title": ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            "section": ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            "standard": ctk.CTkFont(family="Segoe UI", size=11),
            "console": ctk.CTkFont(family="Consolas", size=11)
        }
        
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.pack(fill="x", padx=15, pady=(12, 5))
        
        self.lbl_main_title = ctk.CTkLabel(self.header_frame, text="📥 AUTOMATED DATA READING GATEWAY", font=self.fonts["title"], text_color="#A6E3A1")
        self.lbl_main_title.pack(side="left")

        self.zoom_panel = ctk.CTkFrame(self.header_frame, fg_color="#313244", height=32, corner_radius=6)
        self.zoom_panel.pack(side="right")
        
        self.btn_zoom_out = ctk.CTkButton(self.zoom_panel, text="A-", width=38, height=26, fg_color="#45475a", hover_color="#585b70", text_color="#CDD6F4", font=self.fonts["section"], command=lambda: self.change_font_scale(-1))
        self.btn_zoom_out.pack(side="left", padx=3, pady=3)

        self.btn_zoom_in = ctk.CTkButton(self.zoom_panel, text="A+", width=38, height=26, fg_color="#45475a", hover_color="#585b70", text_color="#CDD6F4", font=self.fonts["section"], command=lambda: self.change_font_scale(1))
        self.btn_zoom_in.pack(side="left", padx=3, pady=3)
        
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent", height=320)
        self.scroll.pack(fill="both", expand=False, padx=15, pady=5)
        
        for dev in devices:
            f = ctk.CTkFrame(self.scroll, fg_color="#313244", corner_radius=8)
            f.pack(fill="x", pady=6, padx=4)
            
            f.grid_columnconfigure(0, weight=1)
            f.grid_columnconfigure(1, weight=1)
            
            lbl_text = f"🏭 {dev['name']}   |   📍 {dev['ip']}:{dev['port']}  [ID: {dev['slave_id']}]"
            lbl_info = ctk.CTkLabel(f, text=lbl_text, font=self.fonts["console"], justify="left")
            lbl_info.grid(row=0, column=0, columnspan=2, padx=15, pady=(12, 4), sticky="w")
            
            sep = ctk.CTkFrame(f, height=2, fg_color="#45475a")
            sep.grid(row=1, column=0, columnspan=2, padx=15, pady=4, sticky="ew")
            
            status_container = ctk.CTkFrame(f, fg_color="transparent")
            status_container.grid(row=2, column=0, padx=15, pady=(4, 12), sticky="w")
            
            status_lbl = ctk.CTkLabel(status_container, text="STOPPED", text_color="#BAC2DE", font=self.fonts["section"], anchor="w")
            status_lbl.pack(side="left")
        
            btn_container = ctk.CTkFrame(f, fg_color="transparent")
            btn_container.grid(row=2, column=1, padx=15, pady=(4, 12), sticky="e")
            
            btn_conn = ctk.CTkButton(btn_container, text="Connect", width=110, height=32, fg_color="#45475a", hover_color="#585b70", text_color="#CDD6F4", font=self.fonts["section"], command=lambda n=dev['name']: connect_cb(n))
            btn_conn.pack(side="left", padx=5)

            btn_disc = ctk.CTkButton(btn_container, text="Disconnect", width=115, height=32, fg_color="#313244", border_width=1, border_color="#F38BA8", text_color="#F38BA8", font=self.fonts["section"], state="disabled", command=lambda n=dev['name']: disconnect_cb(n))
            btn_disc.pack(side="left", padx=5)
            
            self.device_rows[dev['name']] = {
                "lbl_info": lbl_info,
                "lbl": status_lbl, 
                "btn_conn": btn_conn, 
                "btn_disc": btn_disc
            }

        self.global_btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.global_btn_frame.pack(fill="x", padx=15, pady=5)

        self.btn_all_conn = ctk.CTkButton(self.global_btn_frame, text="CONNECT ALL", fg_color="#A6E3A1", text_color="#11111B", font=self.fonts["section"], height=38, command=start_all_cb)
        self.btn_all_conn.pack(side="left", expand=True, fill="x", padx=5)
        
        self.btn_all_disc = ctk.CTkButton(self.global_btn_frame, text="DISCONNECT ALL", fg_color="#F38BA8", text_color="#11111B", font=self.fonts["section"], height=38, command=stop_all_cb)
        self.btn_all_disc.pack(side="right", expand=True, fill="x", padx=5)

        self.lbl_console_title = ctk.CTkLabel(self, text="📊 LOCAL DATA STREAM & TRANSMITTED EVENTS (MQTT ACTIVE)", font=self.fonts["section"], text_color="#89B4FA")
        self.lbl_console_title.pack(anchor="w", padx=15, pady=(10, 2))
        
        self.console_output = ctk.CTkTextbox(self, font=self.fonts["console"], fg_color="#11111B", text_color="#CDD6F4", border_color="#313244", border_width=1)
        self.console_output.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        self.console_output.configure(state="disabled")

    def change_font_scale(self, delta):
        if not (-2 <= self.current_scale_level + delta <= 10):
            return
        self.current_scale_level += delta
        for font_obj in self.fonts.values():
            font_obj.configure(size=font_obj.cget("size") + delta)
        extra_w = self.current_scale_level * 10
        for row in self.device_rows.values():
            row["btn_conn"].configure(width=max(105, 110 + extra_w))
            row["btn_disc"].configure(width=max(110, 115 + extra_w))

    def update_status(self, name, status):
        self.after(0, lambda: self._apply_status(name, status))

    def _apply_status(self, name, status):
        if name in self.device_rows:
            lbl = self.device_rows[name]["lbl"]
            btn_conn = self.device_rows[name]["btn_conn"]
            btn_disc = self.device_rows[name]["btn_disc"]
            lbl.configure(text=status.upper())
            
            if status == "ONLINE":
                lbl.configure(text_color="#A6E3A1")
                btn_conn.configure(text="Connected", fg_color="#29423e", state="disabled", text_color="#A6E3A1")
                btn_disc.configure(state="normal", fg_color="#F38BA8", text_color="#11111B")
            elif status == "Connecting":
                lbl.configure(text_color="#FAB387")  
                btn_conn.configure(text="Connected", fg_color="#29423e", state="disabled", text_color="#FAB387")
                btn_disc.configure(state="normal", fg_color="#F38BA8", text_color="#11111B")
            elif status in ["TIMEOUT", "DATA LOSS", "SILENT", "DISCONNECTED", "REFUSED"]:
                lbl.configure(text_color="#F38BA8")  
                btn_conn.configure(text="Connected", fg_color="#29423e", state="disabled", text_color="#F38BA8")
                btn_disc.configure(state="normal", fg_color="#F38BA8", text_color="#11111B")
            else: 
                lbl.configure(text="OFFLINE", text_color="#BAC2DE")
                btn_conn.configure(text="Connect", fg_color="#45475a", state="normal", text_color="#CDD6F4")
                btn_disc.configure(state="disabled", fg_color="#313244", text_color="#F38BA8")

    def display_data_log(self, name, metrics):
        self.after(0, lambda: self._write_to_console(f"⏱️ [{metrics['time_requested']}] 🟢 {name} ➡️  V1: {metrics['V1']} V  |  Freq: {metrics['Freq']} Hz\n"))

    def display_event_log(self, name, message):
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.after(0, lambda: self._write_to_console(f"ℹ️ [{timestamp}] {name} ── {message}\n"))

    def _write_to_console(self, complete_line):
        self.console_output.configure(state="normal")
        self.console_output.insert("end", complete_line)
        self.console_output.see("end")
        if int(float(self.console_output.index('end-1c'))) > 500:
            self.console_output.delete("1.0", "2.0")
        self.console_output.configure(state="disabled")


# ==============================================================================
# COORDINATOR
# ==============================================================================
class Coordinator:
    def __init__(self):
        self.devices = []
        self.workers = {}
        self.load_devices_from_json()
        self.mqtt_publisher = MqttGatewayPublisher(broker_ip="127.0.0.1", port=1883)
        self.mqtt_publisher.connect()
        self.ui = GatewayUI(self.devices, self.start_all, self.stop_all, self.connect_device, self.disconnect_device)

    def load_devices_from_json(self):
        cfg_path = "config.json"
        if os.path.exists(cfg_path):
            try:
                with open(cfg_path, "r", encoding="utf-8") as f:
                    self.devices = json.load(f).get("devices", [])
            except Exception as e:
                print(f"Erreur JSON : {e}")
        
        if not self.devices:
            self.devices = [
                {"name": "DATAKOM_LINE_A", "type": "DATAKOM", "ip": "127.0.0.1", "port": 502, "slave_id": 1}
            ]

    def start_all(self):
        for d in self.devices: 
            self._start(d)
    
    def stop_all(self):
        for name in list(self.workers.keys()):
            self.disconnect_device(name)
    
    def _start(self, d):
        if d["name"] not in self.workers:
            w = ModbusWorker(
                d, 
                self.ui.update_status, 
                lambda n, m: self.on_data_received(n, m),
                lambda n, msg: self.on_event_received(n, msg)
            )
            self.workers[d["name"]] = w
            w.start()
    
    def connect_device(self, name):
        d = next((x for x in self.devices if x["name"] == name), None)
        if d: self._start(d)
    
    def disconnect_device(self, name):
        if name in self.workers:
            self.workers[name].stop()
            del self.workers[name]
            self.ui.update_status(name, "Offline")
            self.on_event_received(name, "Bouton stop cliqué")
    
    def on_data_received(self, device_name, metrics):
        if device_name in self.workers:
            self.ui.display_data_log(device_name, metrics)
            self.mqtt_publisher.publish_metrics(device_name, metrics)
    
    def on_event_received(self, device_name, event_message):
        self.ui.display_event_log(device_name, event_message)
        self.mqtt_publisher.publish_event(device_name, event_message)
    
    
if __name__ == "__main__":
    coordinator = Coordinator()
    try:
        coordinator.ui.mainloop()
    finally:
        print("[Gateway] Fermeture, déconnexion MQTT...")
        coordinator.mqtt_publisher.disconnect()