"""
Unit tests for the PDF merger functionality.

This module contains tests that verify the functionality of the merge_pdfs function,
including successful merges, custom filenames, and error handling.
"""
import unittest
import os
import tempfile
import shutil
from pypdf import PdfReader, PdfWriter

# Import the merge_pdfs function
from pdfMergerWebsite.backend.utils.pdf_merger import merge_pdfs


class TestPDFMerger(unittest.TestCase):
    """
    Test cases for PDF merger functionality.

    This class tests various scenarios for the PDF merger utility, including
    successful merges, handling of custom filenames, and error conditions.
    """

    def setUp(self):
        """Set up test environment with temporary files before each test."""
        # Create temporary test directory
        self.test_dir = tempfile.mkdtemp()

        # Define paths for test files
        self.test_file1 = os.path.join(self.test_dir, 'test1.pdf')
        self.test_file2 = os.path.join(self.test_dir, 'test2.pdf')

        # Create first valid PDF
        self._create_valid_pdf(self.test_file1)

        # Create second valid PDF
        self._create_valid_pdf(self.test_file2)

        # Verify the files were created successfully
        self.assertTrue(
            os.path.exists(self.test_file1),
            f"Test file 1 not created at {self.test_file1}"
        )
        self.assertTrue(
            os.path.exists(self.test_file2),
            f"Test file 2 not created at {self.test_file2}"
        )
        self.assertTrue(os.path.getsize(self.test_file1) > 0, "Test file 1 is empty")
        self.assertTrue(os.path.getsize(self.test_file2) > 0, "Test file 2 is empty")

    def _create_valid_pdf(self, file_path):
        """
        Create a valid PDF file for testing purposes.

        Args:
            file_path: Path where the test PDF should be created
        """
        # Create a PDF writer
        writer = PdfWriter()

        # Add a blank page
        writer.add_blank_page(width=200, height=200)

        # Write the PDF to the file
        with open(file_path, "wb") as outfile:
            writer.write(outfile)

    def tearDown(self):
        """Clean up test files after each test."""
        try:
            shutil.rmtree(self.test_dir)
        except (OSError, IOError, PermissionError) as exc:
            print(f"Error cleaning up test directory: {exc}")

    def test_merge_pdfs_success(self):
        """Test successful merging of two PDF files."""
        # Check if test files are valid before attempting to merge
        try:
            # Verify we can read these files with pypdf
            with open(self.test_file1, 'rb') as file1, open(self.test_file2, 'rb') as file2:
                pdf1 = PdfReader(file1)
                pdf2 = PdfReader(file2)
                print(f"Test file 1 has {len(pdf1.pages)} pages")
                print(f"Test file 2 has {len(pdf2.pages)} pages")
        except (FileNotFoundError, IOError, ValueError) as exc:
            self.fail(f"Test PDF files are not valid: {exc}")

        output_path = os.path.join(self.test_dir, 'merged.pdf')
        result = merge_pdfs([self.test_file1, self.test_file2], output_path)

        # Add debug output to help diagnose failure
        if not result['success']:
            print(f"Error merging PDFs: {result['error']}")

        self.assertTrue(result['success'])
        self.assertIsNotNone(result['path'])
        self.assertIsNone(result['error'])
        self.assertTrue(os.path.exists(result['path']))
        self.assertTrue(os.path.getsize(result['path']) > 0, "Merged PDF file is empty")

    def test_merge_pdfs_with_custom_filename(self):
        """Test merging PDFs with a custom filename."""
        output_path = os.path.join(self.test_dir, 'merged.pdf')
        custom_filename = 'custom_name'

        result = merge_pdfs([self.test_file1, self.test_file2], output_path, custom_filename)

        # Add debug output to help diagnose failure
        if not result['success']:
            print(f"Error merging PDFs: {result['error']}")

        self.assertTrue(result['success'])
        self.assertTrue(os.path.basename(result['path']) == 'custom_name.pdf')

    def test_merge_pdfs_nonexistent_files(self):
        """Test error handling when attempting to merge nonexistent files."""
        output_path = os.path.join(self.test_dir, 'merged.pdf')
        result = merge_pdfs(['nonexistent1.pdf', 'nonexistent2.pdf'], output_path)

        self.assertFalse(result['success'])
        self.assertIsNotNone(result['error'])

    def test_merge_pdfs_invalid_files(self):
        """Test error handling when attempting to merge invalid PDF files."""
        # Create an invalid file
        invalid_file = os.path.join(self.test_dir, 'invalid.pdf')
        with open(invalid_file, 'w', encoding='utf-8') as file:
            file.write('This is not a PDF file')
        output_path = os.path.join(self.test_dir, 'merged.pdf')
        result = merge_pdfs([invalid_file, self.test_file1], output_path)

        self.assertFalse(result['success'])
        self.assertIsNotNone(result['error'])
