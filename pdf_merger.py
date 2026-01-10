from pathlib import Path
from pypdf import PdfWriter, PdfReader
import os
import time
from utils import create_temp_dir, cleanup_temp_dir

class PDFMerger:
    def __init__(self):
        self.temp_files = []
    
    def merge_pdfs(self, pdf_files, output_path):
        """Merge multiple PDF files into one with proper page separation"""
        writer = PdfWriter()
        appended_count = 0
        
        print(f"\n{'='*60}")
        print(f"STARTING PDF MERGE - Creating book-like PDF")
        print(f"Files to merge: {len(pdf_files)}")
        print(f"{'='*60}")
        
        # Sort files to ensure correct order (by filename)
        pdf_files.sort(key=lambda x: str(x))
        
        for i, pdf_file in enumerate(pdf_files, 1):
            pdf_path = Path(pdf_file)
            
            # Check if file exists
            if not pdf_path.exists():
                print(f"[{i}] ✗ File not found: {pdf_path}")
                continue
            
            file_size = pdf_path.stat().st_size
            print(f"\n[{i}] Processing: {pdf_path.name} ({file_size:,} bytes)")
            
            if file_size == 0:
                print(f"  ⚠ Empty file, skipping")
                continue
            
            # Try to append the PDF
            try:
                # Open the PDF
                reader = PdfReader(str(pdf_path))
                num_pages = len(reader.pages)
                
                if num_pages == 0:
                    print(f"  ⚠ No pages in PDF")
                    continue
                
                print(f"  Found {num_pages} page(s) in this file")
                
                # IMPORTANT FIX: Add only the first page (not all pages)
                # Since each PDF file should represent ONE page
                if num_pages > 1:
                    print(f"  ⚠ Warning: PDF has {num_pages} pages, but we expected 1")
                    print(f"  Only adding the first page")
                    num_pages_to_add = 1
                else:
                    num_pages_to_add = num_pages
                
                # Add each page with its original dimensions
                for page_num in range(num_pages_to_add):
                    page = reader.pages[page_num]
                    
                    # Get page dimensions
                    media_box = page.mediabox
                    width = float(media_box.width)
                    height = float(media_box.height)
                    
                    # Debug output for first few pages
                    if appended_count < 3:  # Only show for first 3 pages
                        print(f"  Page {appended_count + 1}: {width:.1f} x {height:.1f} points "
                              f"({width/72:.1f} x {height/72:.1f} inches)")
                    
                    # IMPORTANT: Create a new page object to ensure clean separation
                    writer.add_page(page)
                    appended_count += 1
                
                print(f"  ✓ Added {num_pages_to_add} page(s) to final PDF")
                
            except Exception as e:
                print(f"  ✗ Error processing {pdf_path.name}: {e}")
                import traceback
                traceback.print_exc()
                # Try to add a blank page as placeholder
                try:
                    writer.add_blank_page(width=612, height=792)
                    appended_count += 1
                    print(f"  Added blank page as placeholder")
                except:
                    pass
        
        # Write merged PDF
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        print(f"\n{'='*60}")
        print(f"WRITING FINAL PDF")
        print(f"Output: {output_path}")
        print(f"Total pages written: {appended_count}")
        print(f"{'='*60}")
        
        try:
            with open(output_path, "wb") as f:
                writer.write(f)
            
            if output_path.exists():
                final_size = output_path.stat().st_size
                
                # Verify the final PDF
                try:
                    final_reader = PdfReader(str(output_path))
                    final_pages = len(final_reader.pages)
                    
                    print(f"\n📊 VERIFYING FINAL PDF:")
                    print(f"   Pages in final PDF: {final_pages}")
                    print(f"   Pages expected: {appended_count}")
                    
                    # Check dimensions of first few pages
                    print(f"\n📐 PAGE DIMENSIONS (first 3 pages):")
                    for i in range(min(3, final_pages)):
                        page = final_reader.pages[i]
                        media_box = page.mediabox
                        width = float(media_box.width)
                        height = float(media_box.height)
                        print(f"   Page {i+1}: {width:.1f} x {height:.1f} points "
                              f"({width/72:.1f} x {height/72:.1f} inches)")
                    
                    # Check if PDF is valid
                    if final_pages == appended_count:
                        print(f"\n✅ PDF VERIFICATION PASSED")
                        print(f"   All {final_pages} pages are properly separated")
                    else:
                        print(f"\n⚠ PDF VERIFICATION WARNING")
                        print(f"   Expected {appended_count} pages, got {final_pages}")
                
                except Exception as e:
                    final_pages = "unknown"
                    print(f"\n⚠ Could not verify final PDF: {e}")
                
                print(f"\n{'='*60}")
                print(f"🎉 MERGE COMPLETE")
                print(f"   Output file: {output_path}")
                print(f"   Total pages: {final_pages}")
                print(f"   File size: {final_size:,} bytes")
                print(f"   Size: {final_size/1024/1024:.2f} MB")
                print(f"{'='*60}")
                
                return output_path
            else:
                print(f"\n❌ Failed to create output file")
                return None
                
        except Exception as e:
            print(f"\n❌ Error writing PDF: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def process_svg_files(self, svg_files, output_path, dpi=150, rasterize=False):
        """
        Main processing function:
        1. Export SVG files to PDF
        2. Merge all PDFs into one file
        """
        from svg_processor import SVGProcessor
        
        start_time = time.time()
        
        # Create output directory if needed
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create temporary directory
        temp_dir = create_temp_dir(output_path.parent)
        print(f"\n📁 Temporary directory: {temp_dir}")
        
        # Initialize SVG processor
        svg_processor = SVGProcessor()
        
        all_pdf_files = []
        total_pages_attempted = 0
        total_pages_exported = 0
        
        # Process each SVG file
        for i, svg_file in enumerate(svg_files, 1):
            svg_path = Path(svg_file)
            print(f"\n{'='*60}")
            print(f"📄 Processing file {i}/{len(svg_files)}: {svg_path.name}")
            print(f"{'='*60}")
            
            try:
                # Get page count for this SVG
                num_pages = svg_processor.get_page_count(svg_path)
                total_pages_attempted += num_pages
                print(f"📊 Pages detected: {num_pages}")
                
                # Export pages for this SVG
                pdf_files = svg_processor.process_svg_file(svg_path, temp_dir, dpi, rasterize)
                
                if pdf_files:
                    # Filter out None or non-existent files
                    valid_files = [f for f in pdf_files if f and f.exists()]
                    all_pdf_files.extend(valid_files)
                    
                    # Count actual pages in each PDF
                    actual_pages = 0
                    for pdf_file in valid_files:
                        try:
                            reader = PdfReader(str(pdf_file))
                            actual_pages += len(reader.pages)
                        except:
                            actual_pages += 1  # Assume 1 page if can't read
                    
                    total_pages_exported += actual_pages
                    print(f"✓ Exported {len(valid_files)} PDF files containing {actual_pages} total pages")
                else:
                    print(f"✗ No pages exported from {svg_path.name}")
                
            except Exception as e:
                print(f"✗ Error processing {svg_path.name}: {e}")
                import traceback
                traceback.print_exc()
        
        print(f"\n{'='*60}")
        print(f"📊 SUMMARY")
        print(f"   Files processed: {len(svg_files)}")
        print(f"   Pages attempted: {total_pages_attempted}")
        print(f"   PDF files created: {len(all_pdf_files)}")
        print(f"   Total PDF pages to merge: {total_pages_exported}")
        print(f"{'='*60}")
        
        # Debug: Show all PDF files that will be merged
        if all_pdf_files:
            print(f"\n📋 LIST OF PDF FILES TO MERGE (in order):")
            for i, pdf_file in enumerate(all_pdf_files, 1):
                if pdf_file.exists():
                    size = pdf_file.stat().st_size
                    try:
                        reader = PdfReader(str(pdf_file))
                        pages = len(reader.pages)
                        print(f"  [{i:3d}] {pdf_file.name} ({pages} pages, {size:,} bytes)")
                    except:
                        print(f"  [{i:3d}] {pdf_file.name} ({size:,} bytes)")
                else:
                    print(f"  [{i:3d}] ✗ MISSING: {pdf_file}")
        
        # Merge all PDFs if any were created
        if all_pdf_files:
            print(f"\n🔄 Starting PDF merge process...")
            merged_path = self.merge_pdfs(all_pdf_files, output_path)
        else:
            print("\n❌ No PDF files were created. Cannot merge.")
            merged_path = None
        
        # Clean up temporary files
        print(f"\n🧹 Cleaning up temporary files...")
        cleanup_temp_dir(temp_dir)
        
        # Also clean up via processor
        svg_processor.cleanup_exported_files()
        
        total_time = time.time() - start_time
        print(f"\n⏱️  Total processing time: {total_time:.2f} seconds")
        
        return merged_path, total_pages_exported