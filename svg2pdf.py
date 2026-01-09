from pathlib import Path
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pypdf import PdfWriter
import traceback
import threading

# ---- FIXED INKSCAPE PATH ----
INKSCAPE_EXE = r"C:\Program Files\Inkscape\bin\inkscape.exe"


def show_error(err):
    win = tk.Toplevel()
    win.title("Error details")
    win.geometry("800x350")

    txt = tk.Text(win, wrap="word")
    txt.pack(expand=True, fill="both")

    txt.insert("1.0", err)
    txt.config(state="normal")


def export_svg(svg_path, out_dir, dpi):
    out_pdf = out_dir / f"{svg_path.stem}.pdf"

    cmd = [
        INKSCAPE_EXE,
        str(svg_path),
        "--export-type=pdf",
        f"--export-dpi={dpi}",
        f"--export-filename={out_pdf}"
    ]

    subprocess.run(cmd, check=True)
    return out_pdf


def process_svg_folder(folder_path, dpi):
    folder = Path(folder_path)
    svg_files = sorted(folder.glob("*.svg"))

    if not svg_files:
        raise Exception("No SVG files found in selected folder")

    pdf_dir = folder / "pdf_exports"
    pdf_dir.mkdir(exist_ok=True)

    total_steps = len(svg_files) + 1  # +1 for merge step
    step = 0

    pdf_list = []

    for svg in svg_files:
        status_var.set(f"Exporting: {svg.name}")
        pdf_list.append(export_svg(svg, pdf_dir, dpi))
        step += 1
        progress_var.set((step / total_steps) * 100)
        root.update_idletasks()

    # Merge PDFs
    status_var.set("Merging PDFs...")
    writer = PdfWriter()

    for pdf in pdf_list:
        writer.append(str(pdf))

    merged_pdf = folder / "Merged_Output.pdf"
    with open(merged_pdf, "wb") as f:
        writer.write(f)

    step += 1
    progress_var.set(100)
    root.update_idletasks()

    return merged_pdf


def select_folder():
    folder_var.set(filedialog.askdirectory())


def run_task():
    try:
        dpi = int(dpi_var.get())
        if not folder_var.get():
            raise Exception("Please select a folder")

        progress_var.set(0)
        status_var.set("Starting...")
        result = process_svg_folder(folder_var.get(), dpi)

        status_var.set("Completed successfully ✔")
        messagebox.showinfo(
            "Success",
            f"PDF export and merge completed!\n\nOutput file:\n{result}"
        )

    except Exception:
        err = traceback.format_exc()
        print(err)
        show_error(err)

    finally:
        run_btn.config(state="normal")


def run():
    run_btn.config(state="disabled")
    threading.Thread(target=run_task, daemon=True).start()


# ---- GUI ----
root = tk.Tk()
root.title("SVG → PDF Merger")
root.geometry("480x320")

folder_var = tk.StringVar()
dpi_var = tk.StringVar(value="300")
progress_var = tk.DoubleVar()
status_var = tk.StringVar(value="Idle")

tk.Button(root, text="Select SVG Folder", command=select_folder).pack(pady=10)
tk.Label(root, textvariable=folder_var, wraplength=440).pack()

tk.Label(root, text="Export DPI").pack(pady=5)
tk.Entry(root, textvariable=dpi_var, width=10).pack()

progress = ttk.Progressbar(
    root,
    orient="horizontal",
    length=420,
    mode="determinate",
    variable=progress_var
)
progress.pack(pady=15)

tk.Label(root, textvariable=status_var).pack()

run_btn = tk.Button(root, text="Export and Merge", command=run)
run_btn.pack(pady=15)

root.mainloop()
