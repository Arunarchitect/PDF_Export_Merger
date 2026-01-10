from pathlib import Path
import time
import os
import re
import xml.etree.ElementTree as ET

def format_time(sec):
    """Format seconds to HH:MM:SS"""
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = int(sec % 60)
    return f"{h:02}:{m:02}:{s:02}"

def format_size(bytes_size):
    """Format bytes to human readable size"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024
    return f"{bytes_size:.2f} TB"

def analyze_svg_structure(svg_path):
    """
    Analyze SVG structure to understand how pages are organized
    """
    try:
        svg_path = Path(svg_path)
        with open(svg_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        print(f"\nAnalyzing {svg_path.name} structure:")
        
        # Find all IDs with 'page' in them
        page_ids = re.findall(r'id="([^"]*page[^"]*)"', content, re.IGNORECASE)
        print(f"  Found {len(page_ids)} IDs with 'page': {page_ids}")
        
        # Find all IDs with 'layer' in them
        layer_ids = re.findall(r'id="([^"]*layer[^"]*)"', content, re.IGNORECASE)
        print(f"  Found {len(layer_ids)} IDs with 'layer' (first 5): {layer_ids[:5]}")
        
        # Look for Inkscape page structure
        inkscape_pages = re.findall(r'<inkscape:page[^>]*>', content)
        if inkscape_pages:
            print(f"  Found {len(inkscape_pages)} Inkscape page tags")
        
        # Look for page numbers in the content
        page_numbers = re.findall(r'\bpage\s*(\d+)\b', content, re.IGNORECASE)
        if page_numbers:
            print(f"  Found page numbers: {sorted(set(page_numbers))}")
        
        return True
    except Exception as e:
        print(f"  Analysis error: {e}")
        return False

def get_svg_pages_smart(svg_path):
    """
    Smart page detection for SVG files with better heuristics
    """
    try:
        svg_path = Path(svg_path)
        
        # First, analyze the file structure
        analyze_svg_structure(svg_path)
        
        with open(svg_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # METHOD 1: Check filename for page hints
        filename = svg_path.stem.lower()
        print(f"  Filename analysis: {filename}")
        
        # Look for page ranges in filename (e.g., "Pg1,2" or "Pg1-2")
        page_range_match = re.search(r'pg[\.\s]*(\d+)[,\-]\s*(\d+)', filename)
        if page_range_match:
            start = int(page_range_match.group(1))
            end = int(page_range_match.group(2))
            if start <= end:
                page_count = end - start + 1
                print(f"  Based on filename range: {page_count} pages ({start} to {end})")
                return page_count
        
        # Look for single page number in filename
        single_page_match = re.search(r'pg[\.\s]*(\d+)', filename)
        if single_page_match:
            print(f"  Based on filename: 1 page (page {single_page_match.group(1)})")
            return 1
        
        # METHOD 2: Look for organized page structure
        # Find all page IDs and extract their numbers
        page_id_matches = re.findall(r'id="(page\d+|Page\d+)"', content)
        
        if page_id_matches:
            # Extract numbers from page IDs
            page_numbers = []
            for page_id in page_id_matches:
                num_match = re.search(r'(\d+)$', page_id)
                if num_match:
                    num = int(num_match.group())
                    page_numbers.append(num)
            
            if page_numbers:
                # Sort and look for a reasonable sequence
                page_numbers.sort()
                
                # Heuristic: If we have sequential numbers starting from 1 or 0
                # and the max number is reasonable (< 20), use that
                if (page_numbers[0] in [0, 1]) and len(page_numbers) <= 20:
                    max_page = max(page_numbers)
                    print(f"  Based on page IDs: {max_page} pages (IDs: {page_numbers})")
                    return max_page if page_numbers[0] == 1 else max_page + 1
        
        # METHOD 3: Look for layer structure
        # Count layers that might be pages
        layer_groups = re.findall(r'<g[^>]*inkscape:groupmode="layer"[^>]*>', content)
        if layer_groups:
            # Check if layers are named as pages
            page_layers = 0
            for layer in layer_groups:
                if 'inkscape:label=' in layer:
                    label_match = re.search(r'inkscape:label="([^"]+)"', layer)
                    if label_match and 'page' in label_match.group(1).lower():
                        page_layers += 1
            
            if page_layers > 0:
                print(f"  Based on layer labels: {page_layers} page layers")
                return page_layers
        
        # METHOD 4: Look for common patterns
        # Check for multiple viewBox attributes
        viewboxes = re.findall(r'viewBox="[^"]*"', content)
        if len(viewboxes) > 1:
            print(f"  Based on viewBox count: {len(viewboxes)} pages")
            return len(viewboxes)
        
        # Default to 1 page
        print(f"  Default: 1 page")
        return 1
        
    except Exception as e:
        print(f"  Page detection error: {e}")
        return 1

def get_svg_pages_accurate(svg_path):
    """
    Main function to get accurate page count with sanity checks
    """
    svg_path = Path(svg_path)
    
    print(f"\n{'='*50}")
    print(f"Detecting pages for: {svg_path.name}")
    
    # First try smart detection
    count = get_svg_pages_smart(svg_path)
    
    # Sanity checks
    file_size = svg_path.stat().st_size
    print(f"  File size: {file_size:,} bytes")
    
    # Heuristic: If count seems too high, apply limits
    if count > 20:
        print(f"  ⚠ Warning: Detected {count} pages - seems high")
        
        # Check file size vs page count
        # Rough estimate: each reasonable page is at least 5KB
        min_expected_size = count * 5000
        
        if file_size < min_expected_size:
            print(f"  ⚠ File too small ({file_size:,} bytes) for {count} pages")
            print(f"  ⚠ Expected at least {min_expected_size:,} bytes")
            
            # Look at filename for clues
            filename = svg_path.stem.lower()
            if 'pg' in filename:
                # Try to extract page range from filename
                range_match = re.search(r'pg[\.\s]*(\d+)[,\-]\s*(\d+)', filename)
                if range_match:
                    start = int(range_match.group(1))
                    end = int(range_match.group(2))
                    if start <= end:
                        adjusted_count = end - start + 1
                        print(f"  ✓ Adjusted to {adjusted_count} pages based on filename range")
                        return adjusted_count
                
                # Look for single page
                single_match = re.search(r'pg[\.\s]*(\d+)', filename)
                if single_match:
                    print(f"  ✓ Adjusted to 1 page based on filename")
                    return 1
        
        # If still high, cap at reasonable number
        if count > 50:
            print(f"  ⚠ Capping at 10 pages (detected {count} seems unreasonable)")
            return 10
    
    print(f"{'='*50}")
    print(f"  Final decision: {count} pages")
    print(f"{'='*50}")
    
    return max(1, count)

def create_temp_dir(base_path):
    """Create a temporary directory for intermediate files"""
    temp_dir = base_path / "temp_pdf_exports"
    temp_dir.mkdir(exist_ok=True)
    return temp_dir

def cleanup_temp_dir(temp_dir):
    """Clean up temporary directory"""
    try:
        # Remove all files in temp directory
        for file in temp_dir.glob("*"):
            try:
                file.unlink()
            except:
                pass
        
        # Remove the directory itself
        if temp_dir.exists():
            temp_dir.rmdir()
    except:
        pass

def sanitize_filename(filename):
    """Remove invalid characters from filename"""
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    return filename