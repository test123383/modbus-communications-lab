# modbus-communications-lab
Multi-threaded Modbus TCP industrial device simulator with network anomaly injection and dynamic batch configuration generator (JSON).

# Modbus Communications & Emulation Lab

This repository contains two complementary tools designed to simulate Modbus TCP industrial devices, generate emulator configurations in batches, and test the robustness of network communications.

---

# 1. Project Architecture (Directory Structure)

The following is the recommended folder organization for the projects:

```text
.

├── README.md                          # This file (Instructions & Getting Started Guide)
│
├── [Project 1] - Modbus Lab GUI/
│   ├── interface.py                   # Simulation interface & network anomaly injection
│   ├── config.json                    # Configuration file for physical simulators
│   └── requirements.txt               # Dependencies (customtkinter)
│
└── [Project 2] - Config Generator/
    ├── interface2.py                  # Dynamic configuration generator interface
    └── requirements.txt               # Dependencies (customtkinter)
