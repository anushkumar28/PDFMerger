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
                handleDownload(data.download_link);
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

    // Add or update the function that handles PDF download
    function handleDownload(downloadLink) {
        // Show loading state
        const resultDiv = document.getElementById('result');
        resultDiv.innerHTML = '<p>Preparing your download...</p>';
        
        // Create a download button with event handling
        const downloadButton = document.createElement('a');
        downloadButton.href = downloadLink;
        downloadButton.className = 'download-btn';
        downloadButton.innerHTML = '<i class="fas fa-download"></i> Download Merged PDF';
        downloadButton.target = '_blank'; // Open in new tab
        
        // Add error handling
        downloadButton.addEventListener('click', function(event) {
            // Check if download completes
            const checkDownload = setTimeout(function() {
                // After 5 seconds, check if download started
                fetch(downloadLink, { method: 'HEAD' })
                    .then(response => {
                        if (!response.ok) {
                            showError('The file could not be downloaded. Please try merging again.');
                        }
                    })
                    .catch(() => {
                        showError('Download failed. The file might have been deleted or is not accessible.');
                    });
            }, 5000);
            
            // On successful navigation, clear the timeout
            window.addEventListener('blur', function() {
                clearTimeout(checkDownload);
            }, { once: true });
        });
        
        // Clear the result div and add the download button
        resultDiv.innerHTML = '';
        resultDiv.appendChild(downloadButton);
        
        // Add a message about file expiration
        const expirationNote = document.createElement('p');
        expirationNote.className = 'expiration-note';
        expirationNote.textContent = 'Note: This file will expire after 24 hours.';
        resultDiv.appendChild(expirationNote);
    }

    // Function to show errors
    function showError(message) {
        const resultDiv = document.getElementById('result');
        resultDiv.innerHTML = `
            <div class="error-message">
                <i class="fas fa-exclamation-triangle"></i>
                <p>${message}</p>
                <button onclick="window.location.reload()" class="retry-btn">Try Again</button>
            </div>
        `;
    }

    // Add keyboard navigation support
    const focusableElements = document.querySelectorAll('button, a, input');
    focusableElements.forEach(element => {
        if (!element.hasAttribute('tabindex')) {
            element.setAttribute('tabindex', '0');
        }
    });
});