import fitz
import re
import os
import glob


def highlight_pdf(input_file: str, strings: list[str], extractor_id: int) -> str:
    """
    Load the input_file PDF, search for the strings and highlight them in yellow.
    Write the highlighted version of the file name.pdf as name.marked.<extractor_id>.pdf

    Deletes any old marked-up versions of the file and includes the extractor_id in the filename.
    """
    
    # Generate output filename with extractor_id
    base_name = os.path.splitext(input_file)[0]
    output_file = f"{base_name}.marked.{extractor_id}.pdf"
    
    # Clean up any old marked files for this base document
    _cleanup_old_marked_files(base_name, extractor_id)
    
    # Open the PDF document
    pdf_doc = fitz.open(input_file)
    
    total_matches = 0
    
    # Iterate through each page
    for page_num in range(len(pdf_doc)):
        page = pdf_doc[page_num]
        
        # Search for each string on the current page
        for search_string in strings:
            # Find all instances of the search string on the page
            text_instances = page.search_for(search_string)
            
            # Highlight each instance found
            for inst in text_instances:
                # Add yellow highlight annotation
                highlight = page.add_highlight_annot(inst)
                highlight.set_colors(fill=(1, 1, 0))  # Yellow color
                highlight.update()
                total_matches += 1
    
    # Save the modified PDF
    pdf_doc.save(output_file)
    pdf_doc.close()
    
    return output_file


def extract_info(input_file: str):
    """
    Extracts file info
    """
    # Open the PDF
    pdfDoc = fitz.open(input_file)
    output = {
        "File": input_file, "Encrypted": ("True" if pdfDoc.is_encrypted else "False")
    }
    # If PDF is encrypted the file metadata cannot be extracted
    if not pdfDoc.is_encrypted:
        for key, value in pdfDoc.metadata.items():
            output[key] = value
    # To Display File Info
    print("## File Information ##################################################")
    print("\n".join("{}:{}".format(i, j) for i, j in output.items()))
    print("######################################################################")
    return True, output


def search_for_text(lines, search_str):
    """
    Search for the search string within the document lines
    """
    for line in lines:
        # Find all matches within one line
        results = re.findall(search_str, line, re.IGNORECASE)
        # In case multiple matches within one line
        for result in results:
            yield result


def highlight_matching_data(page, matched_values, type):
    """
    Highlight matching values
    """
    matches_found = 0
    # Loop throughout matching values
    for val in matched_values:
        matches_found += 1
        matching_val_area = page.searchFor(val)
        # print("matching_val_area",matching_val_area)
        highlight = None
        if type == 'Highlight':
            highlight = page.addHighlightAnnot(matching_val_area)
        elif type == 'Squiggly':
            highlight = page.addSquigglyAnnot(matching_val_area)
        elif type == 'Underline':
            highlight = page.addUnderlineAnnot(matching_val_area)
        elif type == 'Strikeout':
            highlight = page.addStrikeoutAnnot(matching_val_area)
        else:
            highlight = page.addHighlightAnnot(matching_val_area)
        # To change the highlight colar
        # highlight.setColors({"stroke":(0,0,1),"fill":(0.75,0.8,0.95) })
        # highlight.setColors(stroke = fitz.utils.getColor('white'), fill = fitz.utils.getColor('red'))
        # highlight.setColors(colors= fitz.utils.getColor('red'))
        highlight.update()
    return matches_found


def _cleanup_old_marked_files(base_name: str, extractor_id: int) -> None:
    """
    Delete any old marked-up versions of the file for the specific extractor_id.
    
    Args:
        base_name: Base filename without extension (e.g., "/path/to/document")
        extractor_id: Extractor ID - only files with this specific ID will be cleaned up
    """
    # Pattern to match marked files for this specific document and extractor_id
    pattern = f"{base_name}.marked.{extractor_id}.pdf"
    
    # Find existing marked file for this specific combination
    if os.path.exists(pattern):
        try:
            os.remove(pattern)
            print(f"Cleaned up existing marked file: {pattern}")
        except OSError as e:
            print(f"Warning: Could not remove existing marked file {pattern}: {e}")


def get_marked_files(input_file: str, extractor_id: int = None) -> list[str]:
    """
    Get a list of marked versions of a given input file.
    
    Args:
        input_file: Path to the original PDF file
        extractor_id: If provided, only return files for this extractor_id
        
    Returns:
        List of paths to marked versions of the file
    """
    base_name = os.path.splitext(input_file)[0]
    
    if extractor_id is not None:
        # Return only files for specific extractor_id
        pattern = f"{base_name}.marked.{extractor_id}.pdf"
        return glob.glob(pattern)
    else:
        # Return all marked files for this document
        pattern = f"{base_name}.marked.*.pdf"
        return glob.glob(pattern)
