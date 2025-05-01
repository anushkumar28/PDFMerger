from flask import Flask, request, jsonify
import os
from werkzeug.utils import secure_filename
from utils.pdf_merger import merge_pdfs

app = Flask(__name__)

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'pdf'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/upload', methods=['POST'])
def upload_files():
    if 'files[]' not in request.files:
        return jsonify({'error': 'No files part'}), 400

    files = request.files.getlist('files[]')
    pdf_paths = []

    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            pdf_paths.append(file_path)
        else:
            return jsonify({'error': f'File {file.filename} is not a valid PDF'}), 400

    output_path = os.path.join(app.config['UPLOAD_FOLDER'], 'merged_document.pdf')
    if merge_pdfs(pdf_paths, output_path):
        return jsonify({'message': 'Files merged successfully', 'download_link': output_path}), 200
    else:
        return jsonify({'error': 'Error merging files'}), 500

if __name__ == '__main__':
    app.run(debug=True)