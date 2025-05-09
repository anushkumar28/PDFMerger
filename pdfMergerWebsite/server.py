import os
import io
import uuid
import secrets
import logging
import time
import sys
import base64
import threading
import json
from flask import Flask, request, jsonify, send_file, send_from_directory, render_template, g, redirect
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.utils import secure_filename
from pypdf import PdfReader, PdfWriter
import jinja2  # For jinja2.exceptions.TemplateError

# Update your logging format to include more detailed timestamp and process info
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(process)d] - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('pdf_merger')

# Flask app configuration
app = Flask(__name__,
            static_folder='frontend',
            template_folder='templates')
CORS(app)

# Add this to your app configuration section
app.config['PROPAGATE_EXCEPTIONS'] = True

# Enhanced logging configuration
logging.basicConfig(
    level=logging.DEBUG if app.debug else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)  # Log to stdout for Docker logs
    ]
)
logger = logging.getLogger('pdf_merger')

# Add this with your other configuration settings, after initializing the Flask app
# Configuration constants
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['OUTPUT_FOLDER'] = 'static/output'
app.config['ALLOWED_EXTENSIONS'] = {'pdf'}
app.config['MAX_CONTENT_LENGTH'] = int(os.environ.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))  # Default 16MB

# Define PDF expiry duration (in seconds)
PDF_EXPIRY_SECONDS = int(os.environ.get('PDF_EXPIRY_SECONDS', 3600))  # Default to 1 hour if not specified
logger.info(f"PDF expiry set to {PDF_EXPIRY_SECONDS} seconds")

# Memory store for PDF documents
pdf_memory_store = {}

# PDF statistics tracker
pdf_stats = {
    'total_created': 0,
    'total_expired': 0,
    'last_cleanup': time.time()
}

# Log important app info at startup
def log_app_info():
    """Log important application information at startup."""
    logger.info("Application started with configuration:")
    logger.info("Debug mode: %s", app.debug)
    logger.info("Template folder: %s", app.template_folder)
    logger.info("Static folder: %s", app.static_folder)
    logger.info("PDF expiry: %d seconds", PDF_EXPIRY_SECONDS)
    logger.info("Available routes: %s", [str(rule) for rule in app.url_map.iter_rules()])

# Register function to run once at startup
with app.app_context():
    log_app_info()

# Log template directory information
logger.info("Template folder configured as: %s", app.template_folder)
template_dir_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), app.template_folder)
logger.info("Full template directory path: %s", template_dir_path)
logger.info("Templates directory exists: %s", os.path.exists(template_dir_path))

if os.path.exists(template_dir_path):
    template_files = os.listdir(template_dir_path)
    logger.info("Template files found: %s", template_files)
else:
    logger.warning("Templates directory not found! Creating it...")
    os.makedirs(template_dir_path, exist_ok=True)

# Directory configuration
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
OUTPUT_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'output')

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max upload

# Ensure directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Ensure template directory exists
template_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
os.makedirs(template_dir, exist_ok=True)

# Configure rate limiting
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"  # For production, consider Redis
)

# In-memory PDF storage
pdf_memory_store = {}

# Add these variables near the top of your file, after initializing pdf_memory_store
pdf_stats = {
    'total_created': 0,
    'total_expired': 0,
    'last_cleanup': time.time()
}

