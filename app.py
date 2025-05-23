# app.py
# Main Flask application for RaspControll

# Standard Library Imports
import io
import os
import datetime # For timestamps
import shutil
from pathlib import Path
import subprocess # For SSH command execution

# Third-party Library Imports
from flask import Flask, render_template, redirect, url_for, request, send_file, session, send_from_directory, flash
# Note: `flash` was imported in the prompt but not used in the final simulated app.
# If real notifications or feedback messages were implemented beyond simple page reloads,
# `flash` would be useful here.

# Raspberry Pi Specific Libraries (install these on your Pi for real hardware interaction)
# ------------------------------------------------------------------------------------
# For System Monitoring & Process List:
try:
    import psutil
    PSUTIL_AVAILABLE = True
    print("psutil library loaded successfully. Real system monitoring and process list enabled.")
except ImportError:
    PSUTIL_AVAILABLE = False
    print("psutil library not found. System monitoring and process list will be simulated.")

# For GPIO Control:
try:
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM) # Use Broadcom pin numbering
    GPIO.setwarnings(False) # Disable warnings
    RPI_GPIO_AVAILABLE = True
    # Define which pins are controllable and their default state/setup
    CONTROLLABLE_PINS = {
        17: {"name": "GPIO 17", "state": GPIO.LOW, "mode": GPIO.OUT, "id": 17},
        18: {"name": "GPIO 18", "state": GPIO.LOW, "mode": GPIO.OUT, "id": 18},
        27: {"name": "GPIO 27", "state": GPIO.LOW, "mode": GPIO.OUT, "id": 27},
    }
    # Setup initial pin modes
    for pin, config in CONTROLLABLE_PINS.items():
        GPIO.setup(pin, config["mode"], initial=config["state"])
    print("RPi.GPIO library loaded successfully. Real GPIO control enabled.")

except ImportError:
    RPI_GPIO_AVAILABLE = False
    CONTROLLABLE_PINS = { # Fallback to simulation
        17: {"name": "GPIO 17", "state": "OFF", "id": 17},
        18: {"name": "GPIO 18", "state": "ON", "id": 18},
        27: {"name": "GPIO 27", "state": "OFF", "id": 27},
    }
    print("RPi.GPIO library not found. GPIO control will be simulated.")
except RuntimeError as e: # Handle cases where RPi.GPIO is imported but not on a Pi
    RPI_GPIO_AVAILABLE = False
    CONTROLLABLE_PINS = { # Fallback to simulation
        17: {"name": "GPIO 17", "state": "OFF", "id": 17},
        18: {"name": "GPIO 18", "state": "ON", "id": 18},
        27: {"name": "GPIO 27", "state": "OFF", "id": 27},
    }
    print(f"RPi.GPIO could not be initialized (not on a Pi or no permissions): {e}. GPIO control will be simulated.")

# For Camera Integration
CAMERA_AVAILABLE = False
picam2 = None # For Picamera2
camera = None # For older PiCamera
try:
    from picamera2 import Picamera2
    picam2 = Picamera2()
    CAMERA_AVAILABLE = True
    print("Picamera2 library found and initialized.")
except (ImportError, RuntimeError, FileNotFoundError) as e: 
    print(f"Picamera2 not available ({e}), trying older PiCamera library...")
    try:
        from picamera import PiCamera
        camera = PiCamera()
        CAMERA_AVAILABLE = True
        print("PiCamera library found and initialized.")
    except (ImportError, RuntimeError) as e2:
        print(f"PiCamera also not available ({e2}). Camera feature will use placeholder.")

# For DHT Temperature/Humidity Sensors (e.g., DHT11, DHT22):
# import Adafruit_DHT # pip install Adafruit_DHT (may require libgpiod2 or other system deps)
#
# For DS18B20 Temperature Sensors:
# from w1thermsensor import W1ThermSensor # pip install w1thermsensor
#
# For BMP/BME Pressure/Temperature/Humidity Sensors (e.g., BMP180, BMP280, BME280 via I2C):
# import adafruit_bmp280 
# import board 
# import busio 
#
# For Sense HAT (provides various sensors, LED matrix, joystick):
# from sense_hat import SenseHat # pip install sense-hat
# ------------------------------------------------------------------------------------

# File Manager Configuration
FILE_MANAGER_BASE_DIR = Path.home() / "RaspControll_files"
FILE_MANAGER_REAL_MODE = False
try:
    FILE_MANAGER_BASE_DIR.mkdir(parents=True, exist_ok=True)
    test_file_path = FILE_MANAGER_BASE_DIR / ".perm_test"
    with open(test_file_path, "w") as f: f.write("test")
    with open(test_file_path, "r") as f: f.read()
    os.remove(test_file_path)
    FILE_MANAGER_REAL_MODE = True
    print(f"File Manager: Operating in real mode. Base directory: {FILE_MANAGER_BASE_DIR}")
    if not any(FILE_MANAGER_BASE_DIR.iterdir()): 
        (FILE_MANAGER_BASE_DIR / "sample_file.txt").write_text("Hello from RaspControll!")
        (FILE_MANAGER_BASE_DIR / "another_folder").mkdir(exist_ok=True)
        (FILE_MANAGER_BASE_DIR / "another_folder" / "nested_file.log").write_text("Log entry.")
