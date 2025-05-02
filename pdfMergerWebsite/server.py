from flask import Flask, request, jsonify, send_from_directory, after_this_request
from flask_cors import CORS
import os
import traceback
from backend.utils.pdf_merger import merge_pdfs
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import logging
from werkzeug.utils import secure_filename
import secrets
import threading
import time

app = Flask(__name__, static_folder='frontend')
CORS(app)

UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max upload

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Add structured error handling with proper logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='pdf_merger.log'
)
logger = logging.getLogger('pdf_merger')

# Update your rate limiting configuration
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"  # For production, consider Redis or another persistent backend
)

# At the start of your server.py file
try:
    # Create upload directory if it doesn't exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Test write permissions
    test_file = os.path.join(app.config['UPLOAD_FOLDER'], 'test_write.txt')
    with open(test_file, 'w') as f:
        f.write('test')
    os.remove(test_file)
    logger.info(f"Upload directory is writable: {app.config['UPLOAD_FOLDER']}")
except Exception as e:
    logger.error(f"ERROR: Cannot write to upload directory: {str(e)}", exc_info=True)
    # This will help identify permission issues at startup

# Track files to clean up
uploaded_file_tracker = {}

@app.route('/')
def index():
    return send_from_directory('frontend', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('frontend', path)

# If needed, add a specific route for the manifest
@app.route('/manifest.json')
def serve_manifest():
    return send_from_directory(app.static_folder, 'manifest.json')

# Implement more secure file validation
def is_safe_pdf(file_path):
    """Validate if a file is a real PDF and not malicious"""
    try:
        with open(file_path, 'rb') as f:
            header = f.read(5)
            # Check for PDF magic number
            return header == b'%PDF-'
    except:
        return False

# Add this function to validate uploaded files
def validate_pdf_file(file):
    """Validate that the uploaded file is actually a PDF."""
    # Check MIME type
    if not file.content_type == 'application/pdf':
        return False
        
    # Check file signature (magic bytes)
    file_content = file.read(5)
    file.seek(0)  # Reset file pointer
    
    # PDF files start with %PDF-
    return file_content.startswith(b'%PDF-')

# Generate a secure random token for filenames
def generate_secure_filename(filename):
    """Generate a secure filename with a random token."""
    secure_name = secure_filename(filename)
    random_token = secrets.token_hex(8)
    name, ext = os.path.splitext(secure_name)
    return f"{name}_{random_token}{ext}"

# Add specific limits to sensitive routes
@app.route('/upload', methods=['POST'])
@limiter.limit("10 per minute")
def upload_files():
    try:
        logger.info("Files in request: %s", list(request.files.keys()))
        
        if 'files' not in request.files:
            logger.info("No 'files' part in request")
            return jsonify({'error': 'No files part'}), 400

        files = request.files.getlist('files')
        logger.info("Number of files received: %d", len(files))
        
        if len(files) < 2:
            logger.info("Need at least 2 files to merge")
            return jsonify({'error': 'Need at least 2 PDF files to merge'}), 400
        
        pdf_paths = []

        for file in files:
            if file and file.filename.endswith('.pdf'):
                filename = generate_secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                
                # Validate PDF after saving
                if not is_safe_pdf(file_path):
                    os.remove(file_path)  # Remove potentially malicious file
                    return jsonify({'error': 'Invalid or potentially unsafe PDF file'}), 400
                
                # Verify the file was saved
                if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                    pdf_paths.append(file_path)
                    logger.info("Successfully saved file: %s", file_path)
                else:
                    logger.info("Failed to save file or file is empty: %s", file_path)
                    return jsonify({'error': f'Failed to save file: {filename}'}), 500
            else:
                logger.info("Invalid file: %s", file.filename if file else 'None')
                return jsonify({'error': 'Only PDF files are allowed'}), 400

        if not pdf_paths or len(pdf_paths) < 2:
            logger.info("No valid PDF files were uploaded")
            return jsonify({'error': 'No valid PDF files were uploaded'}), 400

        # Get custom filename if provided or generate a default one
        output_filename = None
        if 'output_filename' in request.form and request.form['output_filename'].strip():
            output_filename = request.form['output_filename'].strip()
            logger.info("Custom filename provided: %s", output_filename)
        else:
            # Generate a unique output filename
            import uuid
            output_filename = f"merged_document_{uuid.uuid4().hex[:8]}"
        
        # Make sure it has .pdf extension
        if not output_filename.lower().endswith('.pdf'):
            output_filename += '.pdf'
            
        output_path = os.path.join(app.config['UPLOAD_FOLDER'], 'merged_document.pdf') # Use a default base name
        
        logger.info("Attempting to merge PDFs to: %s with custom name: %s", output_path, output_filename)

        # Change this line to pass the output_filename parameter
        merge_result = merge_pdfs(pdf_paths, output_path, output_filename)
        logger.info("Merge result: %s", merge_result)
        
        if merge_result['success']:
            merged_filename = os.path.basename(merge_result["path"])
            download_link = f'/download/{merged_filename}'
            
            # Store files to clean up later
            uploaded_file_tracker[merged_filename] = {
                'input_paths': pdf_paths,
                'merged_path': merge_result["path"]
            }
            
            logger.info("Success! Download link: %s", download_link)
            return jsonify({
                'message': 'Files merged successfully', 
                'download_link': download_link
            }), 200
        else:
            # Clean up input files on failure
            for path in pdf_paths:
                try:
                    if os.path.exists(path):
                        os.remove(path)
                        logger.info("Removed uploaded file: %s", path)
                except Exception as e:
                    logger.error(f"Error removing file {path}: {str(e)}", exc_info=True)
                    
            logger.info("Error merging files: %s", merge_result['error'])
            return jsonify({'error': merge_result['error'] or 'Error merging files'}), 500
    except Exception as e:
        # Clean up any uploaded files on exception
        for path in pdf_paths if 'pdf_paths' in locals() else []:
            try:
                if os.path.exists(path):
                    os.remove(path)
                    logger.info("Removed uploaded file: %s", path)
            except Exception as remove_err:
                logger.error(f"Error removing file {path}: {str(remove_err)}", exc_info=True)
                
        logger.error(f"Exception in upload_files: {str(e)}", exc_info=True)
        traceback.print_exc()
        return jsonify({'error': f'Server error: {str(e)}'}), 500

# Also fix the download route to handle potential errors
@app.route('/download/<filename>')
def download_file(filename):
    # Validate filename to prevent path traversal
    if not os.path.basename(filename) == filename:
        return "Invalid filename", 400
        
    # Serve the file
    response = send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)
    
    # Schedule cleanup
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    delayed_file_cleanup(file_path)
    
    return response

