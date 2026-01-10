import tkinter as tk
import sys
from pathlib import Path

def debug_mode():
    """Run in debug mode to analyze SVG files"""
    if len(sys.argv) > 1 and sys.argv[1] == "--debug":
        try:
            from utils import analyze_svg_structure
            from svg_processor import SVGProcessor
        except ImportError as e:
            print(f"Import error: {e}")
            return True
        
        files = sys.argv[2:] if len(sys.argv) > 2 else []
        
        if files:
            for file in files:
                svg_path = Path(file)
                if svg_path.exists():
                    print(f"\n{'='*60}")
                    print(f"DEBUGGING: {svg_path.name}")
                    print(f"{'='*60}")
                    
                    # Analyze SVG structure
                    analyze_svg_structure(svg_path)
                    
                    # Try to detect pages
                    processor = SVGProcessor()
                    pages = processor.get_page_count(svg_path)
                    print(f"\nDetected pages: {pages}")
                    
                    # Get file size
                    file_size = svg_path.stat().st_size
                    print(f"File size: {file_size:,} bytes")
                    
                    # Try simple export test
                    print(f"\nTrying simple export test...")
                    try:
                        from utils import create_temp_dir
                        temp_dir = create_temp_dir(svg_path.parent)
                        result = processor.process_svg_file(svg_path, temp_dir, dpi=150, rasterize=False)
                        print(f"Export result: {len(result) if result else 0} files")
                        
                        # Clean up
                        from utils import cleanup_temp_dir
                        cleanup_temp_dir(temp_dir)
                    except Exception as e:
                        print(f"Export test failed: {e}")
                    
                    print(f"{'='*60}")
                else:
                    print(f"File not found: {file}")
        else:
            print("No files specified for debugging")
            print("Usage: python main.py --debug file1.svg file2.svg ...")
        return True
    return False

def main():
    """Main entry point for the application"""
    # Check for debug mode
    if debug_mode():
        return
    
    # Normal GUI mode
    from gui import SVGPDFMergerGUI
    
    root = tk.Tk()
    app = SVGPDFMergerGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()