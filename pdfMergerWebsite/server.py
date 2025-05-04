import os
import io
import uuid
import secrets
import logging
import time
from flask import Flask, request, jsonify, send_file, send_from_directory, render_template
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.utils import secure_filename
from pypdf import PdfReader, PdfWriter
import jinja2  # For jinja2.exceptions.TemplateError

# Configure logging once
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='pdf_merger.log'
)
logger = logging.getLogger('pdf_merger')

# Flask app configuration
app = Flask(__name__,
            static_folder='frontend',
            template_folder='templates')
CORS(app)

# Directory configuration
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
OUTPUT_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'output')

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max upload

# Ensure directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Configure rate limiting
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"  # For production, consider Redis
)

# In-memory PDF storage
pdf_memory_store = {}

# Verify upload directory permissions
try:
    test_file = os.path.join(app.config['UPLOAD_FOLDER'], 'test_write.txt')
    with open(test_file, 'w', encoding='utf-8') as f:
        f.write('test')
    os.remove(test_file)
    logger.info("Upload directory is writable: %s", app.config['UPLOAD_FOLDER'])
except (OSError, IOError, PermissionError) as e:
    logger.error("ERROR: Cannot write to upload directory: %s", str(e), exc_info=True)
def validate_pdf_file(file):
    """
    Validate that the uploaded file is actually a PDF.
    
    Args:
        file: The uploaded file object
        
    Returns:
        bool: True if file is a valid PDF, False otherwise
    """
    # Check MIME type
    if not file.content_type == 'application/pdf':
        return False
    # Check file signature (magic bytes)
    file_content = file.read(5)
    file.seek(0)  # Reset file pointer
    # PDF files start with %PDF-
    return file_content.startswith(b'%PDF-')

def generate_secure_filename(filename):
    """
    Generate a secure filename with a random token.
    
    Args:
        filename (str): Original filename
        
    Returns:
        str: Secure filename with random token
    """
    secure_name = secure_filename(filename)
    random_token = secrets.token_hex(8)
    name, ext = os.path.splitext(secure_name)
    return f"{name}_{random_token}{ext}"

def is_safe_pdf(file_path):
    """
    Validate if a file is a real PDF and not malicious.
    
    Args:
        file_path (str): Path to the PDF file
        
    Returns:
        bool: True if file is a safe PDF, False otherwise
    """
    try:
        with open(file_path, 'rb') as file_obj:
            header = file_obj.read(5)
            # Check for PDF magic number
            return header == b'%PDF-'
    except (IOError, OSError, FileNotFoundError, PermissionError):
        return False

@app.route('/')
def index():
    """Serve the main page."""
    try:
        return app.send_static_file('index.html')
    except (FileNotFoundError, IOError, OSError) as e:
        logger.exception("Error serving index.html: %s", str(e))
        return "PDF Merger Application - Error loading frontend. Check server logs."
@app.route('/<path:path>')
def serve_static(path):
    """Serve static files."""
    return send_from_directory('frontend', path)

@app.route('/manifest.json')
def serve_manifest():
    """Serve the PWA manifest file."""
    return send_from_directory(app.static_folder, 'manifest.json')

@app.route('/upload', methods=['POST'])
@limiter.limit("10 per minute")
def upload_file():
    """Handle PDF file uploads and merging."""
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
                except (ValueError, TypeError, IOError, IndexError) as e:
                    logger.error("Invalid PDF file %s: %s", file.filename, str(e))
                    return jsonify({'error': f'Invalid PDF file {file.filename}: {str(e)}'}), 400
            else:
                logger.error("Invalid file: %s", file.filename)
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
        current_time = time.time()
        pdf_memory_store[unique_id] = {
            'data': output_buffer,
            'filename': output_filename,
            'expiration': current_time + 3600  # 1 hour expiration
        }
        logger.info("Merge successful. Created in-memory PDF with ID: %s", unique_id)
        # Create download link with the unique ID as identifier
        download_link = f"/download/{unique_id}"
        return jsonify({
            'message': 'Files merged successfully',
            'download_link': download_link
        })    
    except (ValueError, TypeError, IOError, OSError, PermissionError) as e:
        logger.exception("Error in upload handler: %s", str(e))
        return jsonify({'error': str(e)}), 500

@app.route('/download/<unique_id>')
def download_file(unique_id):
    """Serve the merged PDF file for download."""
    try:
        # Check if the ID exists in our in-memory store
        if unique_id not in pdf_memory_store:
            logger.error("PDF with ID %s not found in memory store", unique_id)
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
        
    except (IOError, OSError, ValueError, TypeError, KeyError, MemoryError) as e:
        logger.exception("Error in download handler: %s", str(e))
        return jsonify({'error': str(e)}), 500

@app.before_request
def cleanup_expired_pdfs():
    """Remove PDFs from memory that are older than 1 hour."""
    current_time = time.time()
    
    # Get list of expired IDs to avoid dictionary size change during iteration
    expired_ids = [
        pdf_id for pdf_id in list(pdf_memory_store.keys())
        if pdf_memory_store[pdf_id].get('expiration', 0) < current_time
    ]
    
    # Remove expired entries
    for pdf_id in expired_ids:
        del pdf_memory_store[pdf_id]
        logger.info("Removed expired PDF with ID: %s", pdf_id)

@app.route('/error')
def error_page():
    """Render the error page."""
    message = request.args.get('message', 'An error occurred')
    return render_template('error.html', message=message)

@app.after_request
def add_security_headers(response):
    """Add security headers to all responses."""
    # Generate a new nonce
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
    # Other security headers
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response

@app.errorhandler(404)
def page_not_found(_):
    """Handle 404 errors."""
    try:
        # Try to render the error template
        return render_template('error.html', message="Page not found"), 404
    except (IOError, OSError, FileNotFoundError, jinja2.exceptions.TemplateError) as template_error:
        # If template rendering fails, return a simple response
        logger.exception("Error rendering template: %s", str(template_error))
        return "404 - Page not found", 404


@app.errorhandler(500)
def server_error(e):
    """Handle 500 errors."""
    logger.error("Server error: %s", str(e))
    return render_template('error.html', message="Internal server error"), 500


@app.errorhandler(400)
def bad_request(e):
    """Handle 400 errors."""
    logger.warning("Bad request: %s", str(e))
    return render_template('error.html', message="Bad request"), 400


if __name__ == '__main__':
    # Use a production WSGI server in production environment
    if os.environ.get('FLASK_ENV') == 'production':
        # In production, don't use debug mode
        app.run(host='0.0.0.0', port=5000, debug=False)
    else:
        # For development
        app.run(debug=True)