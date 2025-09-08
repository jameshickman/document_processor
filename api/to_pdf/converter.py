import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any
import logging

# Import libraries for different conversion methods
try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.utils import ImageReader
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ConversionError(Exception):
    """Custom exception for conversion errors"""
    pass


def to_pdf(source_file: str) -> str:
    """
    Convert the input file to a PDF using the most appropriate method.
    Use the same filename, replace the extension with pdf.
    Write the converted file to the same location as the source.

    Supports: DOCX, TXT, HTML, MD, RTF, images (JPEG, PNG, TIFF, BMP, GIF)
    
    Args:
        source_file: Path to the source file to convert
        
    Returns:
        str: Path to the generated PDF file
        
    Raises:
        ConversionError: If conversion fails
        FileNotFoundError: If source file doesn't exist
    """
    if not os.path.exists(source_file):
        raise FileNotFoundError(f"Source file not found: {source_file}")
    
    source_path = Path(source_file)
    output_file = str(source_path.with_suffix('.pdf'))
    
    # Get file extension
    extension = source_path.suffix.lower()
    
    # Choose conversion method based on file type
    if extension in ['.txt', '.text']:
        _convert_text_to_pdf(source_file, output_file)
    elif extension in ['.html', '.htm']:
        _convert_html_to_pdf(source_file, output_file)
    elif extension in ['.md', '.markdown']:
        _convert_markdown_to_pdf(source_file, output_file)
    elif extension in ['.docx', '.doc']:
        _convert_office_to_pdf(source_file, output_file)
    elif extension in ['.rtf']:
        _convert_rtf_to_pdf(source_file, output_file)
    elif extension in ['.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp', '.gif']:
        _convert_image_to_pdf(source_file, output_file)
    else:
        # Try pandoc as fallback
        _convert_with_pandoc(source_file, output_file)
    
    if not os.path.exists(output_file):
        raise ConversionError(f"Failed to create PDF: {output_file}")
    
    return output_file


