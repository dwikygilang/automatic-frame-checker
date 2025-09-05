# Automatic Frame Checker
A simple Python GUI tool (Tkinter-based) to automatically check missing frames in render output folders. It detects the frame prefix and file extension, scans the folder, and generates a detailed report with frame range, missing frames, and export/copy options.

## ✨ Features
- Dark-themed Tkinter GUI  
- Auto-detect prefix & extension from render sequence  
- Detect missing frames in a range  
- Export report to `.txt` file  
- Copy report to clipboard  

## 📦 Dependencies

- Python 3.10 or newer
- Tkinter (usually comes pre-installed with Python)
  - Windows/Mac: included by default
  - Linux: install manually → `sudo apt-get install python3-tk`
- Git (for cloning the repository)

## ⚡ Quick Start

```bash
# Clone the repository
git clone https://github.com/dwikygilang/automatic-frame-checker.git
cd automatic-frame-checker

# (Optional) Create virtual environment
python -m venv venv
source venv/bin/activate  # On Linux/Mac
venv\Scripts\activate     # On Windows

# Run the app
python main.py
```

## 🖼️ Screenshots

### Main Interface
<img width="716" height="566" alt="image" src="https://github.com/user-attachments/assets/b4d58edb-0d52-4720-86e5-e9081a1a9d23" />

### Example Report with Missing Frames
<img width="718" height="570" alt="image" src="https://github.com/user-attachments/assets/d9f57f71-a10f-4bf7-a680-80b0e1da8d94" />

### Example Report without Missing Frames
<img width="716" height="566" alt="image" src="https://github.com/user-attachments/assets/0f8eb19c-4ce3-4502-aae1-c477deeaa379" />