# Configuration - Add persistence settings
PERSISTENCE_ENABLED = os.environ.get('PERSISTENCE_ENABLED', 'false').lower() == 'true'
PDF_EXPIRY_SECONDS = int(os.environ.get('PDF_EXPIRY_SECONDS', 3600))
PERSISTENCE_FILE = os.path.join('/app/data', 'pdf_store.json')
PERSISTENCE_INTERVAL = 60  # Save every minute in development

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
        logger.debug("Attempting to serve index.html")
        # Print the available static files to debug
        for root, _, files in os.walk('frontend'):
            logger.debug("Directory: %s", root)
            logger.debug("Files: %s", files)
        return app.send_static_file('index.html')
    except (FileNotFoundError, IOError, OSError) as e:
        logger.exception("Error serving index.html: %s", str(e))
        # Return a simple HTML response as fallback
        return """
        <!DOCTYPE html>
        <html>
        <head><title>PDF Merger</title></head>
        <body>
            <h1>PDF Merger Application</h1>
            <p style="color: red;">Error loading the application: """ + str(e) + """</p>
        </body>
        </html>
        """, 500

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

        if not files or len(files) < 2:
            logger.info("Need at least 2 files to merge")
            return jsonify({'error': 'Need at least 2 PDF files to merge'}), 400

        # Process PDFs entirely in memory
        pdf_readers = []

        for file in files:
            if not file or not file.filename:
                continue

            if file.filename.lower().endswith('.pdf'):
                # Log file details for debugging
                logger.debug("Processing file: %s, content type: %s, size: %d bytes",
                            file.filename, file.content_type, file.content_length or 0)

                # Read file directly into memory
                try:
                    pdf_content = io.BytesIO(file.read())
                    # Validate PDF content
                    try:
                        pdf_reader = PdfReader(pdf_content)
                        # Check if PDF is encrypted
                        if pdf_reader.is_encrypted:
                            logger.error("Encrypted PDF detected: %s", file.filename)
                            return jsonify({
                                'error': f'PDF file {file.filename} is encrypted. Please remove password protection before uploading.'
                            }), 400
                        logger.debug("Successfully read PDF with %d pages", len(pdf_reader.pages))
                        pdf_readers.append(pdf_reader)
                    except ModuleNotFoundError as crypto_error:
                        if "PyCryptodome" in str(crypto_error):
                            logger.error("Missing PyCryptodome dependency for encrypted PDF: %s", str(crypto_error))
                            return jsonify({
                                'error': 'This PDF requires cryptography support. Please contact the administrator.'
                            }), 500
                        raise
                except (ValueError, TypeError, IOError, OSError, PermissionError, RuntimeError, SyntaxError) as e:
                    logger.error("Invalid PDF file %s: %s", file.filename, str(e), exc_info=True)
                    return jsonify({'error': f'Invalid PDF file {file.filename}: {str(e)}'}), 400
            else:
                logger.error("Invalid file: %s, extension is not .pdf", file.filename)
                return jsonify({'error': f'Invalid file format: {file.filename}. Only PDF files are allowed.'}), 400

        if len(pdf_readers) < 2:
            logger.error("Not enough valid PDFs found after processing")
            return jsonify({'error': 'Need at least 2 valid PDF files to merge'}), 400

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
        output_buffer.seek(0)  # Important: Reset position to beginning
        # Store in memory instead of filesystem
        current_time = time.time()
        pdf_memory_store[unique_id] = {
            'data': output_buffer,
            'filename': output_filename,
            'expiration': current_time + PDF_EXPIRY_SECONDS
        }
        pdf_stats['total_created'] += 1
        logger.info("Merge successful. Created in-memory PDF with ID: %s (expires in 1 hour)", unique_id)
        # Save to persistence if enabled
        if PERSISTENCE_ENABLED:
            threading.Thread(target=save_pdf_store).start()
        # Create download link with the unique ID as identifier
        download_link = f"/download/{unique_id}"
        return jsonify({
            'message': 'Files merged successfully',
            'download_link': download_link
        })
    except (ValueError, TypeError, IOError, OSError, PermissionError) as e:
        logger.exception("Error in upload handler: %s", str(e))
        return jsonify({'error': str(e)}), 500

@app.route('/recover/<pdf_id>')
def recover_pdf(pdf_id):
    """Try to recover a PDF that's not found in memory but might exist in persistence."""
    try:
        logger.info(f"Recovery attempt for PDF ID: {pdf_id}")

        # First check if it's already in memory (might have been added since the download request)
        if pdf_id in pdf_memory_store:
            logger.info(f"PDF {pdf_id} is now available in memory store")
            return redirect(f"/download/{pdf_id}")

        # Log persistence status
        logger.info(f"Persistence enabled: {PERSISTENCE_ENABLED}")
        logger.info(f"Persistence file exists: {os.path.exists(PERSISTENCE_FILE)}")

        # If persistence is enabled, try to load from disk
        if PERSISTENCE_ENABLED:
            if os.path.exists(PERSISTENCE_FILE):
                try:
                    # Load fresh from disk each time
                    with open(PERSISTENCE_FILE, 'r', encoding='utf-8') as file_handle:
                        serializable_store = json.load(file_handle)

                    logger.info(f"Loaded persistence file with {len(serializable_store)} entries")

                    # Check if PDF exists in the persistence file
                    if pdf_id in serializable_store:
                        pdf_data = serializable_store[pdf_id]
                        logger.info(f"Found PDF {pdf_id} in persistence file")

                        # Check if it's expired
                        current_time = time.time()
                        if pdf_data['expiration'] < current_time:
                            time_expired = current_time - pdf_data['expiration']
                            logger.info(f"PDF {pdf_id} expired {time_expired:.1f} seconds ago")
                            return redirect(f"/download-expired/{pdf_id}")

                        # Recover the PDF data
                        logger.info(f"Decoding PDF data from base64")
                        pdf_bytes = base64.b64decode(pdf_data['data_base64'])
                        pdf_buffer = io.BytesIO(pdf_bytes)
                        pdf_buffer.seek(0)

                        # Add back to memory store
                        pdf_memory_store[pdf_id] = {
                            'data': pdf_buffer,
                            'filename': pdf_data['filename'],
                            'expiration': pdf_data['expiration'],
                            'recovered': True
                        }

                        logger.info(f"Successfully recovered PDF {pdf_id} from persistence")
                        return redirect(f"/download/{pdf_id}")
                    else:
                        logger.error(f"PDF {pdf_id} not found in persistence file")
                except json.JSONDecodeError as json_err:
                    logger.error(f"Error parsing persistence file: {str(json_err)}")
                except Exception as e:
                    logger.exception(f"Error recovering from persistence: {str(e)}")
            else:
                logger.error(f"Persistence file not found: {PERSISTENCE_FILE}")
        else:
            logger.warning("Persistence is disabled, cannot recover PDF from disk")

        # If we got here, the PDF couldn't be recovered
        logger.error(f"PDF {pdf_id} not found in memory or persistence")
        return redirect(f"/download-not-found/{pdf_id}")

    except Exception as e:
        logger.exception(f"Error in recovery attempt: {str(e)}")
        return redirect(f"/error?message=Recovery failed: {str(e)}")

