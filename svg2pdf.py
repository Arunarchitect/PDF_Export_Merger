from pathlib import Path
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pypdf import PdfWriter
import pikepdf
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
    """Return human-readable size"""
    for unit in ['B','KB','MB','GB']:
        if bytes_size < 1024:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024
    return f"{bytes_size:.2f} TB"

def export_svg(svg_path, out_dir, dpi):
    out_pdf = out_dir / f"{svg_path.stem}.pdf"
    cmd = [
        INKSCAPE_EXE,
        str(svg_path),
        "--export-type=pdf",
        f"--export-dpi={dpi}",
        "--export-text-to-path",
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
        status_var.set(f"Exporting: {svg.name}")
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

    # Show pre-compression size
    merged_size = os.path.getsize(merged_pdf)
    size_var.set(f"Merged PDF size: {format_size(merged_size)}")

    progress_var.set(100)
    total_time = time.time() - start_time
    return merged_pdf, total_time

# ------------------------ Compression ------------------------

def compress_pdf(input_pdf, output_pdf):
    with pikepdf.open(input_pdf) as pdf:
        pdf.save(output_pdf)

    # Show compressed size
    compressed_size = os.path.getsize(output_pdf)
    size_var.set(f"Compressed PDF size: {format_size(compressed_size)}")
    messagebox.showinfo("Compression Done", f"Compressed PDF created:\n{output_pdf}\n\nSize: {format_size(compressed_size)}")

# ------------------------ GUI Actions ------------------------

def select_folder():
    folder_var.set(filedialog.askdirectory())

def reset_gui():
    folder_var.set("")
    progress_var.set(0)
    status_var.set("Idle")
    elapsed_var.set("Elapsed: 00:00:00")
    size_var.set("")
    run_btn.config(state="normal")
    compress_btn.config(state="disabled")

def update_timer(start_time, running_flag):
    """Update elapsed time every second while task is running"""
    while running_flag[0]:
        elapsed_var.set(f"Elapsed: {format_time(time.time() - start_time)}")
        time.sleep(1)

def run_task():
    running_flag = [True]
    try:
        dpi = int(dpi_var.get())
        if not folder_var.get():
            raise Exception("Please select a folder")

        progress_var.set(0)
        status_var.set("Starting...")
        elapsed_var.set("Elapsed: 00:00:00")
        size_var.set("")

        start_time = time.time()
        # Start timer thread
        timer_thread = threading.Thread(target=update_timer, args=(start_time, running_flag), daemon=True)
        timer_thread.start()

        merged_pdf_path, _ = process_svg_folder(folder_var.get(), dpi)

        running_flag[0] = False
        elapsed_var.set(f"Total Time: {format_time(time.time() - start_time)}")
        status_var.set("Completed ✔")
        compress_btn.config(state="normal")
        messagebox.showinfo(
            "Success",
            f"PDF export and merge completed!\n\nOutput:\n{merged_pdf_path}\n\n"
            f"Time taken: {format_time(time.time() - start_time)}"
        )
        global last_merged_pdf
        last_merged_pdf = merged_pdf_path

    except Exception:
        running_flag[0] = False
        err = traceback.format_exc()
        show_error(err)
    finally:
        next_btn.config(state="normal")
        run_btn.config(state="disabled")

def run():
    run_btn.config(state="disabled")
    next_btn.config(state="disabled")
    compress_btn.config(state="disabled")
    threading.Thread(target=run_task, daemon=True).start()

def compress_task():
    if 'last_merged_pdf' in globals() and last_merged_pdf.exists():
        folder = last_merged_pdf.parent
        compressed_pdf = folder / f"{last_merged_pdf.stem}_compressed.pdf"
        try:
            compress_pdf(str(last_merged_pdf), str(compressed_pdf))
        except Exception:
            show_error(traceback.format_exc())
    else:
        messagebox.showwarning("No PDF", "No merged PDF found to compress.")

# ---------------- GUI ----------------

root = tk.Tk()
root.title("SVG → PDF Merger & Compressor (Open Source)")
root.geometry("560x420")

folder_var = tk.StringVar()
dpi_var = tk.StringVar(value="300")
progress_var = tk.DoubleVar()
status_var = tk.StringVar(value="Idle")
elapsed_var = tk.StringVar(value="Elapsed: 00:00:00")
size_var = tk.StringVar(value="")

tk.Button(root, text="Select SVG Folder", command=select_folder).pack(pady=10)
tk.Label(root, textvariable=folder_var, wraplength=520).pack()

tk.Label(root, text="Export DPI").pack(pady=5)
tk.Entry(root, textvariable=dpi_var, width=10).pack()

progress = ttk.Progressbar(
    root, orient="horizontal", length=520,
    mode="determinate", variable=progress_var
)
progress.pack(pady=15)

tk.Label(root, textvariable=status_var).pack()
tk.Label(root, textvariable=elapsed_var).pack()
tk.Label(root, textvariable=size_var).pack(pady=5)

btn_frame = tk.Frame(root)
btn_frame.pack(pady=15)

run_btn = tk.Button(btn_frame, text="Export & Merge", width=15, command=run)
run_btn.pack(side="left", padx=5)

compress_btn = tk.Button(btn_frame, text="Compress PDF", width=15, command=compress_task, state="disabled")
compress_btn.pack(side="left", padx=5)

next_btn = tk.Button(btn_frame, text="Next Merge Task", width=15, command=reset_gui, state="disabled")
next_btn.pack(side="left", padx=5)

root.mainloop()
