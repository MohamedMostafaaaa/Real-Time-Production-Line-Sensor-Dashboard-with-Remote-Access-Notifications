# Deployment Guide (Production)

This document describes how to deploy the Sensor Dashboard system in production:
- Windows EXE build (PyInstaller)
- External YAML configuration
- Running simulator and webhook server as services (optional)
- Security, observability, and operational recommendations

---

## 1. Deployment Targets

### 1.1 Recommended Production Topology
- **Sensor_Dashboard.exe** on an operator/industrial PC (Windows)
- **Simulator** only for demo/testing (not needed in real deployment)
- **Webhook Server** on a server/VM (Linux or Windows) or hosted endpoint

### 1.2 Network Requirements
- App requires outbound HTTP access to webhook endpoint (e.g., `http://server:8000/alarm`)
- App requires inbound/outbound TCP access to sensor stream source (simulator or real device)
  - Default: TCP `127.0.0.1:9009` for local simulator

---

## 2. Configuration Management (config.yaml)

### 2.1 External Config Strategy (Recommended)
Place `config.yaml` next to the deployed EXE:

The app loads configuration in this order:
1) `APP_CONFIG` environment variable (if set)
2) `config.yaml` next to the EXE (production)
3) `./config.yaml` in current working directory (dev)

### 2.2 What Can Be Changed Without Rebuild
- Sensor low/high limits
- Alarm criteria parameters (temp diff delta, FTIR peaks, etc.)
- TCP transport host/port/timeouts
- Webhook URL + auth token

---

## 3. Building the Windows EXE

### 3.1 Build Prerequisites
- Windows 10/11
- Python 3.11+ (matching dev)
- Virtual environment recommended
- `PyInstaller` installed

### 3.2 Build Command
Using onedir technique:
  #### Command:
    pyinstaller -y --noconfirm --clean `
      --name "Sensor_Dashboard" `
      --windowed `
      --onedir `
      -p . `
      app/dev/run_app.py

  #### output:
    dist/Sensor_Dashboard/Sensor_Dashboard.exe

### 3.3 Deployable Folder Contents
- dist/Sensor_Dashboard/ directory (entire folder)
- config.yaml placed inside dist/Sensor_Dashboard/

## 4. Running in Production

### 4.1 Start the App
  #### Run:
    Sensor_Dashboard.exe