@app.route('/download-expired/<pdf_id>')
def download_expired(pdf_id):
    """Show a user-friendly page for expired PDFs."""
    return render_template('expired.html', pdf_id=pdf_id)

@app.route('/download-not-found/<pdf_id>')
def download_not_found(pdf_id):
    """Show a user-friendly page for PDFs that are not found."""
    return render_template('not_found.html', pdf_id=pdf_id)

# Modify your download_file function to include more detailed logging
@app.route('/download/<unique_id>', methods=['GET'])
def download_file(unique_id):
    """Serve the merged PDF file for download."""
    try:
        # Strip any file extension that might have been appended
        original_id = unique_id
        unique_id = unique_id.split('.')[0]

        if original_id != unique_id:
            logger.info(f"Stripped file extension from ID: {original_id} -> {unique_id}")

        # Log more details about the request
        logger.info(f"Download request for PDF ID: {unique_id}")
        logger.info(f"Request headers: {dict(request.headers)}")
        logger.info(f"Memory store has {len(pdf_memory_store)} PDFs")

        # Run the PDF store status logger
        log_pdf_store_status()

        # Check if the ID exists in our in-memory store
        if unique_id not in pdf_memory_store:
            logger.error(f"PDF with ID {unique_id} not found in memory store")

            # Log the most similar IDs to help diagnose potential typos
            if pdf_memory_store:
                closest_matches = sorted(pdf_memory_store.keys(),
                                         key=lambda x: sum(a==b for a,b in zip(x, unique_id)))[:3]
                logger.info(f"Closest matching IDs: {', '.join(closest_matches)}")

            # Automatically try recovery
            logger.info(f"Attempting recovery for PDF ID: {unique_id}")
            return redirect(f"/recover/{unique_id}")

        # Get the PDF data from memory
        pdf_data = pdf_memory_store[unique_id]['data']
        filename = pdf_memory_store[unique_id]['filename']

        # Check the PDF data integrity
        if not hasattr(pdf_data, 'getvalue'):
            logger.error(f"PDF data for ID {unique_id} is not a BytesIO object: {type(pdf_data)}")
            return jsonify({'error': 'Invalid PDF data format in memory'}), 500

        # Log the size of the PDF
        pdf_size = len(pdf_data.getvalue())
        logger.info(f"Serving PDF: {filename}, size: {pdf_size} bytes")

        if pdf_size == 0:
            logger.error(f"PDF with ID {unique_id} has zero bytes")
            return jsonify({'error': 'PDF file is empty'}), 500

        # Reset buffer position to beginning
        pdf_data.seek(0)

        # Return file with proper headers
        response = send_file(
            pdf_data,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename,
            etag=unique_id
        )

        logger.info(f"Successfully sent PDF: {filename}")
        return response

    except Exception as e:
        logger.exception(f"Error in download handler: {str(e)}")
        # Rest of your error handling code...

