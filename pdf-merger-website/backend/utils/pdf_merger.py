from PyPDF2 import PdfMerger
import os
import traceback

def merge_pdfs(input_paths, output_path, output_filename=None):
    """
    Merge multiple PDF files into a single PDF file
    
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
        print(f"Starting to merge PDFs. Input paths: {input_paths}")
        print(f"Original output path: {output_path}")
        
        # Handle custom filename if provided
        if output_filename:
            # Ensure filename has .pdf extension
            if not output_filename.lower().endswith('.pdf'):
                output_filename += '.pdf'
                
            # Replace the filename portion of the output path
            output_dir = os.path.dirname(output_path)
            output_path = os.path.join(output_dir, output_filename)
            print(f"Custom filename provided. New output path: {output_path}")
        
        # Validate input paths
        valid_paths = []
        for pdf_file in input_paths:
            if not os.path.exists(pdf_file):
                print(f"Warning: File {pdf_file} not found and will be skipped.")
                continue
            if not os.path.isfile(pdf_file):
                print(f"Warning: Path {pdf_file} is not a file and will be skipped.")
                continue
                
            # Check if file is readable
            try:
                with open(pdf_file, 'rb') as f:
                    f.read(1024)  # Try to read a small part
                valid_paths.append(pdf_file)
            except Exception as e:
                print(f"Warning: File {pdf_file} cannot be read: {str(e)}")
                
        if not valid_paths:
            print("Error: No valid PDF files to merge!")
            return {'success': False, 'error': 'No valid PDF files to merge', 'path': None}
            
        print(f"Valid paths for merging: {valid_paths}")
        
        # Create merger object
        merger = PdfMerger()
        
        # Add each PDF file to the merger
        for pdf_file in valid_paths:
            print(f"Adding {pdf_file} to merger...")
            merger.append(pdf_file)
        
        # Ensure the output directory exists
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
            
        # Write the merged PDF to the output file
        print(f"Writing merged PDF to {output_path}")
        merger.write(output_path)
        merger.close()
        
        # Verify the output file was created
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            print(f"Successfully merged {len(valid_paths)} PDFs into {output_path}")
            return {'success': True, 'path': output_path, 'error': None}
        else:
            print(f"Error: Output file {output_path} was not created or is empty")
            return {'success': False, 'error': 'Output file was not created or is empty', 'path': None}
            
    except Exception as e:
        error_msg = f"Error merging PDFs: {str(e)}"
        print(error_msg)
        traceback.print_exc()
        return {'success': False, 'error': error_msg, 'path': None}