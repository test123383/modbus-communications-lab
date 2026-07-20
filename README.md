# modbus-communications-lab
Simulateur multi-threadé d'équipements industriels Modbus TCP avec injection d'anomalies réseau et générateur dynamique de configurations en bloc (JSON).

# Modbus Communications & Emulation Lab
 
Ce dépôt regroupe deux outils complémentaires conçus pour simuler des équipements industriels Modbus TCP, générer des configurations d'émulateurs en bloc, et tester la robustesse des communications réseau. 
 
---
 
## 📁 1. Architecture des Projets (Arborescence)
 
Voici l'organisation des fichiers recommandée pour vos dossiers :
 
```text

.

├── README.md                          # Ce fichier (Instructions & Guide de démarrage)

│

├── [Projet 1] - Modbus Lab GUI/

│   ├── interface.py                        # Interface de simulation & injection d'anomalies

│   ├── config.json                    # Fichier de configuration des simulateurs physiques

│   └── requirements.txt               # Dépendances (customtkinter)

│

└── [Projet 2] - Config Generator/

    ├── interface2.py                        # Interface du générateur de configuration dynamique 

    └── requirements.txt               # Dépendances (customtkinter) 
 
