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
                showError(data.error || 'An unknown error occurred');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showError('An unexpected error occurred. Please try again later.');
        });
    });

    // Use safer DOM methods instead of innerHTML
    function showError(message) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-container';
        
        const errorIcon = document.createElement('div');
        errorIcon.className = 'error-icon';
        errorIcon.textContent = '!';
        
        const heading = document.createElement('h3');
        heading.textContent = 'Error Merging PDFs';
        
        const paragraph = document.createElement('p');
        paragraph.textContent = message || 'Something went wrong. Please try again.';
        
        const button = document.createElement('button');
        button.className = 'retry-button';
        button.textContent = 'Try Again';
        button.addEventListener('click', () => location.reload());
        
        errorDiv.appendChild(errorIcon);
        errorDiv.appendChild(heading);
        errorDiv.appendChild(paragraph);
        errorDiv.appendChild(button);
        
        resultContainer.innerHTML = '';
        resultContainer.appendChild(errorDiv);
    }

    // Add keyboard navigation support
    const focusableElements = document.querySelectorAll('button, a, input');
    focusableElements.forEach(element => {
        if (!element.hasAttribute('tabindex')) {
            element.setAttribute('tabindex', '0');
        }
    });
});