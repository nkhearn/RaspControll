# RaspControll

## Overview

RaspControll is a Flask-based web application designed to provide a comprehensive interface for managing and monitoring a Raspberry Pi remotely. It allows users to interact with various aspects of their Raspberry Pi, including GPIO pins, file system, system processes, and sensor data, all through a web browser. The application is built with a focus on modularity, allowing features to use real hardware data when available on a Raspberry Pi, or fall back to simulated data when running in an environment without the necessary hardware or libraries.

## Features

The application includes the following features:

*   **GPIO Management**: Controls real GPIO pins (if on Pi and `RPi.GPIO` library installed, otherwise simulated). Allows toggling pin states (ON/OFF).
*   **File Manager**: Provides an interface for browsing, uploading, downloading, and deleting files and folders within a configurable base directory on the Raspberry Pi (if `FILE_MANAGER_REAL_MODE` is enabled, otherwise simulated).
*   **SSH Shell**: Executes real commands directly on the Raspberry Pi via a web-based shell (use with extreme caution; no simulation for this feature when commands are entered).
*   **System Monitoring**: Displays real-time system statistics such as CPU usage, RAM usage, storage usage, network I/O, and uptime (if `psutil` library is installed, otherwise simulated).
*   **Camera Integration**: Shows a still image from a connected Pi camera (if a compatible camera and library like `picamera2` or `picamera` are available, otherwise a placeholder is shown). Full video streaming is not yet implemented.
*   **Sensor Readings**: Displays readings from various connected sensors like DHT22 (temperature/humidity), DS18B20 (temperature), BMP180/BMP280 (pressure/temperature), and Sense HAT (if libraries are installed and sensors connected, otherwise simulated).
*   **Process List**: Shows a list of running processes on the Raspberry Pi, including PID, user, CPU%, MEM%, and command name (if `psutil` library is installed, otherwise simulated). Includes a simulated "Kill" button.
*   **Raspberry Pi Information**: Displays static information about the Raspberry Pi model, SoC, RAM, OS version, etc. (currently simulated).
*   **Pinout Diagrams**: Shows a placeholder for Raspberry Pi GPIO pinout diagrams.
*   **Notifications**: A simple system to display application-generated notifications (e.g., file uploaded, GPIO toggled).
*   **Power Control**: Provides buttons to simulate shutdown and reboot actions. Real power commands are commented out by default for safety.

## Target Environment

This application is specifically designed to run on a **Raspberry Pi** single-board computer. While it can run in a simulated mode on other systems, full functionality (especially hardware interactions) requires a Raspberry Pi environment with appropriate peripherals and libraries installed.

## Setup and Installation on Raspberry Pi

Follow these steps to set up and install RaspControll on your Raspberry Pi:

1.  **Clone the Repository**:
    Open a terminal on your Raspberry Pi and run:
    ```bash
    git clone https://github.com/your-username/RaspControll.git # Replace with actual repo URL
    cd RaspControll
    ```

2.  **Create a Virtual Environment**:
    It's recommended to use a virtual environment to manage dependencies:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```
    To deactivate the virtual environment later, simply type `deactivate`.

3.  **Install Python Dependencies**:
    Install the core Python libraries required by the application:
    ```bash
    pip install -r requirements.txt
    ```
    This will install Flask and Pillow.

