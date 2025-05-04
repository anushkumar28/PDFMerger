"""
PDF Merger utility module.

This module provides functionality to merge multiple PDF files into a single PDF document.
"""
import os
import logging
from pypdf import PdfReader, PdfWriter

# Get a named logger for this module
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
    Merge multiple PDF files into a single PDF file.

    Args:
        input_paths (list): List of paths to PDF files to merge
        output_path (str): Path where the merged PDF should be saved
        output_filename (str, optional): Custom filename for the merged PDF

    Returns:
        dict: Dictionary with success status, path, and error message if any
    """
    try:
        # Validate input paths
        if not input_paths or len(input_paths) < 2:
            logger.error("At least two PDF files are required for merging")
            return {
                'success': False,
                'path': None,
                'error': 'At least two PDF files are required for merging'
            }

        # Check if all input files exist without path restrictions
        missing_files = [path for path in input_paths if not os.path.exists(path)]
        if missing_files:
            missing_list = ', '.join(missing_files)
            logger.error("The following files do not exist: %s", missing_list)
            return {
                'success': False,
                'path': None,
                'error': 'The following files do not exist: ' + missing_list
            }

        # Initialize PDF writer
        pdf_writer = PdfWriter()

        # Read and append each PDF
        for path in input_paths:
            try:
                logger.info("Processing file: %s", path)

                # Check if file is readable
                if not os.access(path, os.R_OK):
                    logger.error("No read permission for file: %s", path)
                    return {
                        'success': False,
                        'path': None,
                        'error': 'Cannot read file ' + os.path.basename(path)
                    }

                # Check if file size is not zero
                if os.path.getsize(path) == 0:
                    logger.error("File is empty: %s", path)
                    return {
                        'success': False,
                        'path': None,
                        'error': 'File is empty: ' + os.path.basename(path)
                    }

                # Try to open and read the PDF file
                with open(path, 'rb') as pdf_file:
                    pdf_reader = PdfReader(pdf_file)
                    page_count = len(pdf_reader.pages)
                    logger.info("Found %d pages in %s", page_count, path)

                    # Add each page to the writer
                    for page in pdf_reader.pages:
                        pdf_writer.add_page(page)

            except (IOError, OSError, ValueError, TypeError) as ex:
                logger.error("Error processing file %s: %s", path, str(ex))
                return {
                    'success': False,
                    'path': None,
                    'error': 'Error processing ' + os.path.basename(path) + ': ' + str(ex)
                }

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
        logger.info("Writing merged PDF to: %s", final_output_path)
        try:
            with open(final_output_path, 'wb') as output_file:
                pdf_writer.write(output_file)
        except (IOError, OSError) as ex:
            logger.error("Error writing merged PDF to %s: %s", final_output_path, str(ex))
            return {
                'success': False,
                'path': None,
                'error': 'Error writing output file: ' + str(ex)
            }

        # Verify the file was created
        if not os.path.exists(final_output_path):
            logger.error("Output file was not created: %s", final_output_path)
            return {
                'success': False,
                'path': None,
                'error': 'Failed to create merged PDF file'
            }

        if os.path.getsize(final_output_path) == 0:
            logger.error("Output file is empty: %s", final_output_path)
            return {
                'success': False,
                'path': None,
                'error': 'Output PDF file is empty'
            }

        logger.info("Successfully created merged PDF: %s", final_output_path)
        return {'success': True, 'path': final_output_path, 'error': None}

    except (IOError, OSError) as ex:
        logger.error("File I/O error while merging PDFs: %s", str(ex))
        return {
            'success': False,
            'path': None,
            'error': 'File error merging PDFs: ' + str(ex)
        }
    except ValueError as ex:
        logger.error("Value error while merging PDFs: %s", str(ex))
        return {
            'success': False,
            'path': None,
            'error': 'Invalid value error merging PDFs: ' + str(ex)
        }
    except TypeError as ex:
        logger.error("Type error while merging PDFs: %s", str(ex))
        return {
            'success': False,
            'path': None,
            'error': 'Type error merging PDFs: ' + str(ex)
        }