except Exception as e:
    print(f"File Manager: Error setting up base directory {FILE_MANAGER_BASE_DIR}: {e}. Falling back to simulation.")
    FILE_MANAGER_REAL_MODE = False

# Helper function for formatting bytes
def format_bytes(bts):
    if bts < 1024: return f"{bts} B"
    elif bts < 1024**2: return f"{bts/1024:.2f} KB"
    elif bts < 1024**3: return f"{bts/1024**2:.2f} MB"
    else: return f"{bts/1024**3:.2f} GB"

# Secure path joining function for File Manager
def _secure_join(base_path: Path, current_relative_path_str: str) -> Path | None:
    if ".." in current_relative_path_str.split(os.sep):
        flash("Path traversal attempt detected (contains '..').", "danger")
        return None
    clean_relative_path_str = current_relative_path_str.lstrip('/')
    try:
        combined_path = base_path.joinpath(clean_relative_path_str).resolve()
        if base_path != Path(os.path.commonpath([base_path, combined_path])):
            flash("Attempt to access outside designated file manager directory.", "danger")
            return None
        return combined_path
    except Exception as e:
        flash(f"Error resolving path '{current_relative_path_str}': {e}", "danger")
        return None

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Simulated Notifications
simulated_notifications = [
    {"message": "System started successfully.", "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")},
]

# Simulated File System (used if FILE_MANAGER_REAL_MODE is False)
simulated_files = [
    {"name": "File1.txt", "type": "file", "path": "/"},
    {"name": "Document.pdf", "type": "file", "path": "/"},
    {"name": "Folder1", "type": "directory", "path": "/"},
    {"name": "image.jpg", "type": "file", "path": "/Folder1/"},
]

# Simulated System Statistics (Fallback)
dummy_stats = {
    "cpu_usage": "25% (Simulated)", "cpu_usage_percent": 25,
    "ram_usage": "512MB / 1024MB (50.00%) (Simulated)", "ram_percent": 50.00,
    "storage_usage": "10GB / 32GB (31.25%) (Simulated)", "disk_percent": 31.25,
    "network_sent": "1.20 GB (Simulated)",
    "network_received": "500.00 MB (Simulated)", 
    "uptime": "3 days, 5 hours, 0 minutes (Simulated)"
}
# Simulated Sensor Data
dummy_sensor_data = {
    "dht22": {"temperature": "23°C (Simulated)", "humidity": "45% (Simulated)"},
    "ds18b20": {"temperature": "22.5°C (Simulated)"},
    "bmp180": {"pressure": "1012 hPa (Simulated)", "temperature": "24°C (Simulated)", "altitude": "150m (Simulated)"},
    "sense_hat": {"temperature": "23.5°C (Simulated)", "humidity": "46% (Simulated)", "pressure": "1011 hPa (Simulated)",
                  "joystick": "Middle (Simulated)", "orientation": "Pitch: 0, Roll: 0, Yaw: 0 (Simulated)"}
}
# Simulated Process List
dummy_processes = [
    {"pid": 101, "user": "pi", "cpu": "5.2%", "mem": "2.1%", "command": "/usr/bin/python3 app.py (Simulated)"},
    {"pid": 152, "user": "root", "cpu": "0.5%", "mem": "1.0%", "command": "sshd: pi [priv] (Simulated)"},
]
# Simulated Raspberry Pi Information
dummy_pi_info = {
    "model": "Raspberry Pi 3 Model B+ Rev 1.3 (Simulated)",
    "soc": "BCM2837B0 (Simulated)",
    "ram": "1GB (Simulated)",
    "serial_number": "SIMULATED00000000e0d5c7e5",
    "os_version": "Raspbian GNU/Linux 10 (buster) (Simulated)",
    "kernel_version": "5.4.51-v7l+ (Simulated)"
}

