document.addEventListener('DOMContentLoaded', function() {
    const uploadForm = document.getElementById('upload-form');
    // Change from 'file-input' to 'pdf-files' to match your HTML
    const fileInput = document.getElementById('pdf-files');
    const resultDiv = document.getElementById('result');
    
    uploadForm.addEventListener('submit', function(event) {
        event.preventDefault();
        const files = fileInput.files;

        if (files.length === 0) {
            alert('Please select at least one PDF file to upload.');
            return;
        }

        // Create loading indicator
        resultDiv.innerHTML = '<p>Merging PDFs, please wait...</p>';

        const formData = new FormData();
        for (let i = 0; i < files.length; i++) {
            // Change from 'pdf_files' to 'files' to match the server's expected parameter
            formData.append('files', files[i]);
            console.log('Adding file:', files[i].name);
        }

        // Update fetch URL to match your server endpoint
        fetch('/upload', {
            method: 'POST',
            body: formData
        })
        .then(response => {
            console.log('Response status:', response.status);
            if (!response.ok) {
                return response.json().then(data => {
                    console.error('Error details:', data);
                    throw new Error(data.error || 'Server error');
                });
            }
            return response.json();
        })
        .then(data => {
            console.log('Success:', data);
            // Create download link
            resultDiv.innerHTML = `
                <p>PDFs merged successfully!</p>
                <a href="${data.download_link}" download="merged_document.pdf" class="download-btn">
                    Download Merged PDF
                </a>`;
        })
        .catch(error => {
            console.error('Error:', error);
            resultDiv.innerHTML = `<p class="error">Error: ${error.message}</p>`;
        });
    });
});