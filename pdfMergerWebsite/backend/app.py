"""
Flask application for the PDF Merger service.

This module provides API endpoints for uploading and merging PDF files.
"""
import os
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
from utils.pdf_merger import merge_pdfs

# Initialize Flask application
app = Flask(__name__)

# Configuration constants
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'pdf'}

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Configure Flask app
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Limit upload size to 16MB


def allowed_file(filename):
    """
    Check if the file has an allowed extension.

    Args:
        filename (str): The name of the uploaded file to check

    Returns:
        bool: True if the file extension is allowed, False otherwise
    """
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/upload', methods=['POST'])
def upload_files():
    """
    Handle PDF file uploads and merge them into a single document.

    Returns:
        tuple: JSON response and HTTP status code
    """
    if 'files[]' not in request.files:
        return jsonify({'error': 'No files part'}), 400

    files = request.files.getlist('files[]')

    if not files or not files[0].filename:
        return jsonify({'error': 'No selected files'}), 400

    pdf_paths = []

    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            pdf_paths.append(file_path)
        else:
            return jsonify({
                'error': f'File {file.filename} is not a valid PDF'
            }), 400

    output_path = os.path.join(app.config['UPLOAD_FOLDER'], 'merged_document.pdf')
    merge_result = merge_pdfs(pdf_paths, output_path)

    if merge_result.get('success', False):
        return jsonify({
            'message': 'Files merged successfully',
            'download_link': output_path
        }), 200

    return jsonify({
        'error': merge_result.get('error', 'Error merging files')
    }), 500


# Clean up function to remove temporary files
def cleanup_files(file_paths):
    """
    Clean up temporary files after processing.

    Args:
        file_paths (list): List of file paths to remove
    """
    for file_path in file_paths:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except OSError as error:
            app.logger.error("Error removing file %s: %s", file_path, error)


if __name__ == '__main__':
    app.run(debug=True)
