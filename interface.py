import os
import json
import time
import threading
import struct
import socket
import random
import customtkinter as ctk
from tkinter import filedialog

# --- INDUSTRIAL REGISTER ENCODING ---
def swap_bytes(val):
    return ((val & 0x00FF) << 8) | ((val & 0xFF00) >> 8)

def float32_to_reg_bytes(value):
    try:
        packed = struct.pack('>f', value)
        w1, w2 = struct.unpack('>HH', packed)
        return [w1, w2]
    except Exception:
        return [0x0000, 0x0000]

# --- POP-UP NOTIFICATION / WARNING ---
class CTkWarningWindow(ctk.CTkToplevel):
    def __init__(self, master, title, message, icon="⚠️", btn_color="#FAB387"):
        super().__init__(master)
        self.title(title)
        self.geometry("450x220")
        self.configure(fg_color="#1E1E2E")
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self.lift()
        
        self.transient(master)
        self.grab_set()
        
        self.update_idletasks()
        x = master.winfo_x() + (master.winfo_width() // 2) - (450 // 2)
        y = master.winfo_y() + (master.winfo_height() // 2) - (220 // 2)
        self.geometry(f"+{x}+{y}")

        lbl_icon = ctk.CTkLabel(self, text=icon, font=("Segoe UI", 45))
        lbl_icon.pack(pady=(15, 5))

        lbl_msg = ctk.CTkLabel(self, text=message, font=("Segoe UI", 12, "bold"), text_color=btn_color, justify="center")
        lbl_msg.pack(padx=20, pady=10)

        btn_ok = ctk.CTkButton(self, text="OK", fg_color=btn_color, hover_color="#F38BA8", text_color="#11111B", font=("Segoe UI", 12, "bold"), width=120, command=self.destroy)
        btn_ok.pack(pady=(10, 15))


# --- MULTI-THREADED SIMULATOR CORE ENGINE ---
class SimServer(threading.Thread):
    def __init__(self, config, state_callback, light_callback):
        super().__init__(daemon=True)
        self.config = config
        self.state_callback = state_callback
        self.light_callback = light_callback
        self.running = True
        self.dev_type = config.get("type", "DATAKOM")
        self.socket_server = None
        
        self.fault_latency = False
        self.latency_value = 400.0
        self.fault_timeout = False
        self.timeout_value = 1500.0
        self.fault_drop = False
        self.fault_silence = False
        self.fault_close_instant = False
        self.fault_refuse_conn = False
        self.fault_micro_cuts = False
        
        self.request_counter = 0
        self.micro_cuts_online = True

    def trigger_activity_light(self, color_code):
        self.light_callback(self.config["name"], color_code)

    def update_faults(self, latency, latency_val, timeout, timeout_val, drop, silence, close_instant, refuse_conn, micro_cuts):
        self.fault_latency = latency
        self.latency_value = latency_val
        self.fault_timeout = timeout
        self.timeout_value = timeout_val
        self.fault_drop = drop
        self.fault_silence = silence
        self.fault_close_instant = close_instant
        self.fault_refuse_conn = refuse_conn
        self.fault_micro_cuts = micro_cuts

        if not any([latency, timeout, drop, silence, close_instant, refuse_conn, micro_cuts]):
            self.state_callback(self.config["name"], "ONLINE")

    def run(self):
        self.socket_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.socket_server.bind((self.config["ip"], self.config["port"]))
            self.socket_server.listen(10)
            self.state_callback(self.config["name"], "ONLINE")
        except Exception:
            self.state_callback(self.config["name"], "PORT_ERROR")
            self.running = False
            return

        def micro_cuts_loop():
            last_toggle = time.time()
            while self.running:
                if self.fault_micro_cuts:
                    if time.time() - last_toggle >= 3.0:
                        self.micro_cuts_online = not self.micro_cuts_online
                        last_toggle = time.time()
                        status = "ONLINE" if self.micro_cuts_online else "DISCONNECTED"
                        self.state_callback(self.config["name"], status)
                else:
                    if not self.micro_cuts_online:
                        self.micro_cuts_online = True
                        self.state_callback(self.config["name"], "ONLINE")
                time.sleep(0.2)

        threading.Thread(target=micro_cuts_loop, daemon=True).start()

        while self.running:
            self.socket_server.settimeout(0.5)
            try:
                client_sock, addr = self.socket_server.accept()
            except socket.timeout:
                continue
            except Exception:
                break

            if self.fault_refuse_conn:
                self.state_callback(self.config["name"], "REFUSED")
                client_sock.close()
                continue

            def handle_client(sock):
                sock.settimeout(2.0)
                while self.running:
                    if self.fault_refuse_conn:
                        break
                    if self.fault_micro_cuts and not self.micro_cuts_online:
                        time.sleep(0.1)
                        continue
                    try:
                        req = sock.recv(1024)
                        if not req or len(req) < 12:
                            break

                        self.request_counter += 1

                        if self.fault_silence:
                            self.state_callback(self.config["name"], "SILENT")
                            self.trigger_activity_light("#313244")
                            return

                        if self.fault_drop and (self.request_counter % 3 == 0):
                            self.state_callback(self.config["name"], "DATA LOSS")
                            self.trigger_activity_light("#FAB387")
                            return

                        trans_id = req[0:2]
                        proto_id = req[2:4]
                        unit_id = req[6]
                        func_code = req[7]
                        reg_addr = struct.unpack(">H", req[8:10])[0]
                        reg_count = struct.unpack(">H", req[10:12])[0]

                        v1_val = 230.0 + random.uniform(-1.2, 1.2)
                        f_val = 50.0 + random.uniform(-0.04, 0.04)

                        registers_data = []
                        if self.dev_type == "DATAKOM":
                            if reg_addr == 20480:
                                registers_data = [swap_bytes(int(v1_val)), 0, swap_bytes(int(v1_val)), 0, swap_bytes(int(v1_val)), 0]
                            elif reg_addr == 20528:
                                registers_data = [swap_bytes(int(f_val * 100))]
                            else:
                                registers_data = [0] * reg_count
                        else:
                            if reg_addr in [7001, 19000]:
                                registers_data = float32_to_reg_bytes(v1_val) + float32_to_reg_bytes(v1_val)
                            elif reg_addr in [7061, 19050]:
                                registers_data = float32_to_reg_bytes(f_val)
                            else:
                                registers_data = [0] * reg_count

                        registers_data = registers_data[:reg_count]
                        if len(registers_data) < reg_count:
                            registers_data += [0] * (reg_count - len(registers_data))

                        byte_count = len(registers_data) * 2
                        pdu_res = struct.pack("=BB", func_code, byte_count)
                        for reg in registers_data:
                            pdu_res += struct.pack(">H", reg)

                        mbap_len = len(pdu_res) + 1
                        mbap_res = trans_id + proto_id + struct.pack(">H", mbap_len) + struct.pack("B", unit_id)
                        
                        full_response = mbap_res + pdu_res

                        if self.fault_latency or self.fault_timeout:
                            delay = (self.timeout_value if self.fault_timeout else self.latency_value) / 1000.0
                            self.trigger_activity_light("#89B4FA")
                            time.sleep(delay)
                            self.trigger_activity_light("#313244")
                            if self.fault_timeout:
                                return

                        sock.sendall(full_response)

                        if self.fault_close_instant:
                            break

                    except Exception:
                        break
                sock.close()

            threading.Thread(target=handle_client, args=(client_sock,), daemon=True).start()

    def stop(self):
        self.running = False
        if self.socket_server:
            try: self.socket_server.close()
            except Exception: pass
        self.state_callback(self.config["name"], "STOPPED")


# --- DYNAMIC DEVICE CARD COMPONENT ---
class DeviceCard(ctk.CTkFrame):
    def __init__(self, master, app_instance, config, on_start_callback, on_stop_callback):
        super().__init__(master, fg_color="#1E1E2E", corner_radius=10, border_width=1, border_color="#313244")
        self.config = config
        self.app = app_instance
        self.on_start = on_start_callback
        self.on_stop = on_stop_callback
        self.is_active = False
        self.dev_type = config.get("type", "DATAKOM")
        self.current_status = "STOPPED"
        
        self.grid_columnconfigure(1, weight=1)

        self.lbl_bus_light = ctk.CTkLabel(self, text="⬤", font=self.app.fonts["title"], text_color="#313244", width=30)
        self.lbl_bus_light.grid(row=0, column=0, padx=(12, 0), pady=8, sticky="w")

        self.lbl_info = ctk.CTkLabel(self, text=f"🏭 {config['name']} [{self.dev_type}]  📍 {config['ip']}:{config['port']} (ID: {config.get('slave_id', 1)})", font=self.app.fonts["section"], text_color="#CBA6F7", justify="left")
        self.lbl_info.grid(row=0, column=1, padx=10, pady=8, sticky="w")

        self.frame_actions = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_actions.grid(row=0, column=2, padx=12, pady=8, sticky="e")

        self.lbl_status = ctk.CTkLabel(self.frame_actions, text="● STOPPED", font=self.app.fonts["section"], text_color="#F38BA8")
        self.lbl_status.pack(side="left", padx=10)

        self.btn_action = ctk.CTkButton(self.frame_actions, text="RUN", fg_color="#A6E3A1", hover_color="#89DCEB", text_color="#11111B", width=75, font=self.app.fonts["section"], command=self._toggle_state)
        self.btn_action.pack(side="right")

        self.frame_faults = ctk.CTkFrame(self, fg_color="#11111B", corner_radius=6, border_width=1, border_color="#313244")
        self.frame_faults.grid(row=1, column=0, columnspan=3, padx=12, pady=(0, 12), sticky="ew")
        
        self.frame_faults.grid_columnconfigure(0, weight=1)
        self.frame_faults.grid_columnconfigure(1, weight=1)
        self.frame_faults.grid_columnconfigure(2, weight=1)

        COLOR_PERF = "#89B4FA"
        COLOR_QUALITY = "#FAB387"
        COLOR_CRITIC = "#F38BA8"

        self.box_perf = ctk.CTkFrame(self.frame_faults, fg_color="transparent")
        self.box_perf.grid(row=0, column=0, padx=10, pady=6, sticky="nw")

        self.var_latency = ctk.BooleanVar(value=False)
        self.chk_latency = ctk.CTkCheckBox(self.box_perf, text="⏳ Latency (ms)", variable=self.var_latency, text_color=COLOR_PERF, font=self.app.fonts["small_bold"], checkbox_width=14, checkbox_height=14, command=self._on_fault_changed)
        self.chk_latency.pack(anchor="w", pady=2)
        
        self.txt_latency_val = ctk.CTkEntry(self.box_perf, width=45, height=20, font=self.app.fonts["small"], fg_color="#313244", border_color="#45475A", text_color=COLOR_PERF)
        self.txt_latency_val.insert(0, "400")
        self.txt_latency_val.pack(anchor="w", padx=(20, 0), pady=2)
        self.txt_latency_val.bind("<KeyRelease>", lambda e: self._on_fault_changed())

        self.var_timeout = ctk.BooleanVar(value=False)
        self.chk_timeout = ctk.CTkCheckBox(self.box_perf, text="⏱️ Timeout (ms)", variable=self.var_timeout, text_color=COLOR_PERF, font=self.app.fonts["small_bold"], checkbox_width=14, checkbox_height=14, command=self._on_fault_changed)
        self.chk_timeout.pack(anchor="w", pady=(6, 2))

        self.txt_timeout_val = ctk.CTkEntry(self.box_perf, width=45, height=20, font=self.app.fonts["small"], fg_color="#313244", border_color="#45475A", text_color=COLOR_PERF)
        self.txt_timeout_val.insert(0, "1500")
        self.txt_timeout_val.pack(anchor="w", padx=(20, 0), pady=2)
        self.txt_timeout_val.bind("<KeyRelease>", lambda e: self._on_fault_changed())

        self.box_quality = ctk.CTkFrame(self.frame_faults, fg_color="transparent")
        self.box_quality.grid(row=0, column=1, padx=10, pady=6, sticky="nw")

        self.var_drop = ctk.BooleanVar(value=False)
        self.chk_drop = ctk.CTkCheckBox(self.box_quality, text="📉 Packet Loss", variable=self.var_drop, text_color=COLOR_QUALITY, font=self.app.fonts["small_bold"], checkbox_width=14, checkbox_height=14, command=self._on_fault_changed)
        self.chk_drop.pack(anchor="w", pady=2)

        self.box_critic = ctk.CTkFrame(self.frame_faults, fg_color="transparent")
        self.box_critic.grid(row=0, column=2, padx=10, pady=6, sticky="nw")

        self.var_silence = ctk.BooleanVar(value=False)
        self.chk_silence = ctk.CTkCheckBox(self.box_critic, text="🤫 Device Silence", variable=self.var_silence, text_color=COLOR_CRITIC, font=self.app.fonts["small_bold"], checkbox_width=14, checkbox_height=14, command=self._on_fault_changed)
        self.chk_silence.pack(anchor="w", pady=2)

        self.var_close_instant = ctk.BooleanVar(value=False)
        self.chk_close_instant = ctk.CTkCheckBox(self.box_critic, text="❌ Close Post-Conn", variable=self.var_close_instant, text_color=COLOR_CRITIC, font=self.app.fonts["small_bold"], checkbox_width=14, checkbox_height=14, command=self._on_fault_changed)
        self.chk_close_instant.pack(anchor="w", pady=2)

        self.var_refuse_conn = ctk.BooleanVar(value=False)
        self.chk_refuse_conn = ctk.CTkCheckBox(self.box_critic, text="🚫 Service Unavailable", variable=self.var_refuse_conn, text_color=COLOR_CRITIC, font=self.app.fonts["small_bold"], checkbox_width=14, checkbox_height=14, command=self._on_fault_changed)
        self.chk_refuse_conn.pack(anchor="w", pady=2)

        self.var_micro_cuts = ctk.BooleanVar(value=False)
        self.chk_micro_cuts = ctk.CTkCheckBox(self.box_critic, text="⚡ Micro-Cuts", variable=self.var_micro_cuts, text_color=COLOR_CRITIC, font=self.app.fonts["small_bold"], checkbox_width=14, checkbox_height=14, command=self._on_fault_changed)
        self.chk_micro_cuts.pack(anchor="w", pady=2)

    def update_card_fonts(self):
        self.lbl_bus_light.configure(font=self.app.fonts["title"])
        self.lbl_info.configure(font=self.app.fonts["section"])
        self.lbl_status.configure(font=self.app.fonts["section"])
        self.btn_action.configure(font=self.app.fonts["section"])
        self.chk_latency.configure(font=self.app.fonts["small_bold"])
        self.txt_latency_val.configure(font=self.app.fonts["small"])
        self.chk_timeout.configure(font=self.app.fonts["small_bold"])
        self.txt_timeout_val.configure(font=self.app.fonts["small"])
        self.chk_drop.configure(font=self.app.fonts["small_bold"])
        self.chk_silence.configure(font=self.app.fonts["small_bold"])
        self.chk_close_instant.configure(font=self.app.fonts["small_bold"])
        self.chk_refuse_conn.configure(font=self.app.fonts["small_bold"])
        self.chk_micro_cuts.configure(font=self.app.fonts["small_bold"])

    def flash_light(self, color_code):
        self.lbl_bus_light.configure(text_color=color_code)
        if color_code not in ["#89B4FA", "#313244"]:
            self.after(120, lambda: self.lbl_bus_light.configure(text_color="#313244"))

    def _on_fault_changed(self):
        if self.config["name"] in self.app.active_servers:
            try: lat_val = float(self.txt_latency_val.get())
            except ValueError: lat_val = 400.0
            try: out_val = float(self.txt_timeout_val.get())
            except ValueError: out_val = 1500.0
            
            self.app.active_servers[self.config["name"]].update_faults(
                self.var_latency.get(), lat_val, self.var_timeout.get(), out_val, self.var_drop.get(),
                self.var_silence.get(), self.var_close_instant.get(), self.var_refuse_conn.get(), self.var_micro_cuts.get()
            )

    def _toggle_state(self):
        if not self.is_active: self.force_start()
        else: self.force_stop()

    def force_start(self):
        if not self.is_active:
            self.is_active = True
            self.btn_action.configure(text="STOP", fg_color="#F38BA8", hover_color="#E05F84")
            self.on_start(self.config)
            self._on_fault_changed()

    def force_stop(self):
        if self.is_active:
            self.is_active = False
            self.btn_action.configure(text="RUN", fg_color="#A6E3A1", hover_color="#89DCEB")
            self.lbl_bus_light.configure(text_color="#313244")
            self.on_stop(self.config["name"])
            for v in [self.var_latency, self.var_timeout, self.var_drop, self.var_silence, self.var_close_instant, self.var_refuse_conn, self.var_micro_cuts]:
                v.set(False)

    def update_status_label(self, status):
        self.current_status = status
        if status == "ONLINE": self.lbl_status.configure(text="● RUNNING", text_color="#A6E3A1")
        elif status == "REFUSED": self.lbl_status.configure(text="🚫 REFUSED", text_color="#FAB387")
        elif status == "DISCONNECTED": self.lbl_status.configure(text="● DISCONNECTED", text_color="#F38BA8")
        elif status == "SILENT": self.lbl_status.configure(text="🤫 SILENT", text_color="#FAB387")
        elif status == "DATA LOSS": self.lbl_status.configure(text="📉 DATA LOSS", text_color="#FAB387")
        elif status == "PORT_ERROR":
            self.lbl_status.configure(text="⚠️ PORT BUSY", text_color="#FAB387")
            self.is_active = False
            self.btn_action.configure(text="RUN", fg_color="#A6E3A1", hover_color="#89DCEB")
            self.app.trigger_popup_warning(self.config)
        else: self.lbl_status.configure(text="● STOPPED", text_color="#F38BA8")


# --- DESIGNED GENERATOR ROW COMPONENT WITH TRASH ICON ONLY ---
class GeneratorRow(ctk.CTkFrame):
    def __init__(self, master, app_instance, row_index):
        super().__init__(master, fg_color="transparent")
        self.app = app_instance
        self.row_index = row_index

        self.ent_name = ctk.CTkEntry(self, placeholder_text="Name", width=120, font=self.app.fonts["standard"])
        self.ent_name.insert(0, f"METER_BLOCK_{row_index}")
        self.ent_name.pack(side="left", padx=3)

        self.cmb_manuf = ctk.CTkOptionMenu(self, values=["DATAKOM", "XMETER", "JANITZA", "default"], width=105, font=self.app.fonts["standard"], fg_color="#313244", button_color="#45475A")
        self.cmb_manuf.pack(side="left", padx=3)

        self.ent_host = ctk.CTkEntry(self, placeholder_text="Host", width=100, font=self.app.fonts["standard"])
        self.ent_host.insert(0, "localhost")
        self.ent_host.pack(side="left", padx=3)

        self.ent_port = ctk.CTkEntry(self, placeholder_text="Port", width=55, font=self.app.fonts["standard"])
        self.ent_port.insert(0, str(502 + row_index - 1))
        self.ent_port.pack(side="left", padx=3)

        self.ent_count = ctk.CTkEntry(self, placeholder_text="Count", width=45, font=self.app.fonts["standard"], border_color="#FAB387")
        self.ent_count.insert(0, "3")
        self.ent_count.pack(side="left", padx=3)

        # Trash Button replacing the old "-" button
        self.btn_remove = ctk.CTkButton(
            self, text="🗑️", width=35, height=28, 
            fg_color="#F38BA8", hover_color="#E05F84", text_color="#11111B", 
            font=self.app.fonts["title"], command=lambda: self.app.remove_generator_row(self)
        )
        self.btn_remove.pack(side="left", padx=5)


# --- MAIN APP WITH GLOBALIZED BOTTOM "+" BUTTON ENGINE ---
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Modbus Communications Lab V5")
        self.geometry("1600x900")
        self.configure(fg_color="#11111B")
        self.all_devices_running = False
        self.cards = {}
        self.active_servers = {}
        self.generator_rows = []
        self.row_counter = 1
        self.current_sort_criteria = "SORT: Alphabetical"
        self.selected_export_path = "meters.json"

        self.fonts = {
            "title": ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            "section": ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            "standard": ctk.CTkFont(family="Segoe UI", size=11),
            "small_bold": ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            "small": ctk.CTkFont(family="Segoe UI", size=10)
        }

        # --- HEADER ROW ---
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.pack(fill="x", padx=25, pady=(10, 5))
        
        self.lbl_main_title = ctk.CTkLabel(self.header_frame, text="🛡️ MODBUS PROTOCOL & NETWORK ROBUSTNESS LAB", font=self.fonts["title"], text_color="#89B4FA")
        self.lbl_main_title.pack(side="left")

        self.zoom_panel = ctk.CTkFrame(self.header_frame, fg_color="#1E1E2E", height=32, corner_radius=6)
        self.zoom_panel.pack(side="right", pady=5)
        
        self.btn_zoom_out = ctk.CTkButton(self.zoom_panel, text="A-", width=35, height=26, fg_color="#313244", hover_color="#45475A", text_color="#CDD6F4", font=self.fonts["section"], command=lambda: self.change_font_scale(-1))
        self.btn_zoom_out.pack(side="left", padx=3, pady=3)

        self.btn_zoom_in = ctk.CTkButton(self.zoom_panel, text="A+", width=35, height=26, fg_color="#313244", hover_color="#45475A", text_color="#CDD6F4", font=self.fonts["section"], command=lambda: self.change_font_scale(1))
        self.btn_zoom_in.pack(side="left", padx=3, pady=3)

        # ================= SINGLE PLUS ICON CONTAINER PANEL =================
        self.config_engine_panel = ctk.CTkFrame(self, fg_color="#1E1E2E", corner_radius=8, border_width=1, border_color="#A6E3A1")
        self.config_engine_panel.pack(fill="x", padx=25, pady=5)

        lbl_engine_title = ctk.CTkLabel(self.config_engine_panel, text="⚙️ MULTI-BLOCK METER GENERATOR (Configure independent rules across rows)", font=self.fonts["section"], text_color="#A6E3A1")
        lbl_engine_title.pack(anchor="w", padx=15, pady=(8, 5))

        # Rows Box
        self.rows_scroll_container = ctk.CTkFrame(self.config_engine_panel, fg_color="transparent")
        self.rows_scroll_container.pack(fill="x", padx=15, pady=2)

        # Centralized Single "+" Button Container Layout Row (Anchored directly under the final line)
        self.plus_btn_container = ctk.CTkFrame(self.config_engine_panel, fg_color="transparent")
        self.plus_btn_container.pack(fill="x", padx=15, pady=(2, 6))

        self.btn_global_add = ctk.CTkButton(
            self.plus_btn_container, text="+", width=40, height=28, 
            fg_color="#A6E3A1", hover_color="#89DCEB", text_color="#11111B", 
            font=self.fonts["title"], command=self.add_generator_row
        )
        self.btn_global_add.pack(side="left", padx=3)

        # Bottom Actions Sub-Bar
        self.actions_sub_bar = ctk.CTkFrame(self.config_engine_panel, fg_color="transparent")
        self.actions_sub_bar.pack(fill="x", padx=15, pady=(5, 10))

        self.btn_browse_path = ctk.CTkButton(self.actions_sub_bar, text="📁 Browse File...", fg_color="#89B4FA", hover_color="#B4BEFE", text_color="#11111B", font=self.fonts["section"], width=130, command=self.browse_save_location)
        self.btn_browse_path.pack(side="left", padx=5)

        self.btn_bulk_generate = ctk.CTkButton(self.actions_sub_bar, text="⚡ Generate Bulk Configuration", fg_color="#A6E3A1", hover_color="#89DCEB", text_color="#11111B", font=self.fonts["section"], command=self.generate_bulk_meters_file)
        self.btn_bulk_generate.pack(side="right", padx=5)

        # Initialization
        self.add_generator_row()

        # --- FILTERS & SORT PANEL ---
        self.filter_panel = ctk.CTkFrame(self, fg_color="#1E1E2E", corner_radius=8, border_width=1, border_color="#313244")
        self.filter_panel.pack(fill="x", padx=25, pady=5)

        self.lbl_search_text = ctk.CTkLabel(self.filter_panel, text="🔍 Name :", font=self.fonts["section"], text_color="#89B4FA")
        self.lbl_search_text.pack(side="left", padx=(15, 5), pady=12)
        
        self.search_bar = ctk.CTkEntry(self.filter_panel, placeholder_text="Filter by name...", width=220, font=self.fonts["standard"])
        self.search_bar.pack(side="left", padx=5, pady=12)
        self.search_bar.bind("<KeyRelease>", lambda e: self.apply_filters())

        self.lbl_sep = ctk.CTkLabel(self.filter_panel, text=" | ", font=self.fonts["title"], text_color="#45475A")
        self.lbl_sep.pack(side="left", padx=15)

        self.lbl_tag = ctk.CTkLabel(self.filter_panel, text="🔀 Sort simulators by :", font=self.fonts["section"], text_color="#CBA6F7")
        self.lbl_tag.pack(side="left", padx=(2, 8))
        
        self.combo_sort = ctk.CTkOptionMenu(
            self.filter_panel,
            values=["SORT: Alphabetical", "SORT: IP Address", "SORT: Port Number", "SORT: Active Status"],
            font=self.fonts["section"],
            dropdown_font=self.fonts["standard"],
            fg_color="#313244",
            button_color="#45475A",
            button_hover_color="#585B70",
            dropdown_fg_color="#1E1E2E",
            dropdown_hover_color="#313244",
            text_color="#CDD6F4",
            dropdown_text_color="#CDD6F4",
            width=210,
            command=self._on_sort_changed
        )
        self.combo_sort.pack(side="left", padx=5, pady=12)

        self.btn_global_action = ctk.CTkButton(self, text="START ALL VISIBLE SIMULATORS", fg_color="#A6E3A1", hover_color="#89DCEB", text_color="#11111B", font=self.fonts["title"], height=40, command=self.toggle_all_devices)
        self.btn_global_action.pack(fill="x", padx=25, pady=5)

        self.workspace = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.workspace.pack(fill="both", expand=True, padx=15, pady=10)
        
        self.load_configuration_file()

    # --- RESTRUCTURED GLOBAL BOTTOM PLUS CONTROL ALGORITHM ---
    def add_generator_row(self):
        row = GeneratorRow(self.rows_scroll_container, self, self.row_counter)
        row.pack(fill="x", pady=3)
        self.generator_rows.append(row)
        self.row_counter += 1
        
        # Adjust trash visibility (Hide trash icon if there's only 1 row)
        if len(self.generator_rows) == 1:
            self.generator_rows[0].btn_remove.pack_forget()
        else:
            for r in self.generator_rows:
                r.btn_remove.pack(side="left", padx=5)

    def remove_generator_row(self, row_instance):
        if len(self.generator_rows) > 1:
            row_instance.pack_forget()
            self.generator_rows.remove(row_instance)
            row_instance.destroy()
            
            if len(self.generator_rows) == 1:
                self.generator_rows[0].btn_remove.pack_forget()

    def _on_sort_changed(self, choice):
        self.current_sort_criteria = choice
        self.apply_filters()

    def change_font_scale(self, delta):
        for font_obj in self.fonts.values():
            current_size = font_obj.cget("size")
            new_size = current_size + delta
            if 8 <= new_size <= 24:
                font_obj.configure(size=new_size)
        
        self.lbl_main_title.configure(font=self.fonts["title"])
        self.lbl_search_text.configure(font=self.fonts["section"])
        self.search_bar.configure(font=self.fonts["standard"])
        self.lbl_sep.configure(font=self.fonts["title"])
        self.lbl_tag.configure(font=self.fonts["section"])
        self.combo_sort.configure(font=self.fonts["section"], dropdown_font=self.fonts["standard"])
        self.btn_global_action.configure(font=self.fonts["title"])
        
        for card in self.cards.values():
            card.update_card_fonts()

    def load_configuration_file(self):
        self.cfg_path = "config.json"
        if not os.path.exists(self.cfg_path):
            default_cfg = {"devices": [
                {"name": "DATAKOM_LINE_A", "type": "DATAKOM", "ip": "127.0.0.1", "port": 502, "slave_id": 1},
                {"name": "ENERGYTEAM_X_METER", "type": "XMETER", "ip": "127.0.0.2", "port": 5502, "slave_id": 1}, 
                {"name": "JANITZA_ZONE_1", "type": "JANITZA", "ip": "127.0.0.1", "port": 503, "slave_id": 1}
            ]}
            with open(self.cfg_path, "w", encoding="utf-8") as f: json.dump(default_cfg, f, indent=4)

        with open(self.cfg_path, "r", encoding="utf-8") as f:
            self.all_device_configs = json.load(f).get("devices", [])

        for dev in self.all_device_configs:
            if dev["name"] not in self.cards:
                card = DeviceCard(self.workspace, self, dev, self.start_device, self.stop_device)
                self.cards[dev["name"]] = card

        self.apply_filters()

    def browse_save_location(self):
        file_path = filedialog.asksaveasfilename(
            initialfile="meters.json",
            defaultextension=".json",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")]
        )
        if file_path:
            self.selected_export_path = file_path
            self.btn_browse_path.configure(fg_color="#A6E3A1", text="📁 Path Selected!")

    def generate_bulk_meters_file(self):
        final_consolidated_list = []
        global_unit_id_tracker = 1
        global_datamap_id_tracker = 0

        for idx, row in enumerate(self.generator_rows):
            base_name = row.ent_name.get().strip().upper().replace(" ", "_")
            manufacturer = row.cmb_manuf.get()
            host = row.ent_host.get().strip()
            port_str = row.ent_port.get().strip()
            count_str = row.ent_count.get().strip()

            if not base_name or not count_str or not port_str:
                CTkWarningWindow(self, "Invalid Row Found", f"ERROR: Line #{idx+1} has missing entries! Please fill out all text parameters.")
                return

            try:
                port = int(port_str)
                gen_count = int(count_str)
            except ValueError:
                CTkWarningWindow(self, "Invalid Inputs", f"ERROR: Numerical values required for Port/Count on line #{idx+1}!")
                return

            if gen_count < 1:
                continue

            for i in range(1, gen_count + 1):
                name_incremented = f"{base_name}-{str(i).zfill(3)}"
                serial_incremented = f"{str(global_unit_id_tracker).zfill(10)}"

                meter_object = {
                    "unit_id": global_unit_id_tracker,
                    "name": name_incremented,
                    "serial_number": serial_incremented,
                    "manufacturer": manufacturer.lower() if manufacturer != "default" else "default",
                    "label": "default",
                    "method": "tcp",
                    "host": host if host else "localhost",
                    "port": port,
                    "datamap_id": global_datamap_id_tracker
                }
                
                final_consolidated_list.append(meter_object)
                global_unit_id_tracker += 1
                global_datamap_id_tracker += 1

        if not final_consolidated_list:
            CTkWarningWindow(self, "Empty Dataset", "No objects were built. Make sure count rules are above 0.")
            return

        try:
            with open(self.selected_export_path, "w", encoding="utf-8") as f:
                json.dump(final_consolidated_list, f, indent=4)
            
            filename_only = os.path.basename(self.selected_export_path)
            total_items = len(final_consolidated_list)
            CTkWarningWindow(self, "Multi-Block Export Success", f"Successfully combined & saved {total_items} objects into '{filename_only}'!", icon="✅", btn_color="#A6E3A1")
            
            self.btn_browse_path.configure(fg_color="#89B4FA", text="📁 Browse File...")
            self.selected_export_path = "meters.json"
            
        except Exception as e:
            CTkWarningWindow(self, "Write Error", f"Could not write target file:\n{str(e)}")

    def apply_filters(self):
        search_query = self.search_bar.get().lower().strip()
        for card in self.cards.values():
            card.pack_forget()

        def get_sort_key(item):
            name, card = item
            if self.current_sort_criteria == "SORT: Alphabetical":
                return name.lower()
            elif self.current_sort_criteria == "SORT: IP Address":
                return card.config.get("ip", "0.0.0.0")
            elif self.current_sort_criteria == "SORT: Port Number":
                return int(card.config.get("port", 0))
            elif self.current_sort_criteria == "SORT: Active Status":
                return 0 if card.current_status == "ONLINE" else 1
            return name.lower()

        sorted_cards = sorted(self.cards.items(), key=get_sort_key)
        for name, card in sorted_cards:
            if search_query in name.lower():
                card.pack(fill="x", padx=10, pady=5)

    def trigger_popup_warning(self, dev_config):
        CTkWarningWindow(self, "Network Conflict Detected", f"PORT ERROR DETECTED!\n\nPort {dev_config['port']} is currently in use, please change the port.")

    def toggle_all_devices(self):
        if not self.all_devices_running:
            self.all_devices_running = True
            self.btn_global_action.configure(text="STOP ALL VISIBLE SIMULATORS", fg_color="#F38BA8", hover_color="#E05F84")
            for card in self.cards.values():
                if card.winfo_manager(): 
                    card.force_start()
                    time.sleep(0.05) 
        else:
            self.all_devices_running = False
            self.btn_global_action.configure(text="START ALL VISIBLE SIMULATORS", fg_color="#A6E3A1", hover_color="#89DCEB")
            for card in self.cards.values(): 
                card.force_stop()
            time.sleep(0.4) 

    def start_device(self, dev_config):
        name = dev_config["name"]
        target_ip = dev_config["ip"]
        target_port = dev_config["port"]
        
        for active_name, active_server in self.active_servers.items():
            if active_server.config["port"] == target_port and active_server.config["ip"] == target_ip:
                self.trigger_popup_warning(dev_config)
                if name in self.cards:
                    self.cards[name].update_status_label("PORT_ERROR")
                return

        if name not in self.active_servers:
            server = SimServer(dev_config, self._thread_safe_gui_status, self._thread_safe_gui_light)
            self.active_servers[name] = server
            server.start()

    def stop_device(self, name):
        if name in self.active_servers:
            self.active_servers[name].stop()
            del self.active_servers[name]

    def _thread_safe_gui_status(self, name, status):
        if name in self.cards:
            try: 
                self.after(0, self.cards[name].update_status_label, status)
                if self.current_sort_criteria == "SORT: Active Status":
                    self.after(0, self.apply_filters)
            except Exception: pass

    def _thread_safe_gui_light(self, name, color_code):
        if name in self.cards:
            try: self.after(0, self.cards[name].flash_light, color_code)
            except Exception: pass

if __name__ == "__main__":
    App().mainloop()