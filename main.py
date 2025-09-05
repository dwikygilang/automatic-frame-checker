import os
import re
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext

class FrameCheckerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("🎬 Automatic Frame Checker")
        self.root.geometry("720x540")
        self.root.resizable(False, False)

        # --- Dark Theme Colors ---
        self.bg_main = "#2C2F33"
        self.bg_frame = "#23272A"
        self.fg_text = "#FFFFFF"
        self.entry_bg = "#99AAB5"
        self.entry_fg = "#000000"

        root.configure(bg=self.bg_main)

        # Title
        title = tk.Label(
            root,
            text="🔍 Automatic Frame Checker",
            font=("Segoe UI", 16, "bold"),
            fg=self.fg_text,
            bg=self.bg_main
        )
        title.pack(pady=10)

        # Frame for input
        input_frame = tk.Frame(root, bg=self.bg_frame)
        input_frame.pack(pady=10, padx=10, fill="x")

        tk.Label(input_frame, text="Select Render Folder:", font=("Segoe UI", 10), fg=self.fg_text, bg=self.bg_frame).pack(anchor="w", padx=5, pady=5)

        browse_frame = tk.Frame(input_frame, bg=self.bg_frame)
        browse_frame.pack(fill="x", pady=5)

        self.folder_var = tk.StringVar()
        folder_entry = tk.Entry(
            browse_frame,
            textvariable=self.folder_var,
            width=60,
            font=("Consolas", 10),
            bg=self.entry_bg,
            fg=self.entry_fg,
            insertbackground="white"
        )
        folder_entry.pack(side="left", padx=5)

        browse_btn = tk.Button(browse_frame, text="📂 Browse", command=self.browse_folder,
                               bg="#3498DB", fg="white", relief="flat")
        browse_btn.pack(side="left", padx=5)

        # Action buttons
        action_frame = tk.Frame(root, bg=self.bg_main)
        action_frame.pack(pady=10)

        check_btn = tk.Button(
            action_frame,
            text="✅ Check Frames",
            command=self.check_frames,
            bg="#2ECC71",
            fg="white",
            font=("Segoe UI", 11, "bold"),
            relief="flat",
            width=18
        )
        check_btn.pack(side="left", padx=5)

        copy_btn = tk.Button(
            action_frame,
            text="📋 Copy Missing",
            command=self.copy_to_clipboard,
            bg="#F39C12",
            fg="white",
            font=("Segoe UI", 11, "bold"),
            relief="flat",
            width=18
        )
        copy_btn.pack(side="left", padx=5)

        export_btn = tk.Button(
            action_frame,
            text="💾 Export Report",
            command=self.export_report,
            bg="#9B59B6",
            fg="white",
            font=("Segoe UI", 11, "bold"),
            relief="flat",
            width=18
        )
        export_btn.pack(side="left", padx=5)

        # Output box with scrollbar
        self.output_box = scrolledtext.ScrolledText(
            root,
            height=18,
            width=90,
            font=("Consolas", 10),
            bg="#23272A",
            fg="#FFFFFF",
            insertbackground="white"
        )
        self.output_box.pack(padx=10, pady=10)

        # Footer credit
        footer = tk.Label(
            root,
            text="Made by Dwiky  |  https://github.com/dwikygilang",
            font=("Segoe UI", 8),
            anchor="w",
            fg="#99AAB5",
            bg=self.bg_main
        )
        footer.pack(side="left", padx=10, pady=5)

        # Store last report
        self.last_report = ""

    def browse_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.folder_var.set(folder)

    def detect_prefix_and_ext(self, files):
        if not files:
            return None, None

        sample = files[0]
        match = re.match(r"(.+?)(\d+)(\.\w+)$", sample)
        if match:
            prefix, _, ext = match.groups()
            return prefix, ext
        return None, os.path.splitext(sample)[1]

    def check_frames(self):
        folder = self.folder_var.get()

        if not os.path.isdir(folder):
            messagebox.showerror("Error", "Invalid folder!")
            return

        files = sorted([f for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f))])

        if not files:
            messagebox.showerror("Error", "No files found in folder!")
            return

        prefix, ext = self.detect_prefix_and_ext(files)
        if not prefix or not ext:
            messagebox.showerror("Error", "Failed to detect prefix/file format!")
            return

        frame_numbers = []
        for f in files:
            if f.startswith(prefix) and f.endswith(ext):
                frame_str = f.replace(prefix, "").replace(ext, "")
                try:
                    frame_numbers.append(int(frame_str))
                except ValueError:
                    pass

        if not frame_numbers:
            messagebox.showerror("Error", "No frame numbers detected!")
            return

        frame_numbers = sorted(frame_numbers)
        start, end = min(frame_numbers), max(frame_numbers)
        missing = [i for i in range(start, end + 1) if i not in frame_numbers]

        # Build report
        report = []
        report.append(f"📁 Folder       : {folder}")
        report.append(f"📝 Prefix       : {prefix}")
        report.append(f"📂 File Format  : {ext}")
        report.append(f"🎞️ Frame Range  : {start} - {end}")
        report.append(f"✅ Frames Found : {len(frame_numbers)} of {end - start + 1}\n")

        if missing:
            report.append("⚠️ Missing Frames:")
            report.append(str(missing))
        else:
            report.append("🎉 All frames complete!")

        report_text = "\n".join(report)

        # Save for copy/export
        self.last_report = report_text

        # Output to box
        self.output_box.delete(1.0, tk.END)
        self.output_box.insert(tk.END, report_text)

        # Add color tags
        self.output_box.tag_config("warning", foreground="red")
        self.output_box.tag_config("success", foreground="green")
        if missing:
            self.output_box.tag_add("warning", "end-2l", "end-1l")
        else:
            self.output_box.tag_add("success", "end-1l", "end")

    def copy_to_clipboard(self):
        if not self.last_report:
            messagebox.showinfo("Info", "No report available yet. Please check frames first.")
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(self.last_report)
        messagebox.showinfo("Copied", "Report copied to clipboard!")

    def export_report(self):
        if not self.last_report:
            messagebox.showinfo("Info", "No report available yet. Please check frames first.")
            return
        filepath = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if filepath:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(self.last_report)
            messagebox.showinfo("Exported", f"Report saved to:\n{filepath}")

if __name__ == "__main__":
    root = tk.Tk()
    app = FrameCheckerApp(root)
    root.mainloop()
