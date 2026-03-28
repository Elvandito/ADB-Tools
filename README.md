<div align="center">

# ⚡ ADB Desktop Tools - By Elvan

![Python](https://img.shields.io/badge/Python-3776AB?style=flat&logo=python&logoColor=white)
![Windows](https://img.shields.io/badge/Platform-Windows-0078d7.svg)
![ADB](https://img.shields.io/badge/Android-ADB%20&%20Fastboot-orange.svg)

**ADB Desktop Tools is a modern, fast, and sleek Windows GUI application built with Python.** It simplifies Android debugging, file transfers, and system management by wrapping complex ADB commands into an intuitive, VS Code-inspired interface.

### 📥 [Download Executable](https://github.com/yourusername/ADB-Tools-By-Elvan/releases/latest)
**No installation required. Just download the portable version and run it directly!**

<br>

### 📸 Application Screenshot
![ADB Tools Screenshot](screenshot.png)

</div>

---

## ✨ Key Features

### 💻 Advanced Integrated Terminal
*   **Native Windows Execution:** Executes commands smoothly in the background without annoying console pop-ups (`CREATE_NO_WINDOW`).
*   **Interactive ADB Shell:** Enter `adb shell` to seamlessly transition into your Android device's shell mode.
*   **Smart Device Tracking:** Real-time polling to detect if your Android device is connected or disconnected.

### 📁 Intuitive File Manager (Push/Pull)
*   **ADB Push:** Easily select local files on your PC via a native file picker and send them directly to any path on your Android device (e.g., `/sdcard/Download/`).
*   **ADB Pull:** Quickly fetch files from your Android device. Files are automatically saved to your PC's native Downloads folder for maximum convenience.

### 📺 Advanced Scrcpy Integration
*   **Seamless Switching:** Automatically terminates previous Scrcpy instances before launching a new one to prevent window clutter.
*   **Multiple Modes:** Support for Audio+Video, No Audio, Audio Only, and Screen Off (Battery Saver) modes.

---

## 🚀 Getting Started (Run from Source)

If you want to run the source code directly, follow these steps:

### Prerequisites
*   **Python:** Make sure you have Python 3.8+ installed on your PC.
*   **Android Platform Tools:** Ensure `adb` is installed and added to your Windows Environment Variables (PATH).
*   **USB Debugging:** Must be enabled on your Android device.

### Run Instructions

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/Elvandito/ADB-Tools.git
    cd ADB-Tools
    ```
2.  **Run the Python Script:**
    ```bash
    python adbtools.py
    ```
    *Note: The app uses standard Python libraries like `tkinter`, `subprocess`, and `threading`. No external modules are required to run the script!*

---

## 📦 Building the Executable (.exe)

To generate a standalone `.exe` portable file using `PyInstaller`, run the following commands in your terminal:

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/Elvandito/ADB-Tools.git
    cd ADB-Tools
    ```
2.  **Install PyInstaller:**
    ```bash
    pip install pyinstaller
    ```
3.  **Build the application:**
    ```bash
    python -m PyInstaller --noconsole --onefile --icon=app_icon.ico --add-data "app_icon.ico;." --name="ADB_Tools" adbtools.py
    ```

*Once completed, your compiled `ADB_Tools.exe` file will be waiting inside the `dist/` folder!*

---

## 🤝 Contributing

Contributions are what make the open-source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

1.  Fork the Project
2.  Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3.  Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4.  Push to the Branch (`git push origin feature/AmazingFeature`)
5.  Open a Pull Request

---

## 📜 License

Distributed under the **MIT License**. See `LICENSE` for more information.

> **Developed with ❤️ for the Android Community by Elvan.**
