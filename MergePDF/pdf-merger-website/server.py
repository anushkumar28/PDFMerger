from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import traceback
from backend.utils.pdf_merger import merge_pdfs

app = Flask(__name__, static_folder='frontend')
CORS(app)

UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# At the start of your server.py file
try:
    # Create upload directory if it doesn't exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Test write permissions
    test_file = os.path.join(app.config['UPLOAD_FOLDER'], 'test_write.txt')
    with open(test_file, 'w') as f:
        f.write('test')
    os.remove(test_file)
    print(f"Upload directory is writable: {app.config['UPLOAD_FOLDER']}")
except Exception as e:
    print(f"ERROR: Cannot write to upload directory: {str(e)}")
    # This will help identify permission issues at startup

@app.route('/')
def index():
    return send_from_directory('frontend', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('frontend', path)

@app.route('/upload', methods=['POST'])
def upload_files():
    try:
        print("Files in request:", list(request.files.keys()))
        
        if 'files' not in request.files:
            print("No 'files' part in request")
            return jsonify({'error': 'No files part'}), 400

        files = request.files.getlist('files')
        print(f"Number of files received: {len(files)}")
        
        if len(files) < 2:
            print("Need at least 2 files to merge")
            return jsonify({'error': 'Need at least 2 PDF files to merge'}), 400
        
        pdf_paths = []

        for file in files:
            if file and file.filename.endswith('.pdf'):
                filename = file.filename
                # Use a more secure filename
                filename = os.path.basename(filename)
                
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                
                print(f"Saving file to: {file_path}")
                try:
                    file.save(file_path)
                    # Verify the file was saved
                    if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                        pdf_paths.append(file_path)
                        print(f"Successfully saved file: {file_path}")
                    else:
                        print(f"Failed to save file or file is empty: {file_path}")
                        return jsonify({'error': f'Failed to save file: {filename}'}), 500
                except Exception as save_err:
                    print(f"Error saving file {filename}: {str(save_err)}")
                    return jsonify({'error': f'Error saving file {filename}: {str(save_err)}'}), 500
            else:
                print(f"Invalid file: {file.filename if file else 'None'}")
                return jsonify({'error': 'Only PDF files are allowed'}), 400

        if not pdf_paths or len(pdf_paths) < 2:
            print("No valid PDF files were uploaded")
            return jsonify({'error': 'No valid PDF files were uploaded'}), 400

        # Generate a unique output filename
        import uuid
        output_filename = f"merged_document_{uuid.uuid4().hex[:8]}.pdf"
        output_path = os.path.join(app.config['UPLOAD_FOLDER'], output_filename)
        
        print(f"Attempting to merge PDFs to: {output_path}")
        
        merge_result = merge_pdfs(pdf_paths, output_path)
        print(f"Merge result: {merge_result}")
        
        if merge_result:
            download_link = f'/download/{output_filename}'
            print(f"Success! Download link: {download_link}")
            return jsonify({
                'message': 'Files merged successfully', 
                'download_link': download_link
            }), 200
        else:
            print("Error merging files")
            return jsonify({'error': 'Error merging files'}), 500
    except Exception as e:
        print(f"Exception in upload_files: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/merge', methods=['POST'])
def merge_files():
    if 'files' not in request.files:
        return jsonify({'error': 'No files part'}), 400

    files = request.files.getlist('files')
    pdf_paths = []

    for file in files:
        if file and file.filename.endswith('.pdf'):
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(file_path)
            pdf_paths.append(file_path)
        else:
            return jsonify({'error': 'Only PDF files are allowed'}), 400

    output_path = os.path.join(app.config['UPLOAD_FOLDER'], 'merged_document.pdf')
    if merge_pdfs(pdf_paths, output_path):
        return jsonify({'message': 'Files merged successfully', 'download_link': f'/download/{os.path.basename(output_path)}'}), 200
    else:
        return jsonify({'error': 'Error merging files'}), 500

# Also fix the download route to handle potential errors
@app.route('/download/<filename>')
def download_file(filename):
    try:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            return jsonify({'error': 'File not found'}), 404
        
        print(f"Serving file: {file_path}")
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)
    except Exception as e:
        print(f"Exception in download_file: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Error downloading file: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True)