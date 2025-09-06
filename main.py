"""
Frame Checker Pro v2
Author: Dwiky Gilang Imrodhani | https://github.com/dwikygilang
Features:
 - Modern responsive UI using customtkinter
 - 3-panel layout: Sidebar | Report | Preview + Charts (Notebook)
 - Thumbnail preview (first / middle / last) + slideshow controls
 - Chart tab (bar) and Heatmap tab
 - Theme toggle (dark/light) saved per session
 - Multi-folder batch check, compare 2 folders, export report/chart
 - Export HTML report (embedded chart image)
 - Desktop notification on missing frames (uses plyer if available)
 - Sound alert on missing frames (winsound or playsound if available)
Requirements:
 pip install customtkinter pillow matplotlib pandas openpyxl numpy plyer
 optional sound: pip install playsound
"""

import os
import re
import threading
import time
import base64
import io
import json
from datetime import datetime
from math import ceil

import customtkinter as ctk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import pandas as pd
import numpy as np

# Optional libs
try:
    from plyer import notification as plyer_notification
except Exception:
    plyer_notification = None

try:
    import winsound
except Exception:
    winsound = None

try:
    from playsound import playsound
except Exception:
    playsound = None

# -----------------------
# CONFIG
# -----------------------
APP_TITLE = "Frame Checker Pro v2"
VERSION = "v2.0"
PREVIEW_MAX_SIZE = (640, 360)
AUTO_REFRESH_INTERVAL = 5
SUPPORTED_IMAGE_FORMATS = (".exr", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp")
SETTINGS_FILE = "frame_checker_settings.json"

# -----------------------
# UTIL
# -----------------------
def detect_prefix_and_ext(files):
    if not files: return None, None
    sample = files[0]
    m = re.match(r"(.+?)(\d+)(\.\w+)$", sample)
    if m:
        return m.group(1), m.group(3)
    return None, os.path.splitext(sample)[1]

def summarize_missing_blocks(missing):
    if not missing: return []
    blocks = []
    start = prev = missing[0]
    for n in missing[1:]:
        if n == prev + 1:
            prev = n
        else:
            blocks.append(str(start) if start == prev else f"{start}-{prev}")
            start = prev = n
    blocks.append(str(start) if start == prev else f"{start}-{prev}")
    return blocks

def load_settings():
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"appearance":"dark"}

def save_settings(d):
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(d, f)
    except:
        pass

