<img width="1160" height="742" alt="image2" src="https://github.com/user-attachments/assets/2ff42743-3c47-4e58-993d-7616ed05e216" />
<img width="1881" height="1102" alt="image1" src="https://github.com/user-attachments/assets/a5a0cf2a-0a09-4925-9df8-5dcb443ff806" />
# ⚡ Industrial Multiprotocol Gateway & Modbus Lab

> A comprehensive Python suite for industrial Modbus TCP simulation, network fault injection, dynamic configuration generation, and automated Modbus-to-MQTT gateway data publishing.



---

## 📸 Applications Showcase

### 1. Modbus Protocol & Network Robustness Lab
![Modbus Simulator Interface](assets/simulator-gui.png)

*Features multi-block rule configuration, dynamic simulator controls, and real-time network anomaly injection (Latency, Timeout, Packet Loss, Micro-Cuts, and Device Silence).*

---

### 2. Automated Data Reading Gateway (Modbus TCP ➔ MQTT)
![Automated Gateway Interface](assets/gateway-gui.png)

*Provides centralized connectivity management for Modbus meters, real-time data ingestion, and direct streaming over local MQTT topics.*

---

## 📁 Repository Structure

```text
.
├── README.md                          # Main project documentation
├── assets/                            # Application screenshots
│   ├── simulator-gui.png              # Screenshot of the Modbus Lab GUI
│   └── gateway-gui.png                # Screenshot of the Gateway GUI
│
├── [Projet 1] - Modbus Lab GUI/       # Modbus Simulator & Fault Injector
│   ├── main.py
│   ├── config.json
│   └── requirements.txt
│
└── [Projet 2] - Gateway MQTT GUI/     # Automated Reading Gateway (Modbus ➔ MQTT)
    ├── main.py
    ├── gateway_storage.db
    └── requirements.txt
