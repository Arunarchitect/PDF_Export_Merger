from pathlib import Path
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pypdf import PdfWriter
import threading
import time
import traceback
import os

INKSCAPE_EXE = r"C:\Program Files\Inkscape\bin\inkscape.exe"

# ------------------------ Helper Functions ------------------------

def show_error(err):
    win = tk.Toplevel()
    win.title("Error details")
    win.geometry("850x400")
    txt = tk.Text(win, wrap="word")
    txt.pack(expand=True, fill="both")
    txt.insert("1.0", err)

def format_time(sec):
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = int(sec % 60)
    return f"{h:02}:{m:02}:{s:02}"

def format_size(bytes_size):
    for unit in ['B','KB','MB','GB']:
        if bytes_size < 1024:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024
    return f"{bytes_size:.2f} TB"

# ------------------------ SVG → PDF ------------------------

def export_svg(svg_path, out_dir, dpi):
    out_pdf = out_dir / f"{svg_path.stem}.pdf"
    cmd = [
        INKSCAPE_EXE,
        str(svg_path),
        "--export-type=pdf",
        f"--export-dpi={dpi}",
        # Text remains as text (searchable/selectable) - NO --export-text-to-path!
        "--export-pdf-version=1.5",
        f"--export-filename={out_pdf}"
    ]
    subprocess.run(cmd, check=True)
    return out_pdf

def process_svg_folder(folder_path, dpi):
    start_time = time.time()
    folder = Path(folder_path)
    svg_files = sorted(folder.glob("*.svg"))

    if not svg_files:
        raise Exception("No SVG files found in selected folder")

    pdf_dir = folder / "pdf_exports"
    pdf_dir.mkdir(exist_ok=True)

    total_steps = len(svg_files) + 1
    pdf_list = []

    for i, svg in enumerate(svg_files, 1):
        status_var.set(f"Exporting: {svg.name} ({i}/{len(svg_files)})")
        pdf_list.append(export_svg(svg, pdf_dir, dpi))
        progress_var.set((i / total_steps) * 100)
        root.update_idletasks()

    # Merge PDFs
    status_var.set("Merging PDFs...")
    writer = PdfWriter()
    for pdf in pdf_list:
        writer.append(str(pdf))

    merged_pdf = folder / "Merged_Output.pdf"
    with open(merged_pdf, "wb") as f:
        writer.write(f)

    # Show final size
    merged_size = os.path.getsize(merged_pdf)
    size_var.set(f"Final PDF size: {format_size(merged_size)}")

    progress_var.set(100)
    total_time = time.time() - start_time
    return merged_pdf, total_time, len(svg_files)

# ------------------------ GUI Actions ------------------------

def select_folder():
    folder = filedialog.askdirectory()
    if folder:
        folder_var.set(folder)
        # Auto-enable run button if folder is selected
        run_btn.config(state="normal")

def reset_gui():
    folder_var.set("")
    progress_var.set(0)
    status_var.set("Ready - Select folder and click Export")
    elapsed_var.set("Elapsed: 00:00:00")
    size_var.set("")
    run_btn.config(state="disabled")
    next_btn.config(state="disabled")

def update_timer(start_time, running_flag):
    while running_flag[0]:
        elapsed_var.set(f"Elapsed: {format_time(time.time() - start_time)}")
        time.sleep(1)

def run_task():
    running_flag = [True]
    try:
        # Get DPI value - handle invalid input
        try:
            dpi = int(dpi_var.get())
        except ValueError:
            raise Exception("Please enter a valid number for DPI")
        
        if not folder_var.get():
            raise Exception("Please select a folder")

        # Relaxed DPI validation - Inkscape can handle a wide range
        if dpi < 10 or dpi > 4800:
            # Just warn but don't block execution
            response = messagebox.askyesno(
                "Unusual DPI Value",
                f"DPI value {dpi} is outside typical range (10-4800).\n"
                f"Typical values: 72-600 DPI.\n\n"
                f"Do you want to continue anyway?"
            )
            if not response:
                return

        progress_var.set(0)
        status_var.set("Starting export...")
        elapsed_var.set("Elapsed: 00:00:00")
        size_var.set("")

        start_time = time.time()
        timer_thread = threading.Thread(target=update_timer, args=(start_time, running_flag), daemon=True)
        timer_thread.start()

        merged_pdf_path, total_time, num_files = process_svg_folder(folder_var.get(), dpi)

        running_flag[0] = False
        elapsed_var.set(f"Total Time: {format_time(total_time)}")
        status_var.set(f"Completed - {num_files} files processed")
        
        # Test if PDF is searchable by checking for text
        try:
            from pypdf import PdfReader
            reader = PdfReader(merged_pdf_path)
            text_content = ""
            for page in reader.pages:
                text_content += page.extract_text()
            
            if text_content.strip():
                searchable_status = "✅ Searchable PDF created"
                text_preview = f"\nText found: {text_content[:100]}..." if text_content else ""
            else:
                searchable_status = "⚠️ No text found (may be all images/vectors)"
                text_preview = ""
        except:
            searchable_status = "ℹ️ Could not verify text content"
            text_preview = ""
        
        messagebox.showinfo(
            "Success",
            f"✅ PDF export and merge completed!\n\n"
            f"Files processed: {num_files}\n"
            f"Output DPI: {dpi}\n"
            f"Time taken: {format_time(total_time)}\n"
            f"Output file: {merged_pdf_path}\n\n"
            f"{searchable_status}{text_preview}\n\n"
            f"Note: Text should now be searchable/selectable\n"
            f"Fonts are embedded for proper display"
        )

    except Exception as e:
        running_flag[0] = False
        err = traceback.format_exc()
        show_error(err)
        status_var.set("Error - Check details")
    finally:
        next_btn.config(state="normal")
        run_btn.config(state="disabled")