4.  **Install Raspberry Pi Specific Libraries (Optional but Recommended for Full Functionality)**:
    For features that interact with hardware, you'll need to install additional libraries. Here are the common ones used by RaspControll:

    *   **GPIO Control**:
        ```bash
        sudo apt-get update && sudo apt-get install -y python3-rpi.gpio # System package manager often preferred
        # OR
        # pip install RPi.GPIO
        ```
    *   **System Monitoring & Process List**:
        ```bash
        pip install psutil
        ```
    *   **Camera Integration**:
        *   For newer Raspberry Pi OS (Bullseye and later) with `libcamera`:
            ```bash
            sudo apt-get install -y python3-picamera2 libcamera-apps # Ensure OS packages are up-to-date
            # pip install picamera2 # Usually installed via apt on Pi
            ```
        *   For older Raspberry Pi OS versions (Legacy):
            ```bash
            pip install picamera
            ```
    *   **DHT Temperature/Humidity Sensors (e.g., DHT11, DHT22)**:
        ```bash
        pip install Adafruit_DHT
        ```
        You might also need to install `libgpiod2`: `sudo apt-get install -y libgpiod2`.
    *   **DS18B20 Temperature Sensors**:
        ```bash
        pip install w1thermsensor
        ```
        Requires 1-Wire interface to be enabled (see step 5).
    *   **BMP/BME Pressure/Temperature/Humidity Sensors (e.g., BMP180, BMP280 via I2C)**:
        ```bash
        pip install adafruit-circuitpython-bmp280 adafruit-blinka
        ```
        Requires I2C interface to be enabled (see step 5).
    *   **Sense HAT**:
        ```bash
        sudo apt-get install -y sense-hat # System package manager preferred
        # pip install sense-hat
        ```
        Requires I2C interface to be enabled.

5.  **Enable Hardware Interfaces (via `raspi-config`)**:
    For certain sensors and peripherals (like DS18B20, I2C-based sensors like BMP280, Sense HAT, and sometimes SPI devices), you'll need to enable the respective hardware interfaces on your Raspberry Pi:
    ```bash
    sudo raspi-config
    ```
    Navigate to `Interface Options` (or similar) and enable:
    *   `I2C` (for BMP280, Sense HAT, etc.)
    *   `1-Wire` (for DS18B20)
    *   `SPI` (if you have SPI devices, not explicitly used by default in RaspControll but good to know)
    *   `Camera` (to enable the official camera port)
    Reboot your Raspberry Pi if prompted after enabling interfaces.

## Configuration

Some aspects of the application can be configured by editing `app.py`:

*   **File Manager Base Directory**:
    *   The `FILE_MANAGER_BASE_DIR` variable in `app.py` defines the root directory for the File Manager feature when it's operating in real mode.
    *   By default, it is set to `Path.home() / "RaspControll_files"` (i.e., a folder named `RaspControll_files` in the home directory of the user running the Flask app).
    *   **Important**: It is crucial to choose a safe and dedicated directory for this feature. Setting it to sensitive system directories (e.g., `/`, `/etc`) can pose a significant security risk.
    *   The application attempts to create this directory if it doesn't exist. Ensure the user running the application has write permissions to the parent directory if `RaspControll_files` needs to be created, and read/write permissions for the base directory itself.

*   **GPIO Pins**:
    *   The `CONTROLLABLE_PINS` dictionary in `app.py` defines which GPIO pins are made available for control via the web interface.
    *   If you are using real GPIOs, you can modify this dictionary to change pin numbers (BCM mode), names, and default states. Ensure the pins you choose are safe to use as outputs and are not already in use by other critical hardware.

*   **Sensor Pins/Addresses**:
    *   For some sensors, like the DHT sensor, the GPIO pin it's connected to (`DHT_PIN` in the `/sensors` route in `app.py`) is hardcoded. You may need to adjust this value based on your wiring.
    *   For I2C-based sensors (like BMP280), the I2C address is usually auto-detected by the library, but ensure your sensor is connected to the correct I2C bus on the Pi.

## Usage

1.  **Activate Virtual Environment** (if you created one):
    ```bash
    source venv/bin/activate 
    ```
2.  **Run the Flask Application**:
    Navigate to the application directory (e.g., `cd RaspControll`) and run:
    ```bash
    python3 app.py
    ```
    By default, the application will run in debug mode on `http://127.0.0.1:5000/`. If you want to access it from other devices on your network, you can run it as:
    ```bash
    python3 app.py # And then access via http://<your_pi_ip_address>:5000
    # Or, for development, you can make Flask listen on all interfaces:
    # flask run --host=0.0.0.0 
    # (Note: `flask run` requires FLASK_APP=app.py to be set or uses auto-discovery)
    ```

3.  **Access Features**:
    Open a web browser and navigate to the IP address of your Raspberry Pi on port 5000 (e.g., `http://192.168.1.100:5000`). You can then use the navigation bar to access the different features.

## Security Considerations

