from obswebsocket import obsws, requests
import time
import psutil
import subprocess
import socket
import os
host = os.getenv("OBS_HOST")
port = os.getenv("OBS_PORT", "4455")  # Default port for OBS WebSocket
password = os.getenv("OBS_PASSWORD")  # Set your OBS WebSocket password

# Configuration
OBS_PATH =os.getenv("OBS_PATH", r"C:\Program Files\obs-studio\bin\64bit\obs64.exe")  # Path to OBS executable
OBS_DIR = os.getenv("OBS_DIR", r"C:\Program Files\obs-studio\bin\64bit")  # Directory containing OBS executable

def is_obs_running():
    for proc in psutil.process_iter(['name']):
        if proc.info['name'] and 'obs64.exe' in proc.info['name'].lower():
            return True
    return False

def wait_for_obs_websocket(timeout=20):
    """Wait until OBS WebSocket server is accepting connections."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.settimeout(1)
                s.connect((host, port))
                return True
            except (ConnectionRefusedError, socket.timeout):
                time.sleep(1)
    return False

def launch_obs():
    if not is_obs_running():
        print("Launching OBS Studio...")
        try:
            subprocess.Popen([OBS_PATH], cwd=OBS_DIR)
        except Exception as e:
            print("Failed to launch OBS:", e)
            return False
        print("Waiting for OBS to initialize...")
    else:
        print("OBS is already running.")
    
    print("Waiting for WebSocket server...")
    if not wait_for_obs_websocket():
        print("OBS WebSocket server did not respond in time.")
        return False
    print("OBS WebSocket is ready.")
    return True

def start_obs_recording():
    if not launch_obs():
        return
    try:
        ws = obsws(host, port, password)
        ws.connect()
        response = ws.call(requests.StartRecord())
        print("🎥 Started recording:", response.status)
        ws.disconnect()
    except Exception as e:
        print("Failed to start recording:", e)

def stop_obs_recording():
    try:
        ws = obsws(host, port, password)
        ws.connect()
        response = ws.call(requests.StopRecord())
        print("Stopped recording:", response.status)
        ws.disconnect()
    except Exception as e:
        print("Failed to stop recording:", e)

if __name__ == "__main__":
    start_obs_recording()
    time.sleep(10)
    stop_obs_recording()
