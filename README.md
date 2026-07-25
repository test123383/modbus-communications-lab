
# ⚡ Industrial Multiprotocol Gateway & Modbus Lab

> A comprehensive Python suite for industrial Modbus TCP simulation, network fault injection, dynamic configuration generation, and automated Modbus-to-MQTT gateway data publishing.

![Python](https://img.shields.io/badge/Python-3.8+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![GUI](https://img.shields.io/badge/UI-CustomTkinter-blue?style=for-the-badge)
![Protocol](https://img.shields.io/badge/Protocol-Modbus_TCP-orange?style=for-the-badge)
![Broker](https://img.shields.io/badge/MQTT-Broker_Active-green?style=for-the-badge)

---

## 📸 Applications Showcase

### 1. Modbus Protocol & Network Robustness Lab
![Modbus Simulator Interface]<img width="1160" height="742" alt="image2" src="https://github.com/user-attachments/assets/2ff42743-3c47-4e58-993d-7616ed05e216" />
)

*Features multi-block rule configuration, dynamic simulator controls, and real-time network anomaly injection (Latency, Timeout, Packet Loss, Micro-Cuts, and Device Silence).*

---

### 2. Automated Data Reading Gateway (Modbus TCP ➔ MQTT)
![Automated Gateway Interface](<img width="1160" height="742" alt="image2" src="https://github.com/user-attachments/assets/a2425526-8cdc-4be3-b7a7-667bf04b020e" />
)

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
