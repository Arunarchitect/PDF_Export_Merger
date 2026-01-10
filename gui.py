import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
import threading
import time  # <-- ADD THIS IMPORT
import traceback
import os
from utils import format_time, format_size
from pdf_merger import PDFMerger

class SVGListManager:
    """Manages the list of SVG files in the GUI"""
    def __init__(self, listbox):
        self.listbox = listbox
        self.files = []
    
    def add_files(self, file_paths):
        """Add files to the list"""
        for path in file_paths:
            if path not in self.files:
                self.files.append(path)
        
        self.sort_alphabetical()
        self.refresh_listbox()
    
    def remove_selected(self):
        """Remove selected files from list"""
        selected_indices = self.listbox.curselection()
        for index in reversed(selected_indices):
            if 0 <= index < len(self.files):
                del self.files[index]
        self.refresh_listbox()
    
    def move_up(self):
        """Move selected item up"""
        selected = self.listbox.curselection()
        if selected and selected[0] > 0:
            index = selected[0]
            self.files[index], self.files[index-1] = self.files[index-1], self.files[index]
            self.refresh_listbox()
            self.listbox.selection_set(index-1)
    
    def move_down(self):
        """Move selected item down"""
        selected = self.listbox.curselection()
        if selected and selected[0] < len(self.files) - 1:
            index = selected[0]
            self.files[index], self.files[index+1] = self.files[index+1], self.files[index]
            self.refresh_listbox()
            self.listbox.selection_set(index+1)
    
    def sort_alphabetical(self):
        """Sort files alphabetically by name"""
        self.files.sort(key=lambda x: x.name.lower())
        self.refresh_listbox()
    
    def clear_all(self):
        """Clear all files from list"""
        self.files.clear()
        self.refresh_listbox()
    
    def refresh_listbox(self):
        """Refresh listbox display"""
        self.listbox.delete(0, tk.END)
        for file in self.files:
            from utils import get_svg_pages_accurate
            num_pages = get_svg_pages_accurate(file)
            display_text = f"{file.name}"
            
            # Show page count with color coding
            if num_pages > 1:
                if num_pages > 20:
                    # Likely incorrect page detection
                    display_text += f" ({num_pages} pages? - check)"
                else:
                    display_text += f" ({num_pages} pages)"
            
            self.listbox.insert(tk.END, display_text)
            
            # Color code based on page count reliability
            if num_pages > 20:
                self.listbox.itemconfig(tk.END, {'fg': 'orange'})
            elif num_pages > 1:
                self.listbox.itemconfig(tk.END, {'fg': 'blue'})
    
    def get_files(self):
        """Return list of file paths"""
        return self.files.copy()