# Function to get real Raspberry Pi information
def get_real_pi_info():
    info = dummy_pi_info.copy() # Start with defaults, override with real data

    try: # Get Model, SoC, Serial from /proc/cpuinfo
        output = subprocess.check_output(["cat", "/proc/cpuinfo"], text=True)
        lines = output.splitlines()
        model_found = False
        soc_found = False
        serial_found = False
        for line in lines:
            if line.startswith("Hardware") and not model_found: # Often used for SoC/Model on older Pis
                info["soc"] = line.split(":")[1].strip()
                # Model might be same as SoC or derived, let's try to find a better "Model" line
                # If "Model" line specific to Pi is found, it will overwrite this.
                info["model"] = info["soc"] 
                soc_found = True # Hardware line can be a proxy for SoC
            if line.startswith("Model") and not model_found: # More specific model line for some Pis
                 info["model"] = line.split(":")[1].strip()
                 model_found = True
            if line.lower().startswith("model name") and not soc_found: # Common for CPU model, can be SoC too
                info["soc"] = line.split(":")[1].strip()
                soc_found = True
            if line.startswith("Serial") and not serial_found:
                info["serial_number"] = line.split(":")[1].strip()
                serial_found = True
            # If both model and soc found, and serial is found (or we don't care if it's missing for this check)
            if model_found and soc_found and serial_found: 
                break
        if not model_found: print("Warning: Could not parse Model from /proc/cpuinfo. Using default.")
        if not soc_found: print("Warning: Could not parse SoC from /proc/cpuinfo. Using default.")
        if not serial_found: print("Warning: Could not parse Serial Number from /proc/cpuinfo. Using default.")

    except Exception as e:
        print(f"Error reading /proc/cpuinfo: {e}. Falling back to dummy values for model, soc, serial.")

    try: # Get RAM from free -m
        output = subprocess.check_output(["free", "-m"], text=True)
        lines = output.splitlines()
        for line in lines:
            if line.startswith("Mem:"):
                parts = line.split()
                info["ram"] = f"{parts[1]}MB" # Total RAM in MB
                break
        else: print("Warning: Could not parse RAM from 'free -m'. Using default.")
    except Exception as e:
        print(f"Error running 'free -m': {e}. Falling back to dummy value for RAM.")

    try: # Get OS Version from /etc/os-release
        output = subprocess.check_output(["cat", "/etc/os-release"], text=True)
        lines = output.splitlines()
        for line in lines:
            if line.startswith("PRETTY_NAME="):
                info["os_version"] = line.split("=")[1].strip().strip('"')
                break
        else: print("Warning: Could not parse OS Version from /etc/os-release. Using default.")
    except Exception as e:
        print(f"Error reading /etc/os-release: {e}. Falling back to dummy value for OS Version.")

    try: # Get Kernel Version from uname -r
        info["kernel_version"] = subprocess.check_output(["uname", "-r"], text=True).strip()
    except Exception as e:
        print(f"Error running 'uname -r': {e}. Falling back to dummy value for Kernel Version.")
        
    # Ensure all keys still exist, even if some commands failed.
    for key, val in dummy_pi_info.items():
        if key not in info or info[key] is None: # If a key was missed or set to None
            info[key] = val + " (Error fetching)" # Mark as error for this specific field
            print(f"Warning: Using fallback for '{key}' due to previous error or missing value.")

    return info

@app.route('/')
def index(): return render_template('index.html')

@app.route('/gpio')
def gpio():
    current_pins_state = []
    if RPI_GPIO_AVAILABLE:
        for pin_id, config in CONTROLLABLE_PINS.items():
            if config["mode"] == GPIO.OUT:
                state = GPIO.input(pin_id)
                current_pins_state.append({"id": pin_id, "name": config["name"], "state": "ON" if state == GPIO.HIGH else "OFF"})
    else: 
        for pin_id, config in CONTROLLABLE_PINS.items():
            current_pins_state.append({"id": pin_id, "name": config["name"], "state": config["state"]})
    return render_template('gpio.html', pins=current_pins_state)