@app.before_request
def cleanup_expired_pdfs():
    """Remove PDFs from memory that are older than 1 hour."""
    current_time = time.time()

    # Don't run cleanup on every request - only every 60 seconds
    if current_time - pdf_stats['last_cleanup'] < 60:
        return

    pdf_stats['last_cleanup'] = current_time

    # Get list of expired IDs to avoid dictionary size change during iteration
    expired_ids = [
        pdf_id for pdf_id in list(pdf_memory_store.keys())
        if pdf_memory_store[pdf_id].get('expiration', 0) < current_time
    ]

    # Remove expired entries
    for pdf_id in expired_ids:
        logger.info("Removing expired PDF with ID: %s", pdf_id)
        del pdf_memory_store[pdf_id]
        pdf_stats['total_expired'] += 1

    # Log summary if any PDFs were expired
    if expired_ids:
        logger.info("Cleanup summary: Removed %d PDFs, %d active PDFs remain",
                   len(expired_ids), len(pdf_memory_store))

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

    # Store nonce in g object for templates to access
    g.csp_nonce = nonce

    # Add CSP with nonce and allow unsafe-inline for styles and event handlers
    csp = (
        f"default-src 'self'; "
        f"script-src 'self' 'nonce-{nonce}' 'unsafe-inline' 'unsafe-eval'; "
        f"style-src 'self' https://cdnjs.cloudflare.com 'unsafe-inline' 'nonce-{nonce}'; "
        f"font-src 'self' https://cdnjs.cloudflare.com; "
        f"img-src 'self' data:; "
        f"connect-src 'self'; "
        f"object-src 'none'"
    )
    response.headers['Content-Security-Policy'] = csp

    # Add nonce to the response for client-side access
    response.headers['X-CSP-Nonce'] = nonce

    # Other security headers
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'

    return response

@app.context_processor
def inject_csp_nonce():
    """Make CSP nonce available in templates."""
    return dict(csp_nonce=getattr(g, 'csp_nonce', ''))

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

def save_pdf_store():
    """Save the PDF store to disk for persistence."""
    if not PERSISTENCE_ENABLED:
        return

    try:
        # Create a copy of the store with serializable data
        serializable_store = {}
        for pdf_id, pdf_data in pdf_memory_store.items():
            # Convert BytesIO to base64 string for serialization
            pdf_bytes = pdf_data['data'].getvalue()
            serializable_store[pdf_id] = {
                'data_base64': base64.b64encode(pdf_bytes).decode('utf-8'),
                'filename': pdf_data['filename'],
                'expiration': pdf_data['expiration']
            }

        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(PERSISTENCE_FILE), exist_ok=True)

        with open(PERSISTENCE_FILE, 'w', encoding='utf-8') as file_handle:
            json.dump(serializable_store, file_handle, indent=2)  # Added indentation for better readability

        logger.info("Successfully saved PDF store to disk (%d items)", len(pdf_memory_store))
    except (IOError, OSError, ValueError, TypeError, KeyError, base64.binascii.Error, AttributeError) as e:
        logger.error("Failed to save PDF store: %s", str(e))
    # Schedule the next save
    if PERSISTENCE_ENABLED:
        threading.Timer(PERSISTENCE_INTERVAL, save_pdf_store).start()

def load_pdf_store():
    """Load the PDF store from disk."""
    # Create a new dictionary instead of modifying the global variable
    loaded_store = {}

    if not PERSISTENCE_ENABLED or not os.path.exists(PERSISTENCE_FILE):
        return loaded_store

    try:
        with open(PERSISTENCE_FILE, 'r', encoding='utf-8') as file_handle:
            serializable_store = json.load(file_handle)

        # Convert the serialized data back to BytesIO objects
        loaded_store = {}
        current_time = time.time()

        for pdf_id, pdf_data in serializable_store.items():
            # Skip expired entries
            if pdf_data['expiration'] < current_time:
                continue

            # Convert base64 back to BytesIO
            pdf_bytes = base64.b64decode(pdf_data['data_base64'])
            pdf_buffer = io.BytesIO(pdf_bytes)
            pdf_buffer.seek(0)  # Important: Reset position to beginning

            loaded_store[pdf_id] = {
                'data': pdf_buffer,
                'filename': pdf_data['filename'],
                'expiration': pdf_data['expiration']
            }

        logger.info("Successfully loaded PDF store from disk (%d valid items)", len(loaded_store))
        return loaded_store
    except (IOError, OSError, ValueError, TypeError, KeyError, json.JSONDecodeError, base64.binascii.Error) as e:
        logger.error("Failed to load PDF store: %s", str(e))
        return {}
# Initialize persistence at startup
if PERSISTENCE_ENABLED:
    pdf_memory_store.update(load_pdf_store())
    # Start the save timer
    threading.Timer(PERSISTENCE_INTERVAL, save_pdf_store).start()

