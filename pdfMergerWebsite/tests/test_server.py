"""
Test module for the PDF Merger server application.

This module contains unit tests that verify the functionality of the PDF Merger
web server, including file uploads, downloads, and PDF merging operations.
"""
import unittest
import os
import io
import tempfile
import shutil
import sys
import json
from server import app

# Add the parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class TestServerEndpoints(unittest.TestCase):
    """
    Test cases for the PDF Merger server API endpoints.

    This class tests the main functionality of the server including
    file uploads, PDF merging, and download operations.
    """
    def setUp(self):
        """Set up the test environment before each test method."""
        app.config['TESTING'] = True
        app.config['DEBUG'] = False
        self.app = app.test_client()
        # Create temporary test directory
        self.test_dir = tempfile.mkdtemp()
        # Create test PDF file
        self.test_file = os.path.join(self.test_dir, 'test.pdf')
        with open(self.test_file, 'wb') as f:
            f.write(b'%PDF-1.7\n1 0 obj\n<< /Type /Catalog >>\nendobj\n'
                    b'trailer\n<< /Root 1 0 R >>\n%%EOF')

    def tearDown(self):
        """Clean up resources after each test method."""
        # Clean up test directory
        shutil.rmtree(self.test_dir)

    def test_index_route(self):
        """Test that the index route returns the main page."""
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)

    def test_upload_no_files(self):
        """Test that upload endpoint handles missing files correctly."""
        response = self.app.post('/upload', data={})
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)

        # Split long line to satisfy line-too-long rule
        response = self.app.post(
            '/upload',
            content_type='multipart/form-data',
            data={'output_filename': 'test_output'}
        )
        self.assertEqual(response.status_code, 400)

    def test_upload_single_file(self):
        """Test that upload endpoint requires at least two files."""
        # Create a test file to upload
        with open(self.test_file, 'rb') as pdf:
            data = {
                'files': (io.BytesIO(pdf.read()), 'test.pdf'),
                'output_filename': 'test_output'
            }
            # Split long line to satisfy line-too-long rule
            response = self.app.post(
                '/upload',
                content_type='multipart/form-data',
                data=data
            )
            self.assertEqual(response.status_code, 400)
            response_data = json.loads(response.data)
            self.assertIn('error', response_data)

    def test_download_nonexistent(self):
        """Test downloading a non-existent file returns a 404 error."""
        response = self.app.get('/download/nonexistent_file')
        self.assertEqual(response.status_code, 404)
