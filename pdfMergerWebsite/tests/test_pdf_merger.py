# tests/test_pdf_merger.py
import unittest
import os
import tempfile
import shutil
from backend.utils.pdf_merger import merge_pdfs

class TestPDFMerger(unittest.TestCase):
    
    def setUp(self):
        # Create temporary test directory
        self.test_dir = tempfile.mkdtemp()
        
        # Create test PDF files (minimal valid PDF files)
        self.test_file1 = os.path.join(self.test_dir, 'test1.pdf')
        self.test_file2 = os.path.join(self.test_dir, 'test2.pdf')
        
        with open(self.test_file1, 'wb') as f:
            f.write(b'%PDF-1.7\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF')
        
        with open(self.test_file2, 'wb') as f:
            f.write(b'%PDF-1.7\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF')
    
    def tearDown(self):
        # Clean up test files
        shutil.rmtree(self.test_dir)
    
    def test_merge_pdfs_success(self):
        output_path = os.path.join(self.test_dir, 'merged.pdf')
        result = merge_pdfs([self.test_file1, self.test_file2], output_path)
        
        self.assertTrue(result['success'])
        self.assertIsNotNone(result['path'])
        self.assertIsNone(result['error'])
        self.assertTrue(os.path.exists(result['path']))
    
    def test_merge_pdfs_with_custom_filename(self):
        output_path = os.path.join(self.test_dir, 'merged.pdf')
        custom_filename = 'custom_name'
        
        result = merge_pdfs([self.test_file1, self.test_file2], output_path, custom_filename)
        
        self.assertTrue(result['success'])
        self.assertTrue(os.path.basename(result['path']) == 'custom_name.pdf')
    
    def test_merge_pdfs_nonexistent_files(self):
        output_path = os.path.join(self.test_dir, 'merged.pdf')
        result = merge_pdfs(['nonexistent1.pdf', 'nonexistent2.pdf'], output_path)
        
        self.assertFalse(result['success'])
        self.assertIsNotNone(result['error'])
    
    def test_merge_pdfs_invalid_files(self):
        # Create an invalid file
        invalid_file = os.path.join(self.test_dir, 'invalid.pdf')
        with open(invalid_file, 'w') as f:
            f.write('This is not a PDF file')
        
        output_path = os.path.join(self.test_dir, 'merged.pdf')
        result = merge_pdfs([invalid_file, self.test_file1], output_path)
        
        self.assertFalse(result['success'])
        self.assertIsNotNone(result['error'])