**IMPORTANT**: Running a web application that can control hardware, manage files, and execute commands on your Raspberry Pi has inherent security risks. Please read the following carefully:

*   **Command Shell (SSH Shell)**:
    *   **HIGH RISK**: This feature allows arbitrary commands to be executed on your Raspberry Pi with the permissions of the user running the Flask web server.
    *   **Potential for Damage**: Malicious or accidentally incorrect commands can cause significant damage to your system, lead to data loss, or compromise your Raspberry Pi.
    *   **Basic Blacklist**: A very basic blacklist for some common dangerous commands (e.g., `sudo`, `reboot`, `rm -rf`) is implemented, but **this is not foolproof and can be bypassed**.
    *   **Access Control**: If you use this feature, **strongly restrict network access** to the RaspControll web application. Only allow trusted devices or users to connect. Consider firewall rules (`ufw` or `iptables`) or running the application on a private network.

*   **File Manager**:
    *   **Directory Configuration**: This feature allows file operations (listing, uploading, downloading, deleting) only within the configured `FILE_MANAGER_BASE_DIR`.
    *   **Risk of Misconfiguration**: If `FILE_MANAGER_BASE_DIR` is misconfigured to a sensitive system directory (e.g., `/`, `/home`, `/etc`), it could allow unauthorized access or modification of critical files. Always use a dedicated, non-critical directory.
    *   **Path Traversal**: Basic path traversal prevention is implemented in the `_secure_join` function. However, complex attacks might still be possible if there are bugs in the implementation or underlying libraries.

*   **Power Control**:
    *   **Default Behavior**: Real power commands (`shutdown`, `reboot`) are commented out in `app.py` by default. The buttons only simulate these actions.
    *   **Enabling Real Commands**: To enable real power control, you would need to uncomment the `os.system("sudo ...")` lines in `app.py`. This requires the user running the Flask application to have passwordless `sudo` privileges for the `shutdown` and `reboot` commands. **Configuring passwordless `sudo` is a significant security risk** and should only be done if you fully understand the implications and have other security measures in place.

*   **General Recommendations**:
    *   **Run as Non-Root User**: Always run the Flask application as a non-root user. This limits the potential damage if the application is compromised.
    *   **Network Exposure**: Be extremely cautious about exposing this application directly to the internet. It is best suited for use on a private, trusted local network.
    *   **HTTPS**: For any production-like use, or if accessed over an untrusted network, deploy RaspControll behind a proper web server like Nginx or Apache, configured with HTTPS to encrypt traffic.
    *   **Strong Credentials**: If you add any form of authentication in the future, ensure strong, unique credentials are used.
    *   **Keep Software Updated**: Regularly update your Raspberry Pi OS, Python, Flask, and all other libraries to patch security vulnerabilities.

## Developer Notes

*   **Simulated Data**: If hardware-specific Python libraries (e.g., `RPi.GPIO`, `psutil`, camera libraries, sensor libraries) are not found, or if hardware initialization fails, the application will gracefully fall back to using simulated data for the respective features. This allows for development and testing on systems without a full Raspberry Pi hardware setup. Check the console output when `app.py` starts to see which modules are loaded in real vs. simulated mode.
*   **Library Installation Comments**: `app.py` contains comments near the import sections for Raspberry Pi-specific libraries, noting their typical `pip install` commands or `apt-get` equivalents.
*   **Placeholder Images**: The application uses the Pillow library (`pip install Pillow`) to generate placeholder images (e.g., for the camera feed if no camera is detected, or for pinout diagrams). The script `create_placeholder.py` is used for this.
*   **Flask Debug Mode**: By default, the application runs with `app.run(debug=True)`. For any deployment scenario, ensure debug mode is turned OFF.
*   **Future Improvements**:
    *   User authentication and authorization.
    *   More robust error handling and logging.
    *   Configuration via a file instead of directly in `app.py`.
    *   AJAX for smoother UI updates (e.g., for sensor readings, SSH output).
    *   Implementation of real-time video streaming for the camera.
    *   More interactive sensor data (e.g., charts).

---

This README provides a comprehensive guide to setting up, configuring, using, and understanding the security implications of RaspControll. Use responsibly.