def _convert_text_to_pdf(source_file: str, output_file: str) -> None:
    """Convert plain text file to PDF using ReportLab"""
    if not REPORTLAB_AVAILABLE:
        _convert_with_pandoc(source_file, output_file)
        return
    
    try:
        with open(source_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        doc = SimpleDocTemplate(output_file, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        
        # Split content into paragraphs
        paragraphs = content.split('\n\n')
        for para in paragraphs:
            if para.strip():
                # Replace single newlines with spaces, preserve paragraph breaks
                para = para.replace('\n', ' ')
                story.append(Paragraph(para, styles['Normal']))
                story.append(Spacer(1, 12))
        
        doc.build(story)
        logger.info(f"Converted text file to PDF: {output_file}")
        
    except Exception as e:
        logger.error(f"Error converting text to PDF: {e}")
        raise ConversionError(f"Text to PDF conversion failed: {e}")


def _convert_html_to_pdf(source_file: str, output_file: str) -> None:
    """Convert HTML file to PDF using wkhtmltopdf or pandoc"""
    # Try wkhtmltopdf first
    if _check_command_exists('wkhtmltopdf'):
        try:
            subprocess.run([
                'wkhtmltopdf', 
                '--page-size', 'A4',
                '--encoding', 'UTF-8',
                source_file, 
                output_file
            ], check=True, capture_output=True)
            logger.info(f"Converted HTML to PDF using wkhtmltopdf: {output_file}")
            return
        except subprocess.CalledProcessError as e:
            logger.warning(f"wkhtmltopdf failed: {e}")
    
    # Fallback to pandoc
    _convert_with_pandoc(source_file, output_file)


def _convert_markdown_to_pdf(source_file: str, output_file: str) -> None:
    """Convert Markdown file to PDF using pandoc"""
    _convert_with_pandoc(source_file, output_file, extra_args=['--from', 'markdown'])


def _convert_office_to_pdf(source_file: str, output_file: str) -> None:
    """Convert Office documents (DOCX, DOC) to PDF"""
    # Try LibreOffice first
    if _check_command_exists('libreoffice'):
        try:
            # Get output directory
            output_dir = os.path.dirname(output_file)
            
            subprocess.run([
                'libreoffice',
                '--headless',
                '--convert-to', 'pdf',
                '--outdir', output_dir,
                source_file
            ], check=True, capture_output=True)
            
            # LibreOffice creates PDF with same name as source
            source_name = Path(source_file).stem
            generated_pdf = os.path.join(output_dir, f"{source_name}.pdf")
            
            # Rename if different from expected output
            if generated_pdf != output_file:
                os.rename(generated_pdf, output_file)
            
            logger.info(f"Converted Office document to PDF using LibreOffice: {output_file}")
            return
            
        except subprocess.CalledProcessError as e:
            logger.warning(f"LibreOffice conversion failed: {e}")
    
    # Fallback to pandoc
    _convert_with_pandoc(source_file, output_file)


def _convert_rtf_to_pdf(source_file: str, output_file: str) -> None:
    """Convert RTF file to PDF using pandoc"""
    _convert_with_pandoc(source_file, output_file, extra_args=['--from', 'rtf'])


def _convert_image_to_pdf(source_file: str, output_file: str) -> None:
    """Convert image file to PDF"""
    if PIL_AVAILABLE and REPORTLAB_AVAILABLE:
        _convert_image_with_reportlab(source_file, output_file)
    elif PYMUPDF_AVAILABLE:
        _convert_image_with_pymupdf(source_file, output_file)
    else:
        raise ConversionError("No image conversion library available (PIL/ReportLab or PyMuPDF required)")


def _convert_image_with_reportlab(source_file: str, output_file: str) -> None:
    """Convert image to PDF using ReportLab"""
    try:
        # Open and process image
        with Image.open(source_file) as img:
            # Convert to RGB if necessary
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Create PDF
            c = canvas.Canvas(output_file, pagesize=letter)
            page_width, page_height = letter
            
            # Calculate image dimensions to fit page with margins
            margin = 50
            max_width = page_width - 2 * margin
            max_height = page_height - 2 * margin
            
            img_width, img_height = img.size
            
            # Scale image to fit page
            scale_w = max_width / img_width
            scale_h = max_height / img_height
            scale = min(scale_w, scale_h)
            
            final_width = img_width * scale
            final_height = img_height * scale
            
            # Center image on page
            x = (page_width - final_width) / 2
            y = (page_height - final_height) / 2
            
            # Save image to temporary file for ReportLab
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_img:
                img.save(temp_img.name, 'JPEG')
                c.drawImage(temp_img.name, x, y, final_width, final_height)
                os.unlink(temp_img.name)
        
        c.save()
        logger.info(f"Converted image to PDF using ReportLab: {output_file}")
        
    except Exception as e:
        logger.error(f"Error converting image to PDF: {e}")
        raise ConversionError(f"Image to PDF conversion failed: {e}")


def _convert_image_with_pymupdf(source_file: str, output_file: str) -> None:
    """Convert image to PDF using PyMuPDF"""
    try:
        doc = fitz.open()  # Create new PDF document
        
        # Open image and get dimensions
        img = fitz.open(source_file)
        pix = img[0].get_pixmap()
        
        # Create page with image dimensions
        page = doc.new_page(width=pix.width, height=pix.height)
        
        # Insert image
        page.insert_image(page.rect, filename=source_file)
        
        # Save PDF
        doc.save(output_file)
        doc.close()
        img.close()
        
        logger.info(f"Converted image to PDF using PyMuPDF: {output_file}")
        
    except Exception as e:
        logger.error(f"Error converting image to PDF with PyMuPDF: {e}")
        raise ConversionError(f"Image to PDF conversion failed: {e}")


def _convert_with_pandoc(source_file: str, output_file: str, extra_args: Optional[list] = None) -> None:
    """Convert file to PDF using Pandoc"""
    if not _check_command_exists('pandoc'):
        raise ConversionError("Pandoc is not available and no alternative conversion method found")
    
    try:
        cmd = ['pandoc', source_file, '-o', output_file]
        if extra_args:
            cmd.extend(extra_args)
        
        subprocess.run(cmd, check=True, capture_output=True)
        logger.info(f"Converted file to PDF using Pandoc: {output_file}")
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Pandoc conversion failed: {e}")
        raise ConversionError(f"Pandoc conversion failed: {e}")


def _check_command_exists(command: str) -> bool:
    """Check if a command exists in the system PATH"""
    try:
        subprocess.run([command, '--version'], 
                      capture_output=True, 
                      check=True, 
                      timeout=10)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return False


def get_supported_formats() -> Dict[str, list]:
    """
    Get list of supported input formats
    
    Returns:
        Dict mapping format categories to file extensions
    """
    formats = {
        'text': ['.txt', '.text'],
        'markup': ['.html', '.htm', '.md', '.markdown'],
        'office': ['.docx', '.doc', '.rtf'],
        'images': ['.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp', '.gif']
    }
    
    # Add conditional formats based on available tools
    available_formats = {}
    for category, extensions in formats.items():
        available_formats[category] = extensions
    
    return available_formats


def get_conversion_info() -> Dict[str, Any]:
    """
    Get information about available conversion tools and capabilities
    
    Returns:
        Dict with tool availability and capabilities
    """
    info = {
        'libraries': {
            'reportlab': REPORTLAB_AVAILABLE,
            'pillow': PIL_AVAILABLE,
            'pymupdf': PYMUPDF_AVAILABLE
        },
        'tools': {
            'pandoc': _check_command_exists('pandoc'),
            'libreoffice': _check_command_exists('libreoffice'),
            'wkhtmltopdf': _check_command_exists('wkhtmltopdf')
        },
        'supported_formats': get_supported_formats()
    }
    
    return info