class SVGPDFMergerGUI:
    """Main GUI application"""
    def __init__(self, root):
        self.root = root
        self.root.title("SVG → PDF Merger with File Selection & Reordering")
        self.root.geometry("800x750")
        
        # Variables
        self.dpi_var = tk.StringVar(value="150")
        self.rasterize_var = tk.BooleanVar(value=False)
        self.progress_var = tk.DoubleVar()
        self.status_var = tk.StringVar(value="Ready - Select SVG files and output location")
        self.elapsed_var = tk.StringVar(value="Elapsed: 00:00:00")
        self.size_var = tk.StringVar(value="")
        self.output_var = tk.StringVar()
        
        # Initialize components
        self.list_manager = None
        self.pdf_merger = PDFMerger()
        self.running_flag = None
        
        # Build GUI
        self._setup_gui()
    
    def _setup_gui(self):
        """Set up the GUI components"""
        # Title
        tk.Label(self.root, text="SVG to PDF Converter & Merger", 
                font=("Arial", 14, "bold")).pack(pady=10)
        
        # Note frame
        note_frame = tk.Frame(self.root, bg="#e6f3ff", relief="ridge", bd=1)
        note_frame.pack(pady=5, fill="x", padx=20)
        tk.Label(note_frame, 
                text="💡 Multi-page SVG support | File selection | Drag & drop reordering", 
                bg="#e6f3ff", font=("Arial", 9, "bold"), fg="#0066cc").pack(pady=3)
        
        # File selection frame
        self._create_file_selection_frame()
        
        # Output frame
        self._create_output_frame()
        
        # Export settings frame
        self._create_settings_frame()
        
        # Progress bar
        self.progress = ttk.Progressbar(
            self.root, orient="horizontal", length=600,
            mode="determinate", variable=self.progress_var
        )
        self.progress.pack(pady=15)
        
        # Status labels
        tk.Label(self.root, textvariable=self.status_var, font=("Arial", 10)).pack(pady=2)
        tk.Label(self.root, textvariable=self.elapsed_var, font=("Arial", 9)).pack()
        tk.Label(self.root, textvariable=self.size_var, font=("Arial", 9, "bold"), 
                fg="blue").pack(pady=5)
        
        # Control buttons
        self._create_control_buttons()
        
        # Guide frame
        self._create_guide_frame()
        
        # Footer
        tk.Label(self.root, text="SVG to PDF Converter v3.0 - Modular Version", 
                font=("Arial", 8), fg="gray").pack(side="bottom", pady=5)
    
    def _create_file_selection_frame(self):
        """Create file selection frame with listbox"""
        selection_frame = tk.LabelFrame(self.root, text="SVG File Selection", padx=10, pady=10)
        selection_frame.pack(pady=10, fill="both", expand=True, padx=20)
        
        # File list with scrollbar
        list_frame = tk.Frame(selection_frame)
        list_frame.pack(fill="both", expand=True, pady=5)
        
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.file_listbox = tk.Listbox(list_frame, height=10, yscrollcommand=scrollbar.set,
                                    selectmode=tk.EXTENDED)
        self.file_listbox.pack(side=tk.LEFT, fill="both", expand=True)
        scrollbar.config(command=self.file_listbox.yview)
        
        # Initialize list manager
        self.list_manager = SVGListManager(self.file_listbox)
        
        # File control buttons
        file_controls_frame = tk.Frame(selection_frame)
        file_controls_frame.pack(fill="x", pady=5)
        
        buttons = [
            ("📁 Add Files", self.select_svg_files, 12),
            ("❌ Remove Selected", self.list_manager.remove_selected, 15),
            ("⬆️ Move Up", self.list_manager.move_up, 10),
            ("⬇️ Move Down", self.list_manager.move_down, 10),
            ("🔤 Sort A-Z", self.list_manager.sort_alphabetical, 10),
            ("🗑️ Clear All", self.list_manager.clear_all, 10)
        ]
        
        for text, command, width in buttons:
            tk.Button(file_controls_frame, text=text, command=command, width=width).pack(side=tk.LEFT, padx=2)
    
    def _create_output_frame(self):
        """Create output location frame"""
        output_frame = tk.LabelFrame(self.root, text="Output Settings", padx=10, pady=10)
        output_frame.pack(pady=10, fill="x", padx=20)
        
        tk.Button(output_frame, text="💾 Select Output File", 
                command=self.select_output_location, width=20).pack(side=tk.LEFT, padx=5, pady=5)
        tk.Label(output_frame, text="Output:", font=("Arial", 9)).pack(side=tk.LEFT, padx=5)
        tk.Entry(output_frame, textvariable=self.output_var, width=50).pack(side=tk.LEFT, padx=5, fill="x", expand=True)
    
    def _create_settings_frame(self):
        """Create export settings frame"""
        settings_frame = tk.LabelFrame(self.root, text="Export Settings", padx=10, pady=10)
        settings_frame.pack(pady=10, fill="x", padx=20)
        
        # DPI setting
        tk.Label(settings_frame, text="DPI:").grid(row=0, column=0, sticky="w", pady=5)
        self.dpi_entry = tk.Entry(settings_frame, textvariable=self.dpi_var, width=10)
        self.dpi_entry.grid(row=0, column=1, sticky="w", padx=5, pady=5)
        
        # DPI presets
        presets_frame = tk.Frame(settings_frame)
        presets_frame.grid(row=0, column=2, columnspan=3, padx=20, sticky="w")
        
        for text, value in [("Tiny (72)", "72"), ("Small (96)", "96"), 
                          ("Medium (150)", "150"), ("Print (300)", "300")]:
            btn = tk.Button(presets_frame, text=text, width=8,
                          command=lambda v=value: self.dpi_var.set(v))
            btn.pack(side="left", padx=2)
        
        # Export mode
        tk.Label(settings_frame, text="Export Mode:").grid(row=1, column=0, sticky="w", pady=10)
        mode_frame = tk.Frame(settings_frame)
        mode_frame.grid(row=1, column=1, columnspan=4, sticky="w")
        
        tk.Radiobutton(
            mode_frame, 
            text="Vector (Searchable text, larger files)", 
            variable=self.rasterize_var, 
            value=False,
            font=("Arial", 9)
        ).pack(anchor="w")
        
        tk.Radiobutton(
            mode_frame, 
            text="Rasterize (Smaller files, not searchable)", 
            variable=self.rasterize_var, 
            value=True,
            font=("Arial", 9)
        ).pack(anchor="w")
    
    def _create_control_buttons(self):
        """Create control buttons frame"""
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=15)
        
        self.run_btn = tk.Button(btn_frame, text="▶️ Export & Merge", width=15, 
                               height=2, command=self.run, bg="#4CAF50", fg="white", 
                               state="disabled")
        self.run_btn.pack(side="left", padx=5)
        
        self.next_btn = tk.Button(btn_frame, text="🔄 Start New", width=15, 
                                height=2, command=self.reset_gui, state="normal")
        self.next_btn.pack(side="left", padx=5)
    
    def _create_guide_frame(self):
        """Create guide/info frame"""
        guide_frame = tk.LabelFrame(self.root, text="Features", padx=10, pady=5)
        guide_frame.pack(pady=10, fill="x", padx=40)
        
        guide_text = """✨ FEATURES:
• Multi-page SVG support (exports all pages)
• Select individual SVG files
• Reorder files with Up/Down buttons
• Automatic alphabetical sorting
• Custom output location and filename

📊 FILE PROCESSING:
• Files show page count if multi-page
• Pages exported in order (file order × page order)
• Progress shows current page/total pages

💡 TIPS:
• Use 'Sort A-Z' for alphabetical default order
• Reorder files before export for custom PDF order
• Vector mode = searchable, Rasterize = smaller files"""
        tk.Label(guide_frame, text=guide_text, font=("Arial", 8), 
                justify="left").pack()
    
    def select_svg_files(self):
        """Open file dialog to select SVG files"""
        files = filedialog.askopenfilenames(
            title="Select SVG files",
            filetypes=[("SVG files", "*.svg"), ("All files", "*.*")]
        )
        if files:
            file_paths = [Path(f) for f in files]
            self.list_manager.add_files(file_paths)
            self.update_export_button_state()
    
    def select_output_location(self):
        """Open save dialog for output PDF"""
        output_file = filedialog.asksaveasfilename(
            title="Save PDF as",
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        if output_file:
            self.output_var.set(output_file)
            self.update_export_button_state()
    
    def update_export_button_state(self):
        """Enable/disable export button based on conditions"""
        has_files = len(self.list_manager.get_files()) > 0
        has_output = bool(self.output_var.get().strip())
        
        if has_files and has_output:
            self.run_btn.config(state="normal")
        else:
            self.run_btn.config(state="disabled")
    
    def reset_gui(self):
        """Reset GUI to initial state"""
        self.list_manager.clear_all()
        self.output_var.set("")
        self.progress_var.set(0)
        self.status_var.set("Ready - Select SVG files and output location")
        self.elapsed_var.set("Elapsed: 00:00:00")
        self.size_var.set("")
        self.run_btn.config(state="disabled")
        self.next_btn.config(state="normal")
    
    def update_timer(self, start_time):
        """Update elapsed time display"""
        while self.running_flag[0]:
            self.elapsed_var.set(f"Elapsed: {format_time(time.time() - start_time)}")
            time.sleep(1)
    
    def show_error(self, err):
        """Show error details in a new window"""
        win = tk.Toplevel(self.root)
        win.title("Error details")
        win.geometry("850x400")
        txt = tk.Text(win, wrap="word")
        txt.pack(expand=True, fill="both")
        txt.insert("1.0", err)
    
    def run(self):
        """Start the export process"""
        self.run_btn.config(state="disabled")
        self.next_btn.config(state="disabled")
        threading.Thread(target=self._run_task, daemon=True).start()
    
    def _run_task(self):
        """Main task function (runs in separate thread)"""
        self.running_flag = [True]
        
        try:
            # Validate DPI
            try:
                dpi = int(self.dpi_var.get())
                if dpi < 10 or dpi > 1200:
                    raise ValueError("DPI must be between 10 and 1200")
            except ValueError as e:
                raise Exception(f"Invalid DPI: {e}")
            
            # Get files and output path
            svg_files = self.list_manager.get_files()
            if not svg_files:
                raise Exception("Please select SVG files")
            
            output_path = Path(self.output_var.get())
            if not output_path.parent.exists():
                output_path.parent.mkdir(parents=True)
            
            # Get export mode
            rasterize = self.rasterize_var.get()
            
            # Reset progress
            self.progress_var.set(0)
            self.status_var.set("Starting export...")
            self.elapsed_var.set("Elapsed: 00:00:00")
            self.size_var.set("")
            
            # Start timer
            start_time = time.time()
            timer_thread = threading.Thread(target=self.update_timer, args=(start_time,), daemon=True)
            timer_thread.start()
            
            # Process files
            merged_pdf_path, total_pages = self.pdf_merger.process_svg_files(
                svg_files, output_path, dpi, rasterize
            )
            
            # Stop timer
            self.running_flag[0] = False
            
            # Calculate total time
            total_time = time.time() - start_time
            self.elapsed_var.set(f"Total Time: {format_time(total_time)}")
            self.status_var.set(f"Completed - {len(svg_files)} files, {total_pages} pages processed")
            
            # Show success message
            if merged_pdf_path.exists():
                file_size = os.path.getsize(merged_pdf_path)
                mode = "Rasterized" if rasterize else "Vector"
                
                messagebox.showinfo(
                    "Success",
                    f"✅ PDF export completed!\n\n"
                    f"Files: {len(svg_files)}\n"
                    f"Pages: {total_pages}\n"
                    f"Mode: {mode}\n"
                    f"DPI: {dpi}\n"
                    f"Time: {format_time(total_time)}\n"
                    f"Output: {merged_pdf_path}\n"
                    f"Size: {format_size(file_size)}"
                )
            
        except Exception as e:
            self.running_flag[0] = False
            err = traceback.format_exc()
            self.show_error(err)
            self.status_var.set("Error - Check details")
        
        finally:
            self.next_btn.config(state="normal")