def run():
    run_btn.config(state="disabled")
    next_btn.config(state="disabled")
    threading.Thread(target=run_task, daemon=True).start()

# ---------------- GUI ----------------

root = tk.Tk()
root.title("SVG → PDF Merger (Searchable Text)")
root.geometry("650x500")

# Variables
folder_var = tk.StringVar()
dpi_var = tk.StringVar(value="300")
progress_var = tk.DoubleVar()
status_var = tk.StringVar(value="Ready - Select folder and click Export")
elapsed_var = tk.StringVar(value="Elapsed: 00:00:00")
size_var = tk.StringVar(value="")

# Title
tk.Label(root, text="SVG to PDF Converter & Merger", 
         font=("Arial", 14, "bold")).pack(pady=10)

# Important note about searchable text
note_frame = tk.Frame(root, bg="#e6f3ff", relief="ridge", bd=1)
note_frame.pack(pady=5, fill="x", padx=20)
tk.Label(note_frame, text="📝 Text will be searchable/selectable in PDF", 
         bg="#e6f3ff", font=("Arial", 9, "bold"), fg="#0066cc").pack(pady=3)

# Folder selection
tk.Button(root, text="📁 Select SVG Folder", command=select_folder, 
          width=20, height=2).pack(pady=10)
tk.Label(root, textvariable=folder_var, wraplength=550, 
         bg="#f0f0f0", relief="sunken", padx=10, pady=5).pack(pady=5, fill="x", padx=40)

# DPI setting with presets
dpi_frame = tk.LabelFrame(root, text="Export Settings", padx=10, pady=10)
dpi_frame.pack(pady=10, fill="x", padx=40)

# DPI input
tk.Label(dpi_frame, text="Export DPI:").grid(row=0, column=0, sticky="w", pady=5)
dpi_entry = tk.Entry(dpi_frame, textvariable=dpi_var, width=10)
dpi_entry.grid(row=0, column=1, sticky="w", padx=5, pady=5)

# DPI presets
presets_frame = tk.Frame(dpi_frame)
presets_frame.grid(row=1, column=0, columnspan=2, pady=5, sticky="w")

tk.Label(presets_frame, text="Presets:").pack(side="left", padx=(0, 10))

def set_dpi(value):
    dpi_var.set(value)

for text, value in [("Low (96)", "96"), ("Web (150)", "150"), 
                    ("Print (300)", "300"), ("High (600)", "600")]:
    btn = tk.Button(presets_frame, text=text, width=8,
                   command=lambda v=value: set_dpi(v))
    btn.pack(side="left", padx=2)

# Progress bar
progress = ttk.Progressbar(
    root, orient="horizontal", length=550,
    mode="determinate", variable=progress_var
)
progress.pack(pady=15)

# Status labels
tk.Label(root, textvariable=status_var, font=("Arial", 10)).pack(pady=2)
tk.Label(root, textvariable=elapsed_var, font=("Arial", 9)).pack()
tk.Label(root, textvariable=size_var, font=("Arial", 9, "bold"), 
         fg="blue").pack(pady=5)

# Control buttons frame
btn_frame = tk.Frame(root)
btn_frame.pack(pady=15)

run_btn = tk.Button(btn_frame, text="▶️ Export & Merge", width=15, 
                    height=2, command=run, bg="#4CAF50", fg="white", 
                    state="disabled")
run_btn.pack(side="left", padx=5)

next_btn = tk.Button(btn_frame, text="🔄 Next Folder", width=15, 
                     height=2, command=reset_gui, state="disabled")
next_btn.pack(side="left", padx=5)

# DPI and text guide
guide_frame = tk.LabelFrame(root, text="Settings Guide", padx=10, pady=5)
guide_frame.pack(pady=10, fill="x", padx=40)

guide_text = """DPI Settings:
• 96 DPI: Smallest size, screen viewing only
• 150 DPI: Good balance, screen + basic printing
• 300 DPI: Print quality, standard for documents
• 600 DPI: High quality, large format printing

Text Handling:
• Text remains as text (searchable/selectable)
• Fonts are embedded for proper display
• NO conversion to vector paths"""
tk.Label(guide_frame, text=guide_text, font=("Arial", 8), 
         justify="left").pack()

# Footer
tk.Label(root, text="SVG to PDF Converter v1.2 - Searchable Text Output", 
         font=("Arial", 8), fg="gray").pack(side="bottom", pady=5)

# Set focus to DPI entry
dpi_entry.focus_set()

root.mainloop()