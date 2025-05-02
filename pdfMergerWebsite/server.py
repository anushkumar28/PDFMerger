from flask import Flask, request, jsonify, send_file, send_from_directory, abort, render_template, after_this_request
from flask_cors import CORS
import os
import traceback
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import logging
from werkzeug.utils import secure_filename
import secrets
import threading
import time
import uuid
import io
from pypdf import PdfReader, PdfWriter

app = Flask(__name__, static_folder='frontend')
CORS(app)

# Configure upload folder with absolute path for reliability
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
OUTPUT_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'output')

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max upload

# Ensure directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

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
    # Generate a random nonce for this request
    nonce = secrets.token_hex(16)
    
    # Render template with nonce
    return render_template('index.html', nonce=nonce)

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

# Dictionary to store in-memory PDF data with expiration logic
# This replaces file storage entirely
pdf_memory_store = {}

@app.route('/upload', methods=['POST'])
@limiter.limit("10 per minute")
def upload_file():
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
        
        # Process PDFs entirely in memory
        pdf_readers = []
        
        for file in files:
            if file and file.filename.lower().endswith('.pdf'):
                # Read file directly into memory
                pdf_content = io.BytesIO(file.read())
                try:
                    # Validate PDF content
                    pdf_reader = PdfReader(pdf_content)
                    pdf_readers.append(pdf_reader)
                except Exception as e:
                    logger.error(f"Invalid PDF file {file.filename}: {str(e)}")
                    return jsonify({'error': f'Invalid PDF file {file.filename}: {str(e)}'}), 400
            else:
                logger.error(f"Invalid file: {file.filename}")
                return jsonify({'error': f'Invalid file format: {file.filename}. Only PDF files are allowed.'}), 400

        # Generate output filename
        output_filename = request.form.get('output_filename', 'merged_document')
        if not output_filename:
            output_filename = 'merged_document'
            
        # Add unique ID
        unique_id = str(uuid.uuid4())[:8]
        output_filename = f"{output_filename}_{unique_id}.pdf"
        
        # Create merged PDF in memory
        pdf_writer = PdfWriter()
        
        # Add all pages from all PDFs
        for reader in pdf_readers:
            for page in reader.pages:
                pdf_writer.add_page(page)
                
        # Write PDF to in-memory buffer
        output_buffer = io.BytesIO()
        pdf_writer.write(output_buffer)
        output_buffer.seek(0)
        
        # Store in memory instead of filesystem
        pdf_memory_store[unique_id] = {
            'data': output_buffer,
            'filename': output_filename
        }
        
        logger.info(f"Merge successful. Created in-memory PDF with ID: {unique_id}")
        
        # Create download link with the unique ID as identifier
        download_link = f"/download/{unique_id}"
        
        return jsonify({
            'message': 'Files merged successfully',
            'download_link': download_link
        })
            
    except Exception as e:
        logger.exception(f"Error in upload handler: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/download/<unique_id>')
def download_file(unique_id):
    try:
        # Check if the ID exists in our in-memory store
        if unique_id not in pdf_memory_store:
            logger.error(f"PDF with ID {unique_id} not found in memory store")
            return jsonify({'error': 'File not found or has expired'}), 404
            
        # Get the PDF data from memory
        pdf_data = pdf_memory_store[unique_id]['data']
        filename = pdf_memory_store[unique_id]['filename']
        
        # Send file directly from memory
        return send_file(
            pdf_data,
            download_name=filename,
            as_attachment=True,
            mimetype='application/pdf'
        )
        
    except Exception as e:
        logger.exception(f"Error in download handler: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Optional: Add cleanup for in-memory store
# This is a simple approach; for production, consider using a scheduled task
@app.before_request
def cleanup_expired_pdfs():
    """Remove PDFs from memory that are older than 1 hour"""
    import time
    current_time = time.time()
    
    # Add expiration timestamp if not present
    for pdf_id in list(pdf_memory_store.keys()):
        if 'expiration' not in pdf_memory_store[pdf_id]:
            # Set expiration to 1 hour from now
            pdf_memory_store[pdf_id]['expiration'] = current_time + 3600
    
    # Remove expired entries
    expired_ids = [
        pdf_id for pdf_id in pdf_memory_store 
        if pdf_memory_store[pdf_id]['expiration'] < current_time
    ]
    
    for pdf_id in expired_ids:
        del pdf_memory_store[pdf_id]
        logger.info(f"Removed expired PDF with ID: {pdf_id}")

# Create a simple error template
@app.route('/error')
def error_page():
    message = request.args.get('message', 'An error occurred')
    return render_template('error.html', message=message)

@app.after_request
def add_security_headers(response):
    # Extract nonce if it exists in the response
    nonce = None
    if hasattr(response, 'nonce'):
        nonce = response.nonce
    else:
        # Generate a new nonce if one doesn't exist
        nonce = secrets.token_hex(16)
    
    # Add CSP with nonce
    csp = (
        f"default-src 'self'; "
        f"script-src 'self' 'nonce-{nonce}'; "
        f"style-src 'self' https://cdnjs.cloudflare.com 'unsafe-inline'; "
        f"font-src 'self' https://cdnjs.cloudflare.com; "
        f"img-src 'self' data:; "
        f"object-src 'none'"
    )
    response.headers['Content-Security-Policy'] = csp
    
    # Other security headers...
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    
    return response

if __name__ == '__main__':
    app.run(debug=True)