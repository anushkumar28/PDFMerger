from flask import Flask, request, jsonify, send_from_directory, after_this_request
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

# Track files to clean up
uploaded_file_tracker = {}

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

        # Get custom filename if provided or generate a default one
        output_filename = None
        if 'output_filename' in request.form and request.form['output_filename'].strip():
            output_filename = request.form['output_filename'].strip()
            print(f"Custom filename provided: {output_filename}")
        else:
            # Generate a unique output filename
            import uuid
            output_filename = f"merged_document_{uuid.uuid4().hex[:8]}"
        
        # Make sure it has .pdf extension
        if not output_filename.lower().endswith('.pdf'):
            output_filename += '.pdf'
            
        output_path = os.path.join(app.config['UPLOAD_FOLDER'], 'merged_document.pdf') # Use a default base name
        
        print(f"Attempting to merge PDFs to: {output_path} with custom name: {output_filename}")

        # Change this line to pass the output_filename parameter
        merge_result = merge_pdfs(pdf_paths, output_path, output_filename)
        print(f"Merge result: {merge_result}")
        
        if merge_result['success']:
            merged_filename = os.path.basename(merge_result["path"])
            download_link = f'/download/{merged_filename}'
            
            # Store files to clean up later
            uploaded_file_tracker[merged_filename] = {
                'input_paths': pdf_paths,
                'merged_path': merge_result["path"]
            }
            
            print(f"Success! Download link: {download_link}")
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
                        print(f"Removed uploaded file: {path}")
                except Exception as e:
                    print(f"Error removing file {path}: {str(e)}")
                    
            print(f"Error merging files: {merge_result['error']}")
            return jsonify({'error': merge_result['error'] or 'Error merging files'}), 500
    except Exception as e:
        # Clean up any uploaded files on exception
        for path in pdf_paths if 'pdf_paths' in locals() else []:
            try:
                if os.path.exists(path):
                    os.remove(path)
                    print(f"Removed uploaded file: {path}")
            except Exception as remove_err:
                print(f"Error removing file {path}: {str(remove_err)}")
                
        print(f"Exception in upload_files: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': f'Server error: {str(e)}'}), 500

# Also fix the download route to handle potential errors
@app.route('/download/<filename>')
def download_file(filename):
    try:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            return jsonify({'error': 'File not found'}), 404
        
        # Get files to clean up after the response
        files_to_clean = uploaded_file_tracker.get(filename, {})
        
        @after_this_request
        def clean_up_files(response):
            if filename in uploaded_file_tracker:
                # Clean up input files
                for path in files_to_clean.get('input_paths', []):
                    try:
                        if os.path.exists(path):
                            os.remove(path)
                            print(f"Removed uploaded file: {path}")
                    except Exception as e:
                        print(f"Error removing file {path}: {str(e)}")
                
                # Clean up merged file
                merged_path = files_to_clean.get('merged_path')
                if merged_path and os.path.exists(merged_path):
                    try:
                        os.remove(merged_path)
                        print(f"Removed merged file: {merged_path}")
                    except Exception as e:
                        print(f"Error removing merged file {merged_path}: {str(e)}")
                
                # Remove from tracker
                uploaded_file_tracker.pop(filename, None)
                print(f"Cleaned up files for {filename}")
            
            return response
        
        print(f"Serving file: {file_path}")
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)
    except Exception as e:
        print(f"Exception in download_file: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Error downloading file: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True)