@app.route('/api/debug/pdfs')
def debug_pdfs():
    if request.remote_addr != '127.0.0.1':
        return jsonify({'error': 'Access denied'}), 403

    return jsonify({
        'active_pdfs': len(pdf_memory_store),
        'pdf_ids': list(pdf_memory_store.keys())
    })

@app.route('/api/debug/csp')
def debug_csp():
    """Debug endpoint to check CSP configuration."""
    nonce = getattr(g, 'csp_nonce', secrets.token_hex(16))
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>CSP Debug</title>
        <style nonce="{nonce}">
            body {{ font-family: monospace; padding: 20px; }}
            .success {{ color: green; }}
            .fail {{ color: red; }}
        </style>
        <script nonce="{nonce}">
            console.log('CSP nonce working for scripts');
            window.onload = function() {{
                document.getElementById('status').textContent = 'Script execution successful!';
                document.getElementById('status').className = 'success';
            }};
        </script>
    </head>
    <body>
        <h1>Content Security Policy Debug</h1>
        <p>Current nonce: <strong>{nonce}</strong></p>
        <p>Script status: <span id="status" class="fail">Script execution failed</span></p>
        <p>Style status: <span class="success">Style application successful!</span></p>
    </body>
    </html>
    """

@app.route('/debug/memory-store')
def debug_memory_store():
    """Debug endpoint to view the PDF memory store."""
    # Only allow in development mode
    if not app.debug:
        return jsonify({"error": "Debug mode not enabled"}), 403

    # Format data about stored PDFs (without the actual content)
    store_info = {}
    current_time = time.time()

    for pdf_id, data in pdf_memory_store.items():
        expires_in = data['expiration'] - current_time
        store_info[pdf_id] = {
            'filename': data['filename'],
            'size_bytes': len(data['data'].getvalue()) if hasattr(data['data'], 'getvalue') else 'unknown',
            'expires_in_seconds': int(expires_in),
            'expires_at': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(data['expiration'])),
            'created_at': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(data.get('created_at', data['expiration'] - PDF_EXPIRY_SECONDS)))
        }

    return jsonify({
        'active_pdfs': len(pdf_memory_store),
        'pdf_store': store_info,
        'pdf_stats': pdf_stats
    })

# Add this function to your server.py file for improved PDF tracking
def log_pdf_store_status():
    """Log detailed information about the PDF memory store."""
    try:
        current_time = time.time()
        active_count = len(pdf_memory_store)
        expired_count = 0

        # Check for soon-to-expire PDFs
        for pdf_id, data in pdf_memory_store.items():
            expiry_time = data.get('expiration', 0)
            time_left = expiry_time - current_time

            if time_left < 0:
                expired_count += 1
                logger.warning(f"Found expired PDF still in memory: {pdf_id}, expired {abs(time_left):.1f} seconds ago")
            elif time_left < 300:  # Less than 5 minutes left
                logger.info(f"PDF {pdf_id} will expire soon: {time_left:.1f} seconds left")

        logger.info(f"PDF store status: {active_count} active, {expired_count} expired but not cleaned up")
        logger.info(f"PDF statistics: {pdf_stats['total_created']} created, {pdf_stats['total_expired']} expired")

        # Log the IDs of the first 10 PDFs (to avoid excessive logging)
        sample_ids = list(pdf_memory_store.keys())[:10]
        logger.info(f"Sample of active PDF IDs: {', '.join(sample_ids) if sample_ids else 'none'}")

    except Exception as e:
        logger.error(f"Error logging PDF store status: {str(e)}")

@app.route('/health')
def health_check():
    """Health check endpoint for Docker healthcheck."""
    try:
        # Run a quick database check
        store_size = len(pdf_memory_store)

        # Check if persistence is working
        persistence_ok = True
        if PERSISTENCE_ENABLED:
            persistence_ok = os.path.exists(os.path.dirname(PERSISTENCE_FILE))

        return jsonify({
            'status': 'healthy',
            'timestamp': time.time(),
            'pdf_store': {
                'size': store_size,
                'stats': pdf_stats
            },
            'persistence': {
                'enabled': PERSISTENCE_ENABLED,
                'working': persistence_ok
            }
        })
    except Exception as e:
        logger.exception(f"Health check failed: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500

if __name__ == '__main__':
    # Use environment variables for host and port
    port = int(os.environ.get("PORT", 5000))
    host = os.environ.get("HOST", "0.0.0.0")

    app.run(host=host, port=port, debug=os.environ.get('FLASK_ENV') == 'development')
