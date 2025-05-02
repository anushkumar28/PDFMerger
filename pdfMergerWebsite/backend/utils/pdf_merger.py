import os
import logging
import traceback
from pypdf import PdfReader, PdfWriter, errors

logger = logging.getLogger(__name__)

# Configure logging if not already configured
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

def merge_pdfs(input_paths, output_path, output_filename=None):
    """
    Merge multiple PDF files into a single PDF file using pypdf.
    
    Args:
        input_paths (list): List of paths to PDF files to merge
        output_path (str): Path where the merged PDF should be saved
        output_filename (str, optional): Custom filename for the merged PDF.
                                       If provided, will override the filename portion of output_path
    
    Returns:
        dict: Dictionary containing:
            - 'success': bool indicating if merge was successful
            - 'path': Path to the merged file if successful
            - 'error': Error message if unsuccessful
    """
    try:
        # Validate input paths
        if not input_paths or len(input_paths) < 2:
            logger.error("At least two PDF files are required for merging")
            return {'success': False, 'path': None, 'error': 'At least two PDF files are required for merging'}
        
        # Security check: Ensure all paths are within allowed directory
        allowed_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'static', 'uploads'))
        for path in input_paths:
            abs_path = os.path.abspath(path)
            if not abs_path.startswith(allowed_dir):
                logger.error(f"Invalid file path: {path}")
                return {'success': False, 'path': None, 'error': 'Invalid file path'}
        
        # Check if all input files exist
        missing_files = [path for path in input_paths if not os.path.exists(path)]
        if missing_files:
            missing_list = ', '.join(missing_files)
            logger.error(f"The following files do not exist: {missing_list}")
            return {'success': False, 'path': None, 'error': f'The following files do not exist: {missing_list}'}
        
        # Initialize PDF writer
        pdf_writer = PdfWriter()
        
        # Read and append each PDF
        for path in input_paths:
            try:
                logger.info(f"Processing file: {path}")
                
                # Check if file is readable
                if not os.access(path, os.R_OK):
                    logger.error(f"No read permission for file: {path}")
                    return {'success': False, 'path': None, 'error': f'Cannot read file {os.path.basename(path)}'}
                
                # Check if file size is not zero
                if os.path.getsize(path) == 0:
                    logger.error(f"File is empty: {path}")
                    return {'success': False, 'path': None, 'error': f'File is empty: {os.path.basename(path)}'}
                
                # Set resource limits to prevent DoS
                pdf_reader = PdfReader(path, strict=True)
                
                # Limit number of pages per PDF (optional)
                max_pages = 500
                if len(pdf_reader.pages) > max_pages:
                    logger.error(f"PDF exceeds maximum page limit of {max_pages}: {path}")
                    return {'success': False, 'path': None, 'error': f'PDF exceeds maximum page limit of {max_pages}'}
                
                # Add each page to the writer
                for page in pdf_reader.pages:
                    pdf_writer.add_page(page)
                
            except errors.PdfReadError as e:
                logger.error(f"Error reading PDF file {path}: {str(e)}")
                return {'success': False, 'path': None, 'error': f'Invalid PDF file {os.path.basename(path)}: {str(e)}'}
            except Exception as e:
                logger.error(f"Unexpected error processing PDF file {path}: {str(e)}")
                logger.error(traceback.format_exc())
                return {'success': False, 'path': None, 'error': f'Error processing {os.path.basename(path)}: {str(e)}'}
        
        # Handle custom filename if provided
        final_output_path = output_path
        if output_filename:
            output_dir = os.path.dirname(output_path)
            if not output_filename.lower().endswith('.pdf'):
                output_filename += '.pdf'
            final_output_path = os.path.join(output_dir, output_filename)
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(os.path.abspath(final_output_path)), exist_ok=True)
        
        # Write the merged PDF
        logger.info(f"Writing merged PDF to: {final_output_path}")
        try:
            with open(final_output_path, 'wb') as output_file:
                pdf_writer.write(output_file)
        except Exception as e:
            logger.error(f"Error writing merged PDF to {final_output_path}: {str(e)}")
            logger.error(traceback.format_exc())
            return {'success': False, 'path': None, 'error': f'Error writing output file: {str(e)}'}
        
        # Verify the file was created
        if not os.path.exists(final_output_path):
            logger.error(f"Output file was not created: {final_output_path}")
            return {'success': False, 'path': None, 'error': 'Failed to create merged PDF file'}
        
        if os.path.getsize(final_output_path) == 0:
            logger.error(f"Output file is empty: {final_output_path}")
            return {'success': False, 'path': None, 'error': 'Output PDF file is empty'}
        
        logger.info(f"Successfully created merged PDF: {final_output_path}")
        return {'success': True, 'path': final_output_path, 'error': None}
        
    except Exception as e:
        logger.error(f"Unexpected error merging PDFs: {str(e)}")
        logger.error(traceback.format_exc())
        return {'success': False, 'path': None, 'error': f'Error merging PDFs: {str(e)}'}