# -----------------------
# APP
# -----------------------
class FrameCheckerPro(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.settings = load_settings()
        ctk.set_appearance_mode(self.settings.get("appearance","dark"))
        ctk.set_default_color_theme("dark-blue")
        self.title(f"{APP_TITLE} - {VERSION}")
        self.geometry("1350x860")
        self.minsize(1000, 640)

        # state
        self.selected_folders = []
        self.last_report_text = ""
        self.stop_auto_refresh = threading.Event()
        self.slideshow_playing = False
        self.slideshow_after_id = None

        # build ui
        self._build_ui()
        self._bind_shortcuts()

    # -----------------------
    # UI BUILD
    # -----------------------
    def _build_ui(self):
        # toolbar
        toolbar = ctk.CTkFrame(self, corner_radius=0)
        toolbar.grid(row=0, column=0, sticky="ew")
        toolbar.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(toolbar, text=APP_TITLE, font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, sticky="w", padx=12, pady=8)
        self.theme_var = ctk.StringVar(value=self.settings.get("appearance","dark"))
        theme_switch = ctk.CTkOptionMenu(toolbar, values=["dark","light"], variable=self.theme_var, command=self._on_theme_change)
        theme_switch.grid(row=0, column=2, padx=12, sticky="e")
        ctk.CTkLabel(toolbar, text=f"{VERSION}", fg_color=None).grid(row=0, column=3, padx=(0,12), sticky="e")

        # main layout
        main = ctk.CTkFrame(self)
        main.grid(row=1, column=0, sticky="nsew", padx=10, pady=(6,8))
        self.grid_rowconfigure(1, weight=1); self.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(0, weight=1)
        main.grid_columnconfigure(1, weight=1)  # center
        main.grid_columnconfigure(2, weight=0)  # right

        # left sidebar
        sidebar = ctk.CTkFrame(main, width=320, corner_radius=8)
        sidebar.grid(row=0, column=0, sticky="nsew", padx=(0,8), pady=0)
        sidebar.grid_rowconfigure(14, weight=1)

        ctk.CTkLabel(sidebar, text="Folders (Batch)", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, padx=12, pady=(12,6), sticky="w")
        ctk.CTkButton(sidebar, text="➕ Add Folder", corner_radius=12, command=self._add_folder).grid(row=1, column=0, padx=12, pady=6, sticky="ew")
        ctk.CTkButton(sidebar, text="🗑 Remove Selected", corner_radius=12, fg_color="#ff6b6b", hover_color="#ff8b8b", command=self._remove_selected).grid(row=2, column=0, padx=12, pady=6, sticky="ew")
        ctk.CTkButton(sidebar, text="✅ Check Selected", corner_radius=12, fg_color="#2ecc71", hover_color="#44d17a", command=self._run_check_selected).grid(row=3, column=0, padx=12, pady=6, sticky="ew")
        ctk.CTkButton(sidebar, text="🔍 Compare 2 Selected", corner_radius=12, command=self._compare_two_selected).grid(row=4, column=0, padx=12, pady=6, sticky="ew")

        ttk.Separator(sidebar, orient="horizontal").grid(row=5, column=0, padx=12, pady=(8,8), sticky="ew")

        ctk.CTkLabel(sidebar, text="Settings", font=ctk.CTkFont(size=12, weight="bold")).grid(row=6, column=0, padx=12, pady=(0,6), sticky="w")
        self.var_auto_detect = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(sidebar, text="Auto-detect prefix & ext", variable=self.var_auto_detect).grid(row=7, column=0, padx=12, pady=4, sticky="w")
        ctk.CTkLabel(sidebar, text="Allowed formats (comma):").grid(row=8, column=0, padx=12, pady=(6,0), sticky="w")
        self.var_formats = ctk.StringVar(value="png,exr,jpg")
        ctk.CTkEntry(sidebar, textvariable=self.var_formats).grid(row=9, column=0, padx=12, pady=(4,8), sticky="ew")

        self.var_auto_refresh = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(sidebar, text="Auto-refresh (watch all)", variable=self.var_auto_refresh, command=self._toggle_auto_refresh).grid(row=10, column=0, padx=12, pady=6, sticky="w")
        ctk.CTkLabel(sidebar, text="Auto-refresh interval (s):").grid(row=11, column=0, padx=12, pady=(6,2), sticky="w")
        self.var_refresh_interval = ctk.IntVar(value=AUTO_REFRESH_INTERVAL)
        ctk.CTkEntry(sidebar, textvariable=self.var_refresh_interval).grid(row=12, column=0, padx=12, pady=(2,8), sticky="ew")

        # tree
        self.tree = ttk.Treeview(sidebar, columns=("path","status"), show="headings", height=8)
        self.tree.heading("path", text="Folder")
        self.tree.heading("status", text="Status")
        self.tree.column("path", width=240)
        self.tree.column("status", width=90, anchor="center")
        self.tree.grid(row=13, column=0, padx=12, pady=(6,12), sticky="nsew")

        # center
        center = ctk.CTkFrame(main, corner_radius=8)
        center.grid(row=0, column=1, sticky="nsew", padx=(0,8), pady=0)
        center.grid_rowconfigure(2, weight=1); center.grid_columnconfigure(0, weight=1)

        # top actions
        top_actions = ctk.CTkFrame(center)
        top_actions.grid(row=0, column=0, sticky="ew", padx=12, pady=(8,6))
        top_actions.grid_columnconfigure(6, weight=1)
        ctk.CTkButton(top_actions, text="📋 Copy (Ctrl+C)", corner_radius=10, command=self._copy_report).grid(row=0, column=0, padx=6)
        ctk.CTkButton(top_actions, text="💾 Export (TXT/CSV/XLSX)", corner_radius=10, command=self._export_report).grid(row=0, column=1, padx=6)
        ctk.CTkButton(top_actions, text="🌐 Export HTML", corner_radius=10, command=self._export_report_html).grid(row=0, column=2, padx=6)
        ctk.CTkButton(top_actions, text="🖼 Export Chart PNG", corner_radius=10, command=self._export_chart_png).grid(row=0, column=3, padx=6)
        ctk.CTkButton(top_actions, text="🔁 Refresh", corner_radius=10, command=self._run_check_selected).grid(row=0, column=4, padx=6)
        ctk.CTkLabel(top_actions, text="Select two folders to Compare").grid(row=0, column=5, padx=10)

        # report
        ctk.CTkLabel(center, text="📑 Report", font=ctk.CTkFont(size=14, weight="bold")).grid(row=1, column=0, sticky="nw", padx=12, pady=(6,0))
        self.txt_report = ctk.CTkTextbox(center, wrap="word")
        self.txt_report.grid(row=2, column=0, sticky="nsew", padx=12, pady=(4,12))

        # right: preview + charts
        right = ctk.CTkFrame(main, width=480, corner_radius=8)
        right.grid(row=0, column=2, sticky="nsew", pady=0)
        right.grid_rowconfigure(4, weight=1); right.grid_columnconfigure(0, weight=1)

        # preview controls
        preview_top = ctk.CTkFrame(right)
        preview_top.grid(row=0, column=0, sticky="ew", padx=12, pady=(12,6))
        preview_top.grid_columnconfigure(4, weight=1)
        self.btn_prev = ctk.CTkButton(preview_top, text="◀", width=40, corner_radius=10, command=self._preview_prev)
        self.btn_prev.grid(row=0, column=0, padx=(0,6))
        self.btn_play = ctk.CTkButton(preview_top, text="▶ Play", width=80, corner_radius=10, command=self._toggle_slideshow)
        self.btn_play.grid(row=0, column=1, padx=(0,6))
        self.btn_next = ctk.CTkButton(preview_top, text="▶", width=40, corner_radius=10, command=self._preview_next)
        self.btn_next.grid(row=0, column=2, padx=(0,6))
        ctk.CTkLabel(preview_top, text="FPS:").grid(row=0, column=3, padx=(6,2))
        self.var_fps = ctk.IntVar(value=6)
        ctk.CTkEntry(preview_top, textvariable=self.var_fps, width=50).grid(row=0, column=4, sticky="e")

        # preview display
        self.preview_frame = ctk.CTkFrame(right, fg_color=("transparent"))
        self.preview_frame.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0,8))
        self.preview_frame.grid_rowconfigure(0, weight=1)
        self.preview_frame.grid_columnconfigure(0, weight=1)
        self.preview_label = ctk.CTkLabel(self.preview_frame, text="No preview")
        self.preview_label.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

        # thumbnails
        thumbs = ctk.CTkFrame(right)
        thumbs.grid(row=2, column=0, sticky="ew", padx=12, pady=(0,8))
        self.thumb_labels = []
        for i, txt in enumerate(["First","Middle","Last"]):
            lbl = ctk.CTkLabel(thumbs, text=txt, width=140, height=96, anchor="center", fg_color=("#222222","#111111"))
            lbl.grid(row=0, column=i, padx=6, pady=4)
            self.thumb_labels.append(lbl)

        # notebook for chart + heatmap
        tab_parent = ttk.Notebook(right)
        tab_parent.grid(row=3, column=0, sticky="nsew", padx=12, pady=(0,12))
        tab_chart = ttk.Frame(tab_parent)
        tab_heat = ttk.Frame(tab_parent)
        tab_parent.add(tab_chart, text="Chart")
        tab_parent.add(tab_heat, text="Heatmap")

        self.fig_chart, self.ax_chart = plt.subplots(figsize=(6,2.6), dpi=100)
        self.fig_chart.patch.set_facecolor("#1b1b1b")
        self.canvas_chart = FigureCanvasTkAgg(self.fig_chart, master=tab_chart)
        self.canvas_chart.get_tk_widget().pack(fill="both", expand=True, padx=6, pady=6)

        self.fig_heat, self.ax_heat = plt.subplots(figsize=(6,1.6), dpi=100)
        self.fig_heat.patch.set_facecolor("#1b1b1b")
        self.canvas_heat = FigureCanvasTkAgg(self.fig_heat, master=tab_heat)
        self.canvas_heat.get_tk_widget().pack(fill="both", expand=True, padx=6, pady=6)

        # status bar
        status = ctk.CTkFrame(self, corner_radius=0)
        status.grid(row=2, column=0, sticky="ew", padx=10, pady=(0,8))
        status.grid_columnconfigure(1, weight=1)
        self.status_label = ctk.CTkLabel(status, text="Idle", anchor="w")
        self.status_label.grid(row=0, column=0, padx=8, pady=6, sticky="w")
        self.info_label = ctk.CTkLabel(status, text=f"{VERSION} • by https://github.com/dwikygilang", anchor="e")
        self.info_label.grid(row=0, column=1, padx=8, pady=6, sticky="e")

    # -----------------------
    # SHORTCUTS
    # -----------------------
    def _bind_shortcuts(self):
        self.bind_all("<Control-e>", lambda e: self._export_report())
        self.bind_all("<Control-c>", lambda e: self._copy_report())
        self.bind_all("<Control-r>", lambda e: self._run_check_selected())

    # -----------------------
    # Folder management
    # -----------------------
    def _add_folder(self):
        folder = filedialog.askdirectory(title="Select render folder")
        if not folder: return
        if any(d['path']==folder for d in self.selected_folders):
            messagebox.showinfo("Info","Folder already added.")
            return
        entry = {"path":folder,"prefix":None,"ext":None,"frames":[],"missing":[],"last_checked":None}
        self.selected_folders.append(entry)
        self._refresh_tree()
        self._set_status(f"Added: {os.path.basename(folder)}")

    def _remove_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Info","Select a folder first.")
            return
        for iid in sorted(sel, reverse=True):
            idx = int(iid)
            if 0 <= idx < len(self.selected_folders):
                self.selected_folders.pop(idx)
        self._refresh_tree()
        self._clear_report()

    def _refresh_tree(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        for i,d in enumerate(self.selected_folders):
            status = d.get("status","Idle")
            self.tree.insert("", "end", iid=str(i), values=(d["path"], status))

    # -----------------------
    # Checking logic (threaded)
    # -----------------------
    def _run_check_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Info","Select folder(s) to check.")
            return
        t = threading.Thread(target=self._worker_check, args=(sel,), daemon=True)
        t.start()

    def _worker_check(self, selection):
        self._set_status("Checking...")
        for iid in selection:
            try:
                idx = int(iid)
            except:
                continue
            if idx < 0 or idx >= len(self.selected_folders): continue
            slot = self.selected_folders[idx]
            slot["status"] = "Checking"
            self._refresh_tree()
            self._check_folder(slot)
            slot["last_checked"] = datetime.now()
            slot["status"] = "Done" if not slot["missing"] else f"Missing {len(slot['missing'])}"
            self._refresh_tree()
            self._render_report_for(slot)
            # if missing -> notify & sound
            if slot.get("missing"):
                self._notify_missing(slot)
        self._set_status("Idle")

    def _check_folder(self, slot):
        folder = slot["path"]
        try:
            all_files = sorted([f for f in os.listdir(folder) if os.path.isfile(os.path.join(folder,f))])
        except:
            slot["frames"]=[]; slot["missing"]=[]; slot["prefix"]=None; slot["ext"]=None; return
        allowed = [s.strip().lower() for s in self.var_formats.get().split(",") if s.strip()]
        if allowed:
            files = [f for f in all_files if os.path.splitext(f)[1].lstrip(".").lower() in allowed]
        else:
            files = [f for f in all_files if os.path.splitext(f)[1].lower() in SUPPORTED_IMAGE_FORMATS]
        if not files:
            slot["frames"]=[]; slot["missing"]=[]; slot["prefix"]=None; slot["ext"]=None; return
        if self.var_auto_detect.get():
            prefix, ext = detect_prefix_and_ext(files)
        else:
            prefix, ext = None, os.path.splitext(files[0])[1]
        nums=[]
        for f in files:
            if prefix and ext and f.startswith(prefix) and f.endswith(ext):
                body = f[len(prefix):-len(ext)]
                try: nums.append(int(body))
                except: pass
            else:
                m = re.search(r"(\d+)(\.\w+)$", f)
                if m:
                    try: nums.append(int(m.group(1)))
                    except: pass
        if not nums:
            slot["frames"]=[]; slot["missing"]=[]; slot["prefix"]=prefix; slot["ext"]=ext; return
        nums = sorted(set(nums))
        start,end = nums[0], nums[-1]
        full = set(range(start,end+1))
        missing = sorted(list(full - set(nums)))
        slot["frames"]=nums; slot["missing"]=missing; slot["prefix"]=prefix; slot["ext"]=ext

    # -----------------------
    # Report / preview / charts
    # -----------------------
    def _render_report_for(self, slot):
        folder = slot["path"]
        frames = slot.get("frames", [])
        missing = slot.get("missing", [])
        start = frames[0] if frames else 0
        end = frames[-1] if frames else 0
        total = end - start + 1 if frames else 0
        completeness = f"{(len(frames) / total * 100):.2f}%" if total else "0%"

        lines = []
        lines.append("Render Check Summary\n")
        lines.append(f"- *📁 Folder*:\n `{folder}`\n")
        lines.append(f"- *🔤 Prefix*: `{slot.get('prefix')}`")
        lines.append(f"- *📄 Extension*: `{slot.get('ext')}`")
        lines.append(f"- *🎞️ Frame Range*: `{start} - {end}`")
        lines.append(f"- *✅ Frames Found*: `{len(frames)} / {total}` ({completeness})")
        lines.append(f"- *❌ Missing Frames*: `{len(missing)}`")

        if missing:
            blocks = summarize_missing_blocks(missing)
            lines.append(f"- *🧩 Missing Blocks*:\n `{', '.join(blocks)}`\n")
            if len(missing) > 200:
                lines.append(f"- *📋 Missing List (first 200)*:\n `{', '.join(map(str, missing[:200]))} ... total {len(missing)}`\n")
            else:
                lines.append(f"- *📋 Missing List*:\n `{', '.join(map(str, missing))}`\n")
        else:
            lines.append("- *All frames complete ✅*\n")

        lines.append(f"- *🕒 Last Checked*:\n `{slot.get('last_checked')}`")

        report_text = "\n".join(lines)
        self.last_report_text = report_text

        self.txt_report.delete("0.0", "end")
        self.txt_report.insert("0.0", report_text)

        self._set_status(f"{len(frames)} frames found • {len(missing)} missing")

        # preview + charts
        self._load_thumbnails(slot)
        self._update_chart(slot)
        self._update_heatmap(slot)


    def _clear_report(self):
        self.txt_report.delete("0.0","end"); self.last_report_text=""
        self.preview_label.configure(image="", text="No preview")
        for lbl in self.thumb_labels: lbl.configure(image="", text="")

    # -----------------------
    # Thumbnails & Preview
    # -----------------------
    def _load_thumbnails(self, slot):
        frames = slot.get("frames",[])
        folder = slot["path"]
        if not frames:
            for lbl in self.thumb_labels:
                lbl.configure(image="", text="No preview"); lbl.image=None
            self.preview_label.configure(image="", text="No preview"); self.preview_label.image=None
            return
        picks = [0, len(frames)//2, len(frames)-1]
        imgs=[]
        for idx in picks:
            frame_num = frames[idx]
            found = None
            for f in os.listdir(folder):
                m = re.search(r"(\d+)(\.\w+)$", f)
                if m:
                    try:
                        if int(m.group(1)) == frame_num:
                            found = os.path.join(folder, f); break
                    except: pass
            if not found:
                imgs.append(None); continue
            try:
                im = Image.open(found); im.thumbnail((160,90), Image.ANTIALIAS)
                tk = ImageTk.PhotoImage(im); imgs.append((tk, os.path.basename(found), frame_num))
            except:
                imgs.append(None)
        for i, val in enumerate(imgs):
            lbl = self.thumb_labels[i]
            if val:
                tk, name, fnum = val
                lbl.configure(image=tk, text=f"{name}\n({fnum})"); lbl.image = tk
            else:
                lbl.configure(image="", text="No preview"); lbl.image=None
        # main preview = middle if exists
        mid = imgs[1]
        if mid:
            self.preview_label.configure(image=mid[0], text=""); self.preview_label.image=mid[0]
        else:
            self.preview_label.configure(image="", text="No preview"); self.preview_label.image=None
        slot["_preview_idx"] = len(frames)//2
        self._current_preview_slot = slot

    def _preview_prev(self):
        slot = getattr(self, "_current_preview_slot", None)
        if not slot: return
        idx = slot.get("_preview_idx",0)-1
        if idx < 0: idx = 0
        slot["_preview_idx"] = idx; self._preview_update(slot)

    def _preview_next(self):
        slot = getattr(self, "_current_preview_slot", None)
        if not slot: return
        idx = slot.get("_preview_idx",0)+1
        if idx >= len(slot.get("frames",[])): idx = len(slot.get("frames",[]))-1
        slot["_preview_idx"] = idx; self._preview_update(slot)

    def _preview_update(self, slot):
        idx = slot.get("_preview_idx",0)
        frames = slot.get("frames",[])
        if not frames or idx<0 or idx>=len(frames): return
        frame_num = frames[idx]; folder = slot["path"]
        found=None
        for f in os.listdir(folder):
            m = re.search(r"(\d+)(\.\w+)$", f)
            if m:
                try:
                    if int(m.group(1))==frame_num:
                        found=os.path.join(folder,f); break
                except: pass
        if not found:
            self.preview_label.configure(image="", text="No preview"); self.preview_label.image=None; return
        try:
            im=Image.open(found); im.thumbnail(PREVIEW_MAX_SIZE, Image.ANTIALIAS)
            tk=ImageTk.PhotoImage(im)
            self.preview_label.configure(image=tk, text=""); self.preview_label.image=tk
            self._current_preview_slot = slot
        except:
            pass

    # -----------------------
    # Slideshow
    # -----------------------
    def _toggle_slideshow(self):
        if not getattr(self, "_current_preview_slot", None):
            messagebox.showinfo("Info","No preview loaded.")
            return
        if self.slideshow_playing:
            self.slideshow_playing=False; self.btn_play.configure(text="▶ Play")
            if self.slideshow_after_id: self.after_cancel(self.slideshow_after_id); self.slideshow_after_id=None
        else:
            try: fps = max(1, int(self.var_fps.get()))
            except: fps = 6
            self.slideshow_playing=True; self.btn_play.configure(text="⏸ Pause")
            self._slideshow_step(int(1000/fps))

    def _slideshow_step(self, delay_ms):
        if not self.slideshow_playing: return
        self._preview_next()
        self.slideshow_after_id = self.after(delay_ms, lambda: self._slideshow_step(delay_ms))

    # -----------------------
    # Chart & Heatmap
    # -----------------------
    def _update_chart(self, slot):
        frames = slot.get("frames",[])
        missing = set(slot.get("missing",[]))
        self.ax_chart = self.fig_chart.axes[0] if self.fig_chart.axes else self.fig_chart.add_subplot(111)
        if not frames:
            self.ax_chart.clear(); self.canvas_chart.draw(); return
        start,end = frames[0],frames[-1]
        x=list(range(start,end+1)); y=[1 if n in frames else 0 for n in x]
        colors=["#2ecc71" if n in frames else "red" for n in x]
        self.ax_chart.clear()
        self.ax_chart.bar(x,y,color=colors,width=1.0)
        pct = (len(frames)/(end-start+1))*100 if end-start+1>0 else 0
        self.ax_chart.set_ylim(0,1.2); self.ax_chart.set_yticks([]); self.ax_chart.set_xlabel("Frame")
        self.ax_chart.set_title(f"Completeness: {pct:.2f}%")
        self.fig_chart.tight_layout(); self.canvas_chart.draw()

    def _update_heatmap(self, slot):
        frames = slot.get("frames",[])
        missing = set(slot.get("missing",[]))
        self.ax_heat = self.fig_heat.axes[0] if self.fig_heat.axes else self.fig_heat.add_subplot(111)
        self.ax_heat.clear()
        if not frames:
            self.canvas_heat.draw(); return
        start,end = frames[0],frames[-1]
        total = end - start + 1
        data = np.zeros(total, dtype=int)
        for f in frames:
            if start <= f <= end:
                data[f - start] = 1

        cols = 100  
        rows = ceil(total / cols)
        grid = np.zeros((rows, cols))
        for i in range(total):
            r, c = divmod(i, cols)
            grid[r, c] = data[i]

        self.ax_heat.imshow(grid, cmap="Greens", aspect="auto", interpolation="nearest")
        self.ax_heat.set_title("Heatmap (green=present, black=missing)")
        self.ax_heat.axis("off")
        self.canvas_heat.draw()


    # -----------------------
    # Export / Copy
    # -----------------------
    def _copy_report(self):
        if not self.last_report_text:
            messagebox.showinfo("Info","No report to copy.")
            return
        self.clipboard_clear(); self.clipboard_append(self.last_report_text)
        self._set_status("Report copied to clipboard")

    def _export_report(self):
        if not self.last_report_text:
            messagebox.showinfo("Info","No report to export.")
            return
        fpath = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text","*.txt"),("CSV","*.csv"),("Excel","*.xlsx")])
        if not fpath: return
        try:
            if fpath.lower().endswith(".txt"):
                with open(fpath,"w",encoding="utf-8") as f: f.write(self.last_report_text)
            elif fpath.lower().endswith(".csv"):
                lines=[ln for ln in self.last_report_text.splitlines() if ln.strip()]
                pairs=[ln.split(":",1) if ":" in ln else (ln,"") for ln in lines]
                pd.DataFrame(pairs, columns=["key","value"]).to_csv(fpath,index=False)
            elif fpath.lower().endswith(".xlsx"):
                lines=[ln for ln in self.last_report_text.splitlines() if ln.strip()]
                pairs=[ln.split(":",1) if ":" in ln else (ln,"") for ln in lines]
                pd.DataFrame(pairs, columns=["key","value"]).to_excel(fpath,index=False,engine="openpyxl")
            else:
                with open(fpath,"w",encoding="utf-8") as f: f.write(self.last_report_text)
            self._set_status(f"Exported: {fpath}"); messagebox.showinfo("Export","Saved.")
        except Exception as e:
            messagebox.showerror("Error", f"Export failed: {e}")

    def _export_chart_png(self):
        path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG","*.png")])
        if not path: return
        try:
            self.fig_chart.savefig(path, dpi=150, bbox_inches="tight", facecolor=self.fig_chart.get_facecolor())
            messagebox.showinfo("Saved", f"Chart saved: {path}")
        except Exception as e:
            messagebox.showerror("Error", f"Save failed: {e}")

    def _export_report_html(self):
        # Export HTML: embed current report text + embedded chart PNG (current fig_chart)
        if not self.last_report_text:
            messagebox.showinfo("Info","No report to export.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".html", filetypes=[("HTML","*.html")])
        if not path: return
        try:
            # render chart to PNG bytes
            buf = io.BytesIO()
            self.fig_chart.savefig(buf, format="png", dpi=150, bbox_inches="tight", facecolor=self.fig_chart.get_facecolor())
            buf.seek(0)
            b64 = base64.b64encode(buf.read()).decode("ascii")
            html = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Frame Checker Report</title>
<style>body{{background:#111;color:#eee;font-family:Segoe UI,Arial}}pre{{white-space:pre-wrap}}</style></head>
<body><h2>Frame Checker Report</h2><h4>{datetime.now().isoformat()}</h4>
<pre>{self.last_report_text}</pre><h3>Chart</h3>
<img src="data:image/png;base64,{b64}" style="max-width:100%;height:auto"/>
</body></html>"""
            with open(path,"w",encoding="utf-8") as f: f.write(html)
            messagebox.showinfo("Saved", f"HTML report saved: {path}")
            self._set_status(f"Exported HTML: {path}")
        except Exception as e:
            messagebox.showerror("Error", f"Export HTML failed: {e}")

    # -----------------------
    # Compare 2 selected
    # -----------------------
    def _compare_two_selected(self):
        sel = self.tree.selection()
        if not sel or len(sel) != 2:
            messagebox.showinfo("Info","Select exactly two folders to compare (Ctrl+click)."); return
        idx1, idx2 = int(sel[0]), int(sel[1])
        a = self.selected_folders[idx1]; b = self.selected_folders[idx2]
        if not a.get("frames"): self._check_folder(a)
        if not b.get("frames"): self._check_folder(b)
        a_frames=set(a.get("frames",[])); b_frames=set(b.get("frames",[]))
        only_a=sorted(list(a_frames-b_frames)); only_b=sorted(list(b_frames-a_frames)); both=sorted(list(a_frames&b_frames))
        lines=[]
        lines.append(f"Compare A: {a['path']}")
        lines.append(f"Compare B: {b['path']}\n")
        lines.append(f"A frames: {len(a_frames)} | B frames: {len(b_frames)} | Common: {len(both)}")
        lines.append(f"Only in A (count {len(only_a)}): {', '.join(map(str,only_a[:200]))}{' ...' if len(only_a)>200 else ''}")
        lines.append(f"Only in B (count {len(only_b)}): {', '.join(map(str,only_b[:200]))}{' ...' if len(only_b)>200 else ''}")
        rep="\n".join(lines); self.txt_report.delete("0.0","end"); self.txt_report.insert("0.0",rep); self.last_report_text=rep
        self._set_status(f"Compared: A({len(a_frames)}) vs B({len(b_frames)})")

    # -----------------------
    # Auto-refresh (watch)
    # -----------------------
    def _toggle_auto_refresh(self):
        val = self.var_auto_refresh.get()
        if val:
            self.stop_auto_refresh.clear()
            t = threading.Thread(target=self._auto_refresh_loop, daemon=True); t.start()
            self._set_status("Auto-refresh enabled")
        else:
            self.stop_auto_refresh.set(); self._set_status("Auto-refresh disabled")

    def _auto_refresh_loop(self):
        while not self.stop_auto_refresh.is_set():
            if self.selected_folders:
                iids=[str(i) for i in range(len(self.selected_folders))]
                self._worker_check(iids)
            interval = max(1, int(self.var_refresh_interval.get()))
            for _ in range(interval):
                if self.stop_auto_refresh.is_set(): break
                time.sleep(1)

    # -----------------------
    # Notifications & Sound
    # -----------------------
    def _notify_missing(self, slot):
        title = "Frame Checker - Missing Frames"
        msg = f"{os.path.basename(slot['path'])} • {len(slot.get('missing',[]))} missing"
        # plyer
        try:
            if plyer_notification:
                plyer_notification.notify(title=title, message=msg, app_name=APP_TITLE, timeout=6)
        except:
            pass
        # sound: winsound beep on Windows
        try:
            if winsound:
                winsound.Beep(1000, 300)
            elif playsound:
                # playsystem beep if installed - this expects a file path; skip if none
                pass
        except:
            pass

    # -----------------------
    # Helpers
    # -----------------------
    def _set_status(self, text):
        try:
            self.status_label.configure(text=text)
        except: pass

    def _on_theme_change(self, mode):
        try:
            ctk.set_appearance_mode(mode)
            self.settings["appearance"]=mode; save_settings(self.settings)
            self._set_status(f"Theme: {mode}")
        except:
            pass

# -----------------------
# Run
# -----------------------
if __name__ == "__main__":
    app = FrameCheckerPro()
    app.mainloop()
