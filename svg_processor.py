from pathlib import Path
import subprocess
import re
import os
import shutil
import xml.etree.ElementTree as ET
from utils import get_svg_pages_accurate, sanitize_filename

INKSCAPE_EXE = r"C:\Program Files\Inkscape\bin\inkscape.exe"

class SVGProcessor:
    def __init__(self, inkscape_path=INKSCAPE_EXE):
        self.inkscape_path = inkscape_path
        self.exported_files = []  # Track exported files
    
    def get_page_count(self, svg_path):
        """Get accurate page count for SVG file"""
        return get_svg_pages_accurate(svg_path)
    
    def _get_real_pages_from_svg(self, svg_path):
        """Intelligently find actual pages in SVG"""
        try:
            with open(svg_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Look for Inkscape page structure
            pages = []
            
            # Pattern 1: Look for page1, page2, etc. (case insensitive)
            page_pattern = r'id="(page\d+)"'
            pages.extend(re.findall(page_pattern, content, re.IGNORECASE))
            
            # Pattern 2: Look for Page1, Page2, etc. (case sensitive)
            Page_pattern = r'id="(Page\d+)"'
            pages.extend(re.findall(Page_pattern, content))
            
            # Pattern 3: Look for layer1, layer2, etc. that might be pages
            layer_pattern = r'id="(layer\d+)"'
            layers = re.findall(layer_pattern, content, re.IGNORECASE)
            
            # Filter layers that might actually be pages
            for layer in layers:
                # Check if layer name suggests it's a page
                if any(keyword in content.lower() for keyword in [f'>{layer}<', f'"{layer}"']):
                    # Look for surrounding context
                    context_pattern = f'id="{layer}"[^>]*inkscape:label="[^"]*page[^"]*"'
                    if re.search(context_pattern, content, re.IGNORECASE):
                        pages.append(layer)
            
            # Remove duplicates and sort
            unique_pages = sorted(set(pages))
            
            print(f"Found potential pages: {unique_pages}")
            return unique_pages
            
        except Exception as e:
            print(f"Error analyzing SVG: {e}")
            return []
    
    def _export_page_simple(self, svg_path, page_id, output_pdf, dpi):
        """Simple page export using page ID"""
        cmd = [
            self.inkscape_path,
            str(svg_path),
            f"--export-id={page_id}",
            "--export-id-only",
            "--export-type=pdf",
            f"--export-dpi={dpi}",
            f"--export-filename={output_pdf}"
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                return True
            else:
                print(f"Export failed: {result.stderr}")
                return False
        except Exception as e:
            print(f"Export error: {e}")
            return False
    
    def _export_with_area(self, svg_path, page_num, total_pages, output_pdf, dpi):
        """Export by calculating area (for horizontally arranged pages)"""
        # Get document dimensions
        cmd = [
            self.inkscape_path,
            str(svg_path),
            "--query-width",
            "--query-height"
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if len(lines) >= 2:
                    doc_width = float(lines[0])
                    doc_height = float(lines[1])
                    
                    # Calculate area for this page (assuming horizontal arrangement)
                    page_width = doc_width / total_pages
                    x1 = (page_num - 1) * page_width
                    x2 = x1 + page_width
                    
                    export_cmd = [
                        self.inkscape_path,
                        str(svg_path),
                        f"--export-area={x1}:0:{x2}:{doc_height}",
                        "--export-type=pdf",
                        f"--export-dpi={dpi}",
                        f"--export-filename={output_pdf}"
                    ]
                    
                    result = subprocess.run(export_cmd, capture_output=True, text=True, timeout=30)
                    return result.returncode == 0
        except:
            pass
        
        return False
    
    def _export_entire_document(self, svg_path, output_pdf, dpi):
        """Export entire document as fallback"""
        cmd = [
            self.inkscape_path,
            str(svg_path),
            "--export-type=pdf",
            f"--export-dpi={dpi}",
            f"--export-filename={output_pdf}"
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            return result.returncode == 0
        except:
            return False
    
    def export_svg_page(self, svg_path, page_num, out_dir, dpi, rasterize=False):
        """Export a specific page of an SVG file to PDF"""
        svg_path = Path(svg_path)
        safe_name = sanitize_filename(svg_path.stem)
        base_name = f"{safe_name}_page{page_num:03d}"
        pdf_file = out_dir / f"{base_name}.pdf"
        
        print(f"\nExporting page {page_num} of {svg_path.name}")
        
        # Ensure output directory exists
        out_dir.mkdir(parents=True, exist_ok=True)
        
        # Get total pages
        total_pages = self.get_page_count(svg_path)
        
        # Try different export methods in order
        methods = [
            # Method 1: Try to find and export by page ID
            lambda: self._try_export_by_id(svg_path, page_num, pdf_file, dpi),
            # Method 2: Export by calculated area
            lambda: self._export_with_area(svg_path, page_num, total_pages, pdf_file, dpi),
            # Method 3: If page 1, export entire document
            lambda: self._export_entire_document(svg_path, pdf_file, dpi) if page_num == 1 else False,
        ]
        
        success = False
        for method_num, method in enumerate(methods, 1):
            print(f"  Trying method {method_num}...")
            if method():
                success = True
                print(f"  Method {method_num} succeeded")
                break
        
        if success and pdf_file.exists() and pdf_file.stat().st_size > 0:
            self.exported_files.append(pdf_file)
            
            # Verify page dimensions
            try:
                from pypdf import PdfReader
                reader = PdfReader(str(pdf_file))
                if reader.pages:
                    page = reader.pages[0]
                    width = float(page.mediabox.width)
                    height = float(page.mediabox.height)
                    
                    # Check if dimensions are reasonable
                    if width > 2000:  # If too wide (> ~28 inches)
                        print(f"  ⚠ Warning: Page is very wide ({width:.1f} points)")
                        # Try to fix by exporting with different settings
                        return self._fix_wide_page(svg_path, page_num, pdf_file, dpi)
                    
                    print(f"✓ Created: {pdf_file.name} ({pdf_file.stat().st_size:,} bytes)")
                    print(f"  Dimensions: {width:.1f} x {height:.1f} points")
                    return pdf_file
            except:
                pass
            
            print(f"✓ Created: {pdf_file.name} ({pdf_file.stat().st_size:,} bytes)")
            return pdf_file
        
        print(f"✗ Failed to export page {page_num}")
        return None
    
    def _try_export_by_id(self, svg_path, page_num, output_pdf, dpi):
        """Try to export using page/layer IDs"""
        page_ids = self._get_real_pages_from_svg(svg_path)
        
        if page_num <= len(page_ids):
            page_id = page_ids[page_num - 1]
            print(f"  Using page ID: {page_id}")
            return self._export_page_simple(svg_path, page_id, output_pdf, dpi)
        
        return False
    
    def _fix_wide_page(self, svg_path, page_num, pdf_file, dpi):
        """Fix pages that are too wide by using different export method"""
        print(f"  Attempting to fix wide page...")
        
        # Try to export with different area calculation
        total_pages = self.get_page_count(svg_path)
        
        # Delete the wide PDF first
        if pdf_file.exists():
            pdf_file.unlink()
        
        # Try export with tighter area
        if self._export_with_area(svg_path, page_num, total_pages, pdf_file, dpi):
            if pdf_file.exists():
                # Check new dimensions
                try:
                    from pypdf import PdfReader
                    reader = PdfReader(str(pdf_file))
                    if reader.pages:
                        page = reader.pages[0]
                        width = float(page.mediabox.width)
                        height = float(page.mediabox.height)
                        print(f"  Fixed dimensions: {width:.1f} x {height:.1f} points")
                        return pdf_file
                except:
                    pass
        
        return None
    
    def process_svg_file(self, svg_path, temp_dir, dpi, rasterize=False):
        """Process a single SVG file - export all pages"""
        svg_path = Path(svg_path)
        
        # Get accurate page count
        num_pages = self.get_page_count(svg_path)
        
        print(f"\n{'='*60}")
        print(f"PROCESSING: {svg_path.name}")
        print(f"Pages detected: {num_pages}")
        print(f"{'='*60}")
        
        pdf_files = []
        successful_pages = 0
        
        # Export each page
        for page in range(1, num_pages + 1):
            pdf_file = self.export_svg_page(svg_path, page, temp_dir, dpi, rasterize)
            if pdf_file and pdf_file.exists():
                pdf_files.append(pdf_file)
                successful_pages += 1
            else:
                print(f"⚠ Page {page} failed to export")
        
        print(f"\n{'='*60}")
        print(f"RESULT: {successful_pages}/{num_pages} pages exported")
        print(f"{'='*60}")
        
        return pdf_files
    
    def cleanup_exported_files(self):
        """Clean up all exported files"""
        for file in self.exported_files:
            if file.exists():
                try:
                    file.unlink()
                except:
                    pass
        self.exported_files = []