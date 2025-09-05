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
