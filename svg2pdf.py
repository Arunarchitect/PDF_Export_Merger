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

def export_svg_to_png_then_pdf(svg_path, out_dir, dpi):
    """
    Export SVG to PNG first (rasterizes everything), then convert PNG to PDF
    This actually reduces file size for complex vector graphics
    """
    # Export to PNG first (rasterizes at specified DPI)
    png_file = out_dir / f"{svg_path.stem}.png"
    cmd_png = [
        INKSCAPE_EXE,
        str(svg_path),
        "--export-type=png",
        f"--export-dpi={dpi}",
        f"--export-filename={png_file}"
    ]
    subprocess.run(cmd_png, check=True)
    
    # Convert PNG to PDF
    pdf_file = out_dir / f"{svg_path.stem}.pdf"
    cmd_pdf = [
        INKSCAPE_EXE,
        str(png_file),
        "--export-type=pdf",
        f"--export-dpi={dpi}",
        f"--export-filename={pdf_file}"
    ]
    subprocess.run(cmd_pdf, check=True)
    
    # Clean up PNG file
    if png_file.exists():
        png_file.unlink()
    
    return pdf_file

def export_svg_direct(svg_path, out_dir, dpi):
    """
    Direct SVG to PDF export (keeps vectors, text searchable)
    """
    pdf_file = out_dir / f"{svg_path.stem}.pdf"
    cmd = [
        INKSCAPE_EXE,
        str(svg_path),
        "--export-type=pdf",
        f"--export-dpi={dpi}",
        # Keep text as text for searchability
        "--export-pdf-version=1.5",
        f"--export-filename={pdf_file}"
    ]
    subprocess.run(cmd, check=True)
    return pdf_file

