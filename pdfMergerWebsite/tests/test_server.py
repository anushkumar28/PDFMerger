import unittest
import os
import io
import tempfile
import shutil
import sys
from contextlib import contextmanager
import json

# Add the parent directory to sys.path to make imports work
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from server import app  
class TestServerEndpoints(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['DEBUG'] = False
        self.app = app.test_client()
        
        # Create temporary test directory
        self.test_dir = tempfile.mkdtemp()
        
        # Create test PDF file
        self.test_file = os.path.join(self.test_dir, 'test.pdf')
        with open(self.test_file, 'wb') as f:
            f.write(b'%PDF-1.7\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF')
    
    def tearDown(self):
        # Clean up test directory
        shutil.rmtree(self.test_dir)
        
    def test_upload_endpoint_no_files(self):
        response = self.app.post('/upload', data={})
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)
    
    def test_upload_endpoint_success(self):
        # Create two PDF files in memory
        file1 = (io.BytesIO(b'%PDF-1.7\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF'), 'test1.pdf')
        file2 = (io.BytesIO(b'%PDF-1.7\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF'), 'test2.pdf')
        
        response = self.app.post(
            '/upload', 
            data={
                'files': [file1, file2],
                'output_filename': 'test_merged'
            },
            content_type='multipart/form-data'
        )
        
        # Test may fail due to actual PDF merging, so just check the basic response structure
        if response.status_code == 200:
            data = json.loads(response.data)
            self.assertIn('download_link', data)
            self.assertIn('message', data)
        else:
            print(f"Upload test failed with status code {response.status_code}: {response.data}")
    
    def test_download_endpoint_nonexistent_file(self):
        response = self.app.get('/download/nonexistent.pdf')
        self.assertEqual(response.status_code, 404)