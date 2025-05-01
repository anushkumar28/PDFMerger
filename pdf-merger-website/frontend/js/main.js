// This file handles user interactions and form submissions for the PDF merger website.

document.addEventListener('DOMContentLoaded', function() {
    const uploadForm = document.getElementById('upload-form');
    const fileInput = document.getElementById('pdf-files');
    const outputFilenameInput = document.getElementById('output-filename'); // New line
    const mergeButton = document.getElementById('merge-button');
    const downloadLink = document.getElementById('download-link');
    const fileListContainer = document.createElement('div');
    const resultContainer = document.createElement('div');
    
    // Add file list container after the form
    fileListContainer.id = 'selected-files';
    fileListContainer.className = 'file-list-container';
    uploadForm.after(fileListContainer);
    
    // Add result container after the file list
    resultContainer.id = 'result-container';
    resultContainer.className = 'result-container';
    fileListContainer.after(resultContainer);
    
    // Update the selected files list when files are selected
    fileInput.addEventListener('change', function() {
        displaySelectedFiles(this.files);
    });

    function displaySelectedFiles(files) {
        if (files.length === 0) {
            fileListContainer.innerHTML = '';
            return;
        }
        
        let html = '<h3>Selected Files</h3><ul class="file-list">';
        
        for (let i = 0; i < files.length; i++) {
            const file = files[i];
            const fileSize = (file.size / 1024).toFixed(2) + ' KB';
            html += `
                <li class="file-item">
                    <div class="file-info">
                        <span class="file-name">${file.name}</span>
                        <span class="file-size">${fileSize}</span>
                    </div>
                </li>
            `;
        }
        
        html += '</ul>';
        fileListContainer.innerHTML = html;
    }

    uploadForm.addEventListener('submit', function(event) {
        event.preventDefault();
        const files = fileInput.files;

        if (files.length < 2) {
            alert('Please select at least two PDF files to merge.');
            return;
        }

        // Show loading state
        resultContainer.innerHTML = '<div class="loading">Merging PDFs, please wait...</div>';
        
        const formData = new FormData();
        for (let i = 0; i < files.length; i++) {
            formData.append('files', files[i]);
        }
        
        // Add the custom filename to the form data if provided
        const customFilename = outputFilenameInput.value.trim();
        if (customFilename) {
            formData.append('output_filename', customFilename);
        }

        // Send the request to the server
        fetch('/upload', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.download_link) {
                // Success case
                resultContainer.innerHTML = `
                    <div class="success-message">
                        <h3>PDFs Merged Successfully!</h3>
                        <p>Your files have been combined into a single PDF document.</p>
                        <a href="${data.download_link}" class="download-button" download>Download Merged PDF</a>
                    </div>
                `;
            } else {
                // Error case
                resultContainer.innerHTML = `
                    <div class="error-message">
                        <h3>Error Merging PDFs</h3>
                        <p>${data.error || 'An unknown error occurred'}</p>
                    </div>
                `;
            }
        })
        .catch(error => {
            console.error('Error:', error);
            resultContainer.innerHTML = `
                <div class="error-message">
                    <h3>Error Merging PDFs</h3>
                    <p>An unexpected error occurred. Please try again later.</p>
                    <p class="error-details">${error.message}</p>
                </div>
            `;
        });
    });
});