def process_svg_folder(folder_path, dpi, rasterize=False):
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
        
        if rasterize:
            # Rasterize mode: SVG → PNG → PDF (smaller files, no searchable text)
            pdf_list.append(export_svg_to_png_then_pdf(svg, pdf_dir, dpi))
            mode_text = "Rasterizing"
        else:
            # Vector mode: Direct SVG → PDF (larger files, searchable text)
            pdf_list.append(export_svg_direct(svg, pdf_dir, dpi))
            mode_text = "Vector export"
            
        status_var.set(f"{mode_text}: {svg.name} ({i}/{len(svg_files)})")
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
    return merged_pdf, total_time, len(svg_files), rasterize

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
        # Get DPI value
        try:
            dpi = int(dpi_var.get())
        except ValueError:
            raise Exception("Please enter a valid number for DPI")
        
        if not folder_var.get():
            raise Exception("Please select a folder")

        # Get export mode
        rasterize = rasterize_var.get()
        
        progress_var.set(0)
        status_var.set("Starting export...")
        elapsed_var.set("Elapsed: 00:00:00")
        size_var.set("")

        start_time = time.time()
        timer_thread = threading.Thread(target=update_timer, args=(start_time, running_flag), daemon=True)
        timer_thread.start()

        merged_pdf_path, total_time, num_files, used_rasterize = process_svg_folder(
            folder_var.get(), dpi, rasterize
        )

        running_flag[0] = False
        elapsed_var.set(f"Total Time: {format_time(total_time)}")
        status_var.set(f"Completed - {num_files} files processed")
        
        # Check PDF properties
        try:
            from pypdf import PdfReader
            reader = PdfReader(merged_pdf_path)
            text_content = ""
            for page in reader.pages:
                text_content += page.extract_text()
            
            if text_content.strip() and not used_rasterize:
                searchable_status = "✅ Searchable PDF created"
            elif used_rasterize:
                searchable_status = "📸 Rasterized PDF (not searchable)"
            else:
                searchable_status = "⚠️ No text found (may be all vectors/images)"
        except:
            searchable_status = "ℹ️ Could not verify PDF properties"
        
        mode_info = "Rasterized (PNG→PDF)" if used_rasterize else "Vector (direct SVG→PDF)"
        
        messagebox.showinfo(
            "Success",
            f"✅ PDF export and merge completed!\n\n"
            f"Files processed: {num_files}\n"
            f"Mode: {mode_info}\n"
            f"DPI: {dpi}\n"
            f"Time taken: {format_time(total_time)}\n"
            f"Output file: {merged_pdf_path}\n\n"
            f"{searchable_status}\n"
            f"File size: {format_size(os.path.getsize(merged_pdf_path))}"
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
root.title("SVG → PDF Merger (Size Control Options)")
root.geometry("700x550")

# Variables
folder_var = tk.StringVar()
dpi_var = tk.StringVar(value="150")  # Lower default DPI
rasterize_var = tk.BooleanVar(value=False)  # Rasterization option
progress_var = tk.DoubleVar()
status_var = tk.StringVar(value="Ready - Select folder and click Export")
elapsed_var = tk.StringVar(value="Elapsed: 00:00:00")
size_var = tk.StringVar(value="")

# Title
tk.Label(root, text="SVG to PDF Converter & Merger", 
         font=("Arial", 14, "bold")).pack(pady=10)

# Important note
note_frame = tk.Frame(root, bg="#e6f3ff", relief="ridge", bd=1)
note_frame.pack(pady=5, fill="x", padx=20)
tk.Label(note_frame, 
         text="💡 For smaller files: Use Rasterize mode + lower DPI (72-150)", 
         bg="#e6f3ff", font=("Arial", 9, "bold"), fg="#0066cc").pack(pady=3)

# Folder selection
tk.Button(root, text="📁 Select SVG Folder", command=select_folder, 
          width=20, height=2).pack(pady=10)
tk.Label(root, textvariable=folder_var, wraplength=600, 
         bg="#f0f0f0", relief="sunken", padx=10, pady=5).pack(pady=5, fill="x", padx=40)

# Export settings frame
settings_frame = tk.LabelFrame(root, text="Export Settings", padx=10, pady=10)
settings_frame.pack(pady=10, fill="x", padx=40)

# DPI setting
tk.Label(settings_frame, text="DPI:").grid(row=0, column=0, sticky="w", pady=5)
dpi_entry = tk.Entry(settings_frame, textvariable=dpi_var, width=10)
dpi_entry.grid(row=0, column=1, sticky="w", padx=5, pady=5)

# DPI presets
presets_frame = tk.Frame(settings_frame)
presets_frame.grid(row=0, column=2, columnspan=3, padx=20, sticky="w")

for text, value in [("Tiny (72)", "72"), ("Small (96)", "96"), 
                    ("Medium (150)", "150"), ("Print (300)", "300")]:
    btn = tk.Button(presets_frame, text=text, width=8,
                   command=lambda v=value: dpi_var.set(v))
    btn.pack(side="left", padx=2)

# Export mode (Rasterize option)
tk.Label(settings_frame, text="Export Mode:").grid(row=1, column=0, sticky="w", pady=10)
mode_frame = tk.Frame(settings_frame)
mode_frame.grid(row=1, column=1, columnspan=4, sticky="w")

vector_btn = tk.Radiobutton(
    mode_frame, 
    text="Vector (Searchable text, larger files)", 
    variable=rasterize_var, 
    value=False,
    font=("Arial", 9)
)
vector_btn.pack(anchor="w")

raster_btn = tk.Radiobutton(
    mode_frame, 
    text="Rasterize (Smaller files, not searchable)", 
    variable=rasterize_var, 
    value=True,
    font=("Arial", 9)
)
raster_btn.pack(anchor="w")

# Progress bar
progress = ttk.Progressbar(
    root, orient="horizontal", length=600,
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

# Guide frame
guide_frame = tk.LabelFrame(root, text="How to Reduce File Size", padx=10, pady=5)
guide_frame.pack(pady=10, fill="x", padx=40)

guide_text = """📉 For SMALLEST files:
1. Select "Rasterize" mode
2. Use 72-96 DPI
3. Result: Image-based PDF, not searchable

⚖️ For BALANCED files:
1. Select "Vector" mode  
2. Use 150 DPI
3. Result: Searchable text, moderate size

🖨️ For PRINT quality:
1. Select "Vector" mode
2. Use 300 DPI
3. Result: High quality, searchable, large files

Note: A3 size with complex vectors → large files regardless of DPI"""
tk.Label(guide_frame, text=guide_text, font=("Arial", 8), 
         justify="left").pack()

# Footer
tk.Label(root, text="SVG to PDF Converter v2.0 - File Size Control Options", 
         font=("Arial", 8), fg="gray").pack(side="bottom", pady=5)

# Set focus to DPI entry
dpi_entry.focus_set()

root.mainloop()