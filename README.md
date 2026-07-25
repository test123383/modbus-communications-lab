# ⚡ Industrial Multiprotocol Gateway & Modbus Lab

> A comprehensive Python suite for industrial Modbus TCP simulation, network fault injection, dynamic configuration generation, and automated Modbus-to-MQTT gateway data publishing.

![Python](https://img.shields.io/badge/Python-3.8+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![GUI](https://img.shields.io/badge/UI-CustomTkinter-blue?style=for-the-badge)
![Protocol](https://img.shields.io/badge/Protocol-Modbus_TCP-orange?style=for-the-badge)
![Broker](https://img.shields.io/badge/MQTT-Broker_Active-green?style=for-the-badge)

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
    └── requirements.txt<img width="1881" height="1102" alt="image1" src="https://github.com/user-attachments/assets/fc210634-e015-4dc9-8487-373880277992" />
