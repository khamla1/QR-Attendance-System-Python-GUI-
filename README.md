# 📋 Cobalt-Zenith Attendance System (ລະບົບເຊັກຊື່ QR Code)

A modern, Python-based School Attendance System built with **Tkinter**. This application allows teachers to scan student QR codes to record attendance, view history, analyze statistics, and export reports. The interface is localized for **Lao language** support.

---

## ✨ Features (ຟີເຈີຫຼັກ)

### 👨‍🎓 Student Mode (ໂຫມດນັກຮຽນ)
*   **QR Generator**: Students input their ID and Name to generate a personal QR Code.
*   **Save/Show**: The QR Code can be displayed on mobile to be scanned by the teacher.

### 🎓 Teacher Mode (ໂຫມດອາຈານ)
*   **Class Session Management**: Select Subject (Dropdown with Add/+ and Delete/- buttons) and Room Number.
*   **QR Scanner (Webcam)**: Real-time scanning using the computer's webcam.
*   **Image Upload Scan**: Option to upload a QR code image file for scanning.
*   **Instant Feedback**: Visual and audio-style status updates (Success/Duplicate/Error).

### 📊 Attendance History (ປະຫວັດ & ລາຍງານ)
*   **Daily Log**: View attendance records for the current day.
*   **Filtering**: Filter history by **Subject** to see specific class attendance.
*   **Data Management**: option to **Delete** specific records.
*   **Export to Excel**: One-click export of attendance data to `.xlsx` files using Pandas.

### 📈 Statistics (ສະຖິຕິ)
*   **Visual Graphs**: Bar charts showing attendance counts per student for each subject.
*   **Analytics**: Quickly identify top-attending students.

### 🇱🇦 Localization
*   **Lao Language**: Full UI support for Lao text (using `DokChampa` font).
*   **Modern UI**: Dark-themed, clean interface using `ttk` styling.

---

## 🛠️ Tech Stack & Dependencies

The project is built using **Python 3.12+** and the following powerful libraries:

| Library | Purpose |
| :--- | :--- |
| **tkinter** | Built-in GUI framework (Modernized with `ttk`). |
| **opencv-python** | Accessing webcam and processing video frames. |
| **pyzbar** | Decoding QR codes from images and video streams. |
| **qrcode[pil]** | Generating QR codes for students. |
| **Pillow** | Image manipulation for GUI display. |
| **matplotlib** | Rendering bar charts and statistics graphs. |
| **pandas** | Data handling and exporting to Excel. |
| **openpyxl** | Engine for writing `.xlsx` files. |
| **sqlite3** | Built-in database for storing records. |

---

## 🚀 Installation & Setup

1.  **Clone the Repository**
    ```bash
    git clone https://github.com/yourusername/cobalt-zenith.git
    cd cobalt-zenith
    ```

2.  **Install Dependencies**
    Ensure you have Python installed. Then run:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Run the Application**
    ```bash
    python main.py
    ```

---

## 📁 Project Structure

*   `main.py`: The core application entry point. Contains all GUI logic, camera handling, and event loops.
*   `backend.py`: Handles SQLite database operations (CRUD) and core business logic.
*   `requirements.txt`: List of all Python packages required.
*   `attendance.db`: (Auto-generated) SQLite database file storing subjects and check-in records.

---

## 📝 Usage Guide

1.  **First Time Setup**:
    *   Open **Teacher Mode**.
    *   Click the `+` button next to "Subject" to add your subjects (e.g., Math, Science).
2.  **Student Registration**:
    *   Go to **Student Mode**.
    *   Enter ID and Name -> Click "Generate QR".
    *   Save or take a photo of this QR.
3.  **Taking Attendance**:
    *   Teacher selects Subject and Room.
    *   Click **Start Scan** (Camera) or **Upload QR**.
    *   Scan student QRs.
4.  **Reporting**:
    *   Go to **History** to view today's list.
    *   Use the Filter dropdown to see specific classes.
    *   Click **Export Excel** to save the report.

---

**Note**: This application is optimized for Windows and uses the `DokChampa` font for Lao language rendering.