# Implement file cleanup with secure deletion
def secure_delete(file_path):
    """More secure file deletion by overwriting before deleting"""
    if os.path.exists(file_path):
        # Get file size
        file_size = os.path.getsize(file_path)
        
        # Overwrite with random data
        with open(file_path, 'wb') as f:
            f.write(os.urandom(file_size))
            
        # Delete the file
        os.remove(file_path)
        logger.info(f"Securely deleted {file_path}")

def delayed_file_cleanup(file_path, delay=300):
    """Delete a file after a specified delay (in seconds)."""
    def delete_file():
        time.sleep(delay)
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"Deleted temporary file: {file_path}")
        except Exception as e:
            print(f"Error deleting file {file_path}: {e}")
    
    # Start a background thread to delete the file
    thread = threading.Thread(target=delete_file)
    thread.daemon = True
    thread.start()

@app.after_request
def add_security_headers(response):
    """Add security headers to all responses."""
    # Content Security Policy
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' https://cdnjs.cloudflare.com; "
        "font-src 'self' https://cdnjs.cloudflare.com; "
        "img-src 'self' data:; "
        "object-src 'none'"
    )
    
    # Prevent MIME type sniffing
    response.headers['X-Content-Type-Options'] = 'nosniff'
    
    # Prevent clickjacking
    response.headers['X-Frame-Options'] = 'DENY'
    
    # Enable XSS protection
    response.headers['X-XSS-Protection'] = '1; mode=block'
    
    # Control referrer information
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    
    return response

if __name__ == '__main__':
    app.run(debug=True)