@app.route('/gpio/toggle/<int:pin_id>')
def toggle_gpio(pin_id):
    action_msg = ""
    if RPI_GPIO_AVAILABLE:
        if pin_id in CONTROLLABLE_PINS and CONTROLLABLE_PINS[pin_id]["mode"] == GPIO.OUT:
            current_state = GPIO.input(pin_id)
            new_state = not current_state
            GPIO.output(pin_id, new_state)
            action = "turned ON" if new_state == GPIO.HIGH else "turned OFF"
            action_msg = f"Real GPIO pin {CONTROLLABLE_PINS[pin_id]['name']} {action}."
    else:
        if pin_id in CONTROLLABLE_PINS:
            current_state = CONTROLLABLE_PINS[pin_id]["state"]
            new_state = "ON" if current_state == "OFF" else "OFF"
            CONTROLLABLE_PINS[pin_id]["state"] = new_state
            action_msg = f"Simulated GPIO pin {CONTROLLABLE_PINS[pin_id]['name']} {new_state}."
    if action_msg: simulated_notifications.insert(0, {"message": action_msg, "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
    return redirect(url_for('gpio'))

@app.route('/file-manager/', defaults={'current_dir_path': ''})
@app.route('/file-manager/<path:current_dir_path>')
def file_manager(current_dir_path):
    if FILE_MANAGER_REAL_MODE:
        abs_current_path = _secure_join(FILE_MANAGER_BASE_DIR, current_dir_path)
        if abs_current_path is None: return redirect(url_for('file_manager', current_dir_path='')) 
        files_and_folders = []
        try:
            for item in abs_current_path.iterdir():
                files_and_folders.append({
                    "name": item.name, "type": "directory" if item.is_dir() else "file",
                    "link_path": str(Path(current_dir_path) / item.name), 
                    "op_path": str(Path(current_dir_path) / item.name),
                    "size": format_bytes(item.stat().st_size) if item.is_file() else "-",
                    "modified": datetime.datetime.fromtimestamp(item.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')})
        except Exception as e:
            flash(f"Error listing files in '{current_dir_path}': {e}", "danger")
            return redirect(url_for('file_manager', current_dir_path=''))
        files_and_folders.sort(key=lambda x: (x['type'] != 'directory', x['name'].lower()))
        parent_path_obj = Path(current_dir_path).parent
        parent_path_str = str(parent_path_obj) if current_dir_path else None
        if parent_path_str == ".": parent_path_str = ""
        return render_template('file_manager.html', files=files_and_folders, current_path=current_dir_path, parent_path=parent_path_str, real_mode=True, FILE_MANAGER_BASE_DIR=FILE_MANAGER_BASE_DIR) # Pass base dir for display
    else: 
        processed_simulated_files = []
        for s_file in simulated_files:
            sim_op_path = (s_file['path'].lstrip('/') + s_file['name']).lstrip('/')
            if not sim_op_path: sim_op_path = s_file['name']
            processed_simulated_files.append({"name": s_file['name'], "type": s_file['type'], "link_path": sim_op_path, 
                                              "op_path": sim_op_path, "size": "-", "modified": "-", 
                                              "simulated_original_path_attr": s_file['path']})
        return render_template('file_manager.html', files=processed_simulated_files, current_path="Simulated Root", parent_path=None, real_mode=False)

@app.route('/file-manager/upload/<path:current_dir_path>', methods=['POST'])
@app.route('/file-manager/upload', defaults={'current_dir_path': ''}, methods=['POST'])
def upload_file(current_dir_path):
    from werkzeug.utils import secure_filename
    redirect_path = current_dir_path if FILE_MANAGER_REAL_MODE else ''
    if FILE_MANAGER_REAL_MODE:
        abs_target_dir = _secure_join(FILE_MANAGER_BASE_DIR, current_dir_path)
        if abs_target_dir is None or not abs_target_dir.is_dir():
            flash("Invalid target directory for upload.", "danger")
        elif 'file' not in request.files or request.files['file'].filename == '':
            flash('No file selected for upload.', 'warning')
        else:
            file = request.files['file']
            filename = secure_filename(file.filename)
            try:
                file.save(abs_target_dir / filename)
                flash(f"File '{filename}' uploaded successfully to '{current_dir_path}'.", "success")
                simulated_notifications.insert(0, {"message": f"Real upload of {filename} to {current_dir_path}.", "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
            except Exception as e: flash(f"Error uploading file '{filename}': {e}", "danger")
    else: 
        if 'file' in request.files and request.files['file'].filename != '':
            file = request.files['file']
            simulated_files.append({"name": file.filename, "type": "file", "path": "/"}) # Simplified sim path
            flash(f"Simulated upload of '{file.filename}'.", "info")
            simulated_notifications.insert(0, {"message": f"Simulated upload of {file.filename}.", "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
        else: flash('No file selected for simulated upload.', 'warning')
    return redirect(url_for('file_manager', current_dir_path=redirect_path))

@app.route('/file-manager/download/<path:item_path>')
def download_file(item_path): # item_path is op_path
    parent_dir_for_redirect = str(Path(item_path).parent)
    if parent_dir_for_redirect == ".": parent_dir_for_redirect = ""
    if FILE_MANAGER_REAL_MODE:
        abs_item_path = _secure_join(FILE_MANAGER_BASE_DIR, item_path)
        if abs_item_path is None or not abs_item_path.is_file():
            flash("File not found or access denied.", "danger")
        else:
            try: return send_from_directory(abs_item_path.parent, abs_item_path.name, as_attachment=True)
            except Exception as e: flash(f"Error downloading file '{abs_item_path.name}': {e}", "danger")
    else: 
        file_to_download = None
        for f_item_sim_list in simulated_files:
            original_sim_op_path = (f_item_sim_list['path'].lstrip('/') + f_item_sim_list['name']).lstrip('/')
            if not original_sim_op_path: original_sim_op_path = f_item_sim_list['name']
            if original_sim_op_path == item_path: file_to_download = f_item_sim_list; break
        if file_to_download and file_to_download['type'] == 'file':
            return send_file(io.BytesIO(f"This is a simulated download of {file_to_download['name']}".encode()), 
                             mimetype='text/plain', as_attachment=True, download_name=file_to_download['name'])
        else: flash(f"Simulated file '{item_path}' not found for download.", "warning")
    return redirect(url_for('file_manager', current_dir_path=parent_dir_for_redirect if FILE_MANAGER_REAL_MODE else ''))

@app.route('/file-manager/delete/<path:item_path>', methods=['GET', 'POST'])
def delete_file_or_folder(item_path): # item_path is op_path
    current_dir_path_for_redirect = str(Path(item_path).parent)
    if current_dir_path_for_redirect == ".": current_dir_path_for_redirect = ""
    if FILE_MANAGER_REAL_MODE:
        abs_item_path = _secure_join(FILE_MANAGER_BASE_DIR, item_path)
        if abs_item_path is not None:
            try:
                item_name = abs_item_path.name
                if abs_item_path.is_file(): os.remove(abs_item_path); item_type = "File"
                elif abs_item_path.is_dir(): shutil.rmtree(abs_item_path); item_type = "Directory"
                else: flash(f"Item '{item_name}' not found or is not a file/directory.", "warning"); return redirect(url_for('file_manager', current_dir_path=current_dir_path_for_redirect))
                flash(f"{item_type} '{item_name}' deleted successfully.", "success")
                simulated_notifications.insert(0, {"message": f"Real deletion of {item_type.lower()} {item_name}.", "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
            except Exception as e: flash(f"Error deleting '{abs_item_path.name if 'abs_item_path' in locals() else item_path}': {e}", "danger")
    else: 
        global simulated_files
        item_found_and_deleted = False
        final_sim_list = []
        deleted_item_type_sim = ""
        for f_s in simulated_files:
            current_s_op_path = (f_s['path'].lstrip('/') + f_s['name']).lstrip('/')
            if not current_s_op_path: current_s_op_path = f_s['name']
            is_target = (current_s_op_path == item_path)
            is_inside_deleted_dir = False
            if not is_target and deleted_item_type_sim == 'directory' and current_s_op_path.startswith(item_path + '/'):
                is_inside_deleted_dir = True # Basic check for items inside a deleted directory
            if is_target:
                item_found_and_deleted = True
                deleted_item_type_sim = f_s['type']
                if deleted_item_type_sim != 'directory': # If it's a file, or a dir that we are not recursively deleting for sim
                    continue # Don't add to final list
            if not is_target and not is_inside_deleted_dir:
                final_sim_list.append(f_s)
        if item_found_and_deleted:
            simulated_files = final_sim_list
            flash(f"Simulated deletion of '{item_path}'.", "info")
            simulated_notifications.insert(0, {"message": f"Simulated deletion of {item_path}.", "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
        else: flash(f"Simulated item '{item_path}' not found for deletion.", "warning")
    return redirect(url_for('file_manager', current_dir_path=current_dir_path_for_redirect if FILE_MANAGER_REAL_MODE else ''))

@app.route('/ssh', endpoint='ssh_shell_page')
def ssh_shell_page():
    last_command = session.get('last_command', '')
    last_command_output = session.get('last_command_output', '')
    last_command_error = session.get('last_command_error', '')
    if not last_command and not last_command_output and not last_command_error:
        last_command_output = "No commands executed yet or history cleared."
    return render_template('ssh_shell.html', last_command=last_command, last_command_output=last_command_output, last_command_error=last_command_error)

@app.route('/ssh/command', methods=['POST'], endpoint='ssh_command_execute')
def ssh_command_execute():
    command_str = request.form.get('command', '').strip()
    command_output = ""
    command_error = ""
    session['last_command'] = command_str

    if not command_str:
        flash("Please enter a command.", "warning")
        session['last_command_output'] = ""
        session['last_command_error'] = "No command entered."
    elif command_str.lower() == 'clear':
        session['last_command'] = ''
        session['last_command_output'] = 'Command history cleared.'
        session['last_command_error'] = ''
        flash("SSH history cleared.", "info")
    else:
        try:
            command_parts = command_str.split()
            if not command_parts:
                flash("Empty command after splitting.", "warning")
                command_error = "Empty command."
            else:
                forbidden_commands = ['sudo', 'reboot', 'shutdown', 'rm -rf', 'mkfs', 'fdisk', 'dd', 'mv', 'cp', 'chown', 'chmod']
                if any(part in forbidden_commands for part in command_parts[0].split('/')) or command_parts[0] in forbidden_commands :
                    command_error = "Error: Execution of potentially dangerous or filesystem-modifying commands is not allowed."
                    flash(command_error, "danger")
                else:
                    timeout_seconds = 10
                    completed_process = subprocess.run(
                        command_parts, capture_output=True, text=True,
                        timeout=timeout_seconds, check=False, cwd=str(Path.home()) # Run in user's home dir
                    )
                    command_output = completed_process.stdout.strip()
                    if completed_process.stderr:
                        command_error = f"Error Output:\n{completed_process.stderr.strip()}"
                    if completed_process.returncode != 0:
                        err_msg = f"Command exited with status code: {completed_process.returncode}"
                        command_error = f"{command_error}\n{err_msg}".strip() if command_error else err_msg
                    if completed_process.returncode == 0 and not command_output and not command_error:
                        command_output = "[Command executed successfully with no output]"
        except subprocess.TimeoutExpired:
            command_error = f"Error: Command timed out after {timeout_seconds} seconds."
            flash(command_error, "danger")
        except FileNotFoundError:
            command_error = f"Error: Command not found: {command_parts[0]}"
            flash(command_error, "danger")
        except Exception as e:
            command_error = f"Error executing command: {str(e)}"
            flash(command_error, "danger")
        session['last_command_output'] = command_output
        session['last_command_error'] = command_error
    return redirect(url_for('ssh_shell_page'))

@app.route('/ssh/clear_history', methods=['POST'], endpoint='clear_ssh_history')
def clear_ssh_history():
    session.pop('last_command', None)
    session.pop('last_command_output', None)
    session.pop('last_command_error', None)
    flash("SSH command history cleared.", "info")
    return redirect(url_for('ssh_shell_page'))

@app.route('/system-monitoring')
def system_monitoring():
    stats_to_display = dummy_stats.copy(); simulation_note = ""
    pi_info_data = get_real_pi_info()

    if PSUTIL_AVAILABLE:
        try:
            cpu_usage_val = psutil.cpu_percent(interval=0.5)
            ram = psutil.virtual_memory()
            ram_total_fmt = format_bytes(ram.total)
            ram_used_fmt = format_bytes(ram.used)
            ram_percent_val = ram.percent
            
            disk = psutil.disk_usage('/')
            disk_total_fmt = format_bytes(disk.total)
            disk_used_fmt = format_bytes(disk.used)
            disk_percent_val = disk.percent
            
            net_io = psutil.net_io_counters()
            net_sent_fmt = format_bytes(net_io.bytes_sent)
            net_received_fmt = format_bytes(net_io.bytes_recv)
            
            boot_time_timestamp = psutil.boot_time()
            current_time_timestamp = datetime.datetime.now().timestamp()
            uptime_seconds = current_time_timestamp - boot_time_timestamp
            days = int(uptime_seconds // (24 * 3600))
            uptime_seconds %= (24 * 3600)
            hours = int(uptime_seconds // 3600)
            uptime_seconds %= 3600
            minutes = int(uptime_seconds // 60)
            uptime_str = f"{days} days, {hours} hours, {minutes} minutes"
            
            stats_to_display = {
                "cpu_usage": f"{cpu_usage_val}%", "cpu_usage_percent": cpu_usage_val,
                "ram_usage": f"{ram_used_fmt} / {ram_total_fmt} ({ram_percent_val}%)", "ram_percent": ram_percent_val,
                "storage_usage": f"{disk_used_fmt} / {disk_total_fmt} ({disk_percent_val}%)", "disk_percent": disk_percent_val,
                "network_sent": net_sent_fmt,
                "network_received": net_received_fmt, 
                "uptime": uptime_str
            }
        except Exception as e:
            print(f"Error fetching system stats with psutil: {e}. Falling back to simulated data.")
            simulation_note = f" (Error: {e}. Using simulated data.)"
            # Apply simulation note to string display values if error occurs
            for key in ["cpu_usage", "ram_usage", "storage_usage", "network_sent", "network_received", "uptime"]:
                if key in stats_to_display: # stats_to_display would be dummy_stats here
                    if "(Simulated)" not in stats_to_display[key] and simulation_note not in stats_to_display[key]:
                         stats_to_display[key] = stats_to_display[key].replace("(Simulated)", simulation_note) if "(Simulated)" in stats_to_display[key] else f"{stats_to_display[key]}{simulation_note}"
                # Ensure numeric keys have fallbacks from dummy_stats if psutil fails mid-way
                if key + "_percent" in dummy_stats and key + "_percent" not in stats_to_display:
                    stats_to_display[key + "_percent"] = dummy_stats[key + "_percent"]


    else: # psutil not available
        simulation_note = " (psutil not available. Using simulated data.)"
        # Apply simulation note to string display values
        for key in ["cpu_usage", "ram_usage", "storage_usage", "network_sent", "network_received", "uptime"]:
            if key in stats_to_display: # stats_to_display is dummy_stats here
                 if "(Simulated)" not in stats_to_display[key] and simulation_note not in stats_to_display[key]:
                    stats_to_display[key] = stats_to_display[key].replace("(Simulated)", simulation_note) if "(Simulated)" in stats_to_display[key] else f"{stats_to_display[key]}{simulation_note}"
        # Ensure numeric keys from dummy_stats are present
        stats_to_display.setdefault("cpu_usage_percent", dummy_stats["cpu_usage_percent"])
        stats_to_display.setdefault("ram_percent", dummy_stats["ram_percent"])
        stats_to_display.setdefault("disk_percent", dummy_stats["disk_percent"])

    return render_template('system_monitoring.html', stats=stats_to_display, pi_info=pi_info_data)

@app.route('/camera', endpoint='camera_page')
def camera_page(): return render_template('camera.html')

@app.route('/camera_feed')
def camera_feed():
    if CAMERA_AVAILABLE:
        try:
            img_buffer = io.BytesIO()
            if picam2: 
                if not picam2.started: 
                    config = picam2.create_still_configuration(main={"size": (1280, 720)}); picam2.configure(config); picam2.start()
                picam2.capture_file(img_buffer, format='jpeg')
            elif camera: 
                if camera.resolution is None or camera.resolution == (0,0): camera.resolution = (1280, 720)
                camera.capture(img_buffer, format='jpeg', use_video_port=True)
            img_buffer.seek(0)
            return send_file(img_buffer, mimetype='image/jpeg')
        except Exception as e:
            print(f"Error capturing image: {e}")
            simulated_notifications.insert(0, {"message": f"Error capturing image: {e}. Displaying placeholder.", "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
    return send_from_directory(os.path.join(app.root_path, 'static/images'), 'placeholder_camera.png')
# Notes on Real-time Video Streaming: (MJPEG, multipart HTTP response, dedicated camera thread, etc.)

@app.route('/sensors')
def sensors():
    sensor_readings = {'dht22': dummy_sensor_data['dht22'].copy(), 'ds18b20': dummy_sensor_data['ds18b20'].copy(), 
                       'bmp180': dummy_sensor_data['bmp180'].copy(), 'sense_hat': dummy_sensor_data['sense_hat'].copy()}
    for key in sensor_readings:
        for k_sub, v_sub in sensor_readings[key].items(): sensor_readings[key][k_sub] = f"{v_sub}"
        sensor_readings[key]['simulated_reason'] = "Real sensor read not attempted or failed by default."
    try: # DHT22
        import Adafruit_DHT; DHT_SENSOR_TYPE = Adafruit_DHT.DHT22; DHT_PIN = 4
        humidity, temperature = Adafruit_DHT.read_retry(DHT_SENSOR_TYPE, DHT_PIN)
        if humidity is not None and temperature is not None: sensor_readings['dht22'] = {'temperature': f"{temperature:.1f}°C", 'humidity': f"{humidity:.1f}%"}
        else: sensor_readings['dht22']['simulated_reason'] = "Failed to get reading from DHT sensor."
    except ImportError: sensor_readings['dht22']['simulated_reason'] = "Adafruit_DHT library not found."
    except RuntimeError as e: sensor_readings['dht22']['simulated_reason'] = f"DHT runtime error: {e}"
    except Exception as e: sensor_readings['dht22']['simulated_reason'] = f"Unexpected DHT error: {e}"
    try: # DS18B20
        from w1thermsensor import W1ThermSensor, NoSensorFoundError, KernelModuleLoadError
        ds_sensor = W1ThermSensor(); temperature = ds_sensor.get_temperature()
        sensor_readings['ds18b20'] = {'temperature': f"{temperature:.1f}°C"}
    except ImportError: sensor_readings['ds18b20']['simulated_reason'] = "w1thermsensor library not found."
    except NoSensorFoundError: sensor_readings['ds18b20']['simulated_reason'] = "No DS18B20 sensor found."
    except KernelModuleLoadError as e: sensor_readings['ds18b20']['simulated_reason'] = f"DS18B20 kernel module error: {e}"
    except Exception as e: sensor_readings['ds18b20']['simulated_reason'] = f"DS18B20 error: {e}"
    try: # BMP280
        import board; import busio; import adafruit_bmp280
        i2c = busio.I2C(board.SCL, board.SDA); bmp280 = adafruit_bmp280.Adafruit_BMP280_I2C(i2c)
        sensor_readings['bmp180'] = {'temperature': f"{bmp280.temperature:.1f}°C", 'pressure': f"{bmp280.pressure:.1f} hPa"}
        if 'altitude' in sensor_readings['bmp180']: del sensor_readings['bmp180']['altitude'] 
    except ImportError: sensor_readings['bmp180']['simulated_reason'] = "BMP280/board/busio library not found."
    except RuntimeError as e: sensor_readings['bmp180']['simulated_reason'] = f"BMP280 runtime error (check I2C): {e}"
    except Exception as e: sensor_readings['bmp180']['simulated_reason'] = f"BMP280 error: {e}"
    try: # Sense HAT
        from sense_hat import SenseHat; sense = SenseHat()
        sensor_readings['sense_hat'] = {'temperature': f"{sense.get_temperature():.1f}°C", 'humidity': f"{sense.get_humidity():.1f}%", 
                                        'pressure': f"{sense.get_pressure():.1f} hPa", 'joystick': "N/A", 'orientation': "N/A"}
    except ImportError: sensor_readings['sense_hat']['simulated_reason'] = "SenseHat library not found."
    except OSError as e: sensor_readings['sense_hat']['simulated_reason'] = f"Sense HAT OS error (not connected?): {e}"
    except Exception as e: sensor_readings['sense_hat']['simulated_reason'] = f"Sense HAT error: {e}"
    return render_template('sensors.html', sensors=sensor_readings)

@app.route('/processes')
def processes():
    processes_to_display = dummy_processes; simulation_note = "" 
    if PSUTIL_AVAILABLE:
        real_processes = []
        try:
            for proc in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_percent']):
                try:
                    pinfo = proc.info; cpu_percent_formatted = f"{pinfo['cpu_percent']:.1f}%"; memory_percent_formatted = f"{pinfo['memory_percent']:.1f}%"
                    real_processes.append({'pid': pinfo['pid'], 'user': pinfo['username'], 'cpu': cpu_percent_formatted, 'mem': memory_percent_formatted, 'command': pinfo['name']})
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess): pass
                except Exception as e: print(f"Error fetching info for a process: {e}"); pass 
            processes_to_display = real_processes
            if not real_processes: 
                 simulation_note = " (Could not fetch real process list, using simulated data)"; processes_to_display = dummy_processes 
                 for proc_item in processes_to_display: 
                    if simulation_note not in proc_item.get('command', ''): proc_item['command'] = f"{proc_item.get('command', '')}{simulation_note}"
        except Exception as e: 
            print(f"Error iterating over processes with psutil: {e}. Falling back to simulated data.")
            simulation_note = f" (Error: {e}. Using simulated data.)"
            for proc_item in processes_to_display: 
                if "(Simulated)" not in proc_item.get('command', '') and simulation_note not in proc_item.get('command', ''): proc_item['command'] = f"{proc_item.get('command', '')}{simulation_note}"
    else:
        simulation_note = " (psutil not available. Using simulated data.)"
        for proc_item in processes_to_display: 
            if "(Simulated)" not in proc_item.get('command', '') and simulation_note not in proc_item.get('command', ''): proc_item['command'] = f"{proc_item.get('command', '')}{simulation_note}"
    processes_to_display = sorted(processes_to_display, key=lambda p: p.get('pid', 0))
    return render_template('processes.html', processes=processes_to_display)

@app.route('/pi-info')
def pi_info():
    pi_data = get_real_pi_info()
    return render_template('pi_info.html', pi_info=pi_data)

@app.route('/pinout')
def pinout(): return render_template('pinout_diagrams.html')

@app.route('/pinout_image')
def pinout_image(): return send_from_directory(os.path.join(app.root_path, 'static/images'), 'placeholder_pinout.png')

@app.route('/notifications')
def notifications(): return render_template('notifications.html', notifications=simulated_notifications)

@app.route('/notifications/add', methods=['POST'])
def add_notification():
    message = request.form.get('message')
    if message: simulated_notifications.insert(0, {"message": message, "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
    return redirect(url_for('notifications'))

@app.route('/notifications/clear', methods=['POST'])
def clear_notifications():
    global simulated_notifications; simulated_notifications = []
    return redirect(url_for('notifications'))

@app.route('/power')
def power(): return render_template('power_control.html')

@app.route('/power/shutdown', methods=['POST'])
def power_shutdown():
    print("Attempting system shutdown...")
    simulated_notifications.insert(0, {"message": "System shutdown initiated.", "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
    os.system("sudo shutdown now") # Real command
    return "<h1>System Shutdown Initiated</h1><p>If this were a real Raspberry Pi, it would now be shutting down. Close this window.</p><a href='/'>Back to Home (if not shutting down)</a>"

@app.route('/power/reboot', methods=['POST'])
def power_reboot():
    print("Attempting system reboot...")
    simulated_notifications.insert(0, {"message": "System reboot initiated.", "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
    os.system("sudo reboot") # Real command
    return "<h1>System Reboot Initiated</h1><p>If this were a real Raspberry Pi, it would now be rebooting. Close this window.</p><a href='/'>Back to Home (if not rebooting)</a>"

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
