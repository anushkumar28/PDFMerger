document.addEventListener('DOMContentLoaded', function() {
    const uploadForm = document.getElementById('upload-form');
    const fileInput = document.getElementById('pdf-files');
    const resultDiv = document.getElementById('result');
    const filenameInput = document.getElementById('output-filename');
    const fileListContainer = document.createElement('div');
    fileListContainer.className = 'file-list-container';
    uploadForm.after(fileListContainer);
    
    // Update file list when files are selected
    fileInput.addEventListener('change', function() {
        displaySelectedFiles(this.files);
    });
    
    function displaySelectedFiles(files) {
        if (files.length === 0) {
            fileListContainer.innerHTML = '';
            return;
        }
        
        let html = `
            <h3>Selected Files <span class="file-count">${files.length}</span></h3>
            <ul class="file-list">
        `;
        
        for (let i = 0; i < files.length; i++) {
            const file = files[i];
            const fileSize = formatFileSize(file.size);
            const fileExtension = file.name.split('.').pop().toLowerCase();
            
            html += `
                <li class="file-item">
                    <div class="file-icon pdf-icon">
                        <span class="file-extension">.${fileExtension}</span>
                    </div>
                    <div class="file-info">
                        <div class="file-name">${file.name}</div>
                        <div class="file-size">${fileSize}</div>
                    </div>
                </li>
            `;
        }
        
        html += '</ul>';
        fileListContainer.innerHTML = html;
    }
    
    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(1024));
        return parseFloat((bytes / Math.pow(1024, i)).toFixed(2)) + ' ' + sizes[i];
    }
    
    uploadForm.addEventListener('submit', function(event) {
        event.preventDefault();
        const files = fileInput.files;

        if (files.length < 2) {
            showNotification('Please select at least two PDF files to merge.', 'error');
            return;
        }

        // Create loading indicator
        resultDiv.innerHTML = `
            <div class="loading-container">
                <div class="loading-spinner"></div>
                <p>Merging your PDFs...</p>
                <p class="loading-info">This may take a moment depending on file sizes</p>
            </div>
        `;

        const formData = new FormData();
        for (let i = 0; i < files.length; i++) {
            formData.append('files', files[i]);
        }
        
        // Add output filename if provided
        if (filenameInput && filenameInput.value.trim()) {
            formData.append('output_filename', filenameInput.value.trim());
        }

        fetch('/upload', {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(data => {
                    throw new Error(data.error || 'Server error');
                });
            }
            return response.json();
        })
        .then(data => {
            console.log('Success:', data);
            resultDiv.innerHTML = `
                <div class="success-container">
                    <div class="success-icon">✓</div>
                    <h3>PDFs Merged Successfully!</h3>
                    <p>Your PDF files have been combined into a single document.</p>
                    <a href="${data.download_link}" class="download-button" download>
                        <span class="download-icon">↓</span> Download PDF
                    </a>
                </div>
            `;
            
            // Clear file input for next merge
            fileInput.value = '';
            fileListContainer.innerHTML = '';
            
            // Scroll to result
            resultDiv.scrollIntoView({ behavior: 'smooth' });
        })
        .catch(error => {
            console.error('Error:', error);
            resultDiv.innerHTML = `
                <div class="error-container">
                    <div class="error-icon">!</div>
                    <h3>Error Merging PDFs</h3>
                    <p>${error.message || 'Something went wrong. Please try again.'}</p>
                    <button class="retry-button" onclick="location.reload()">Try Again</button>
                </div>
            `;
        });
    });
    
    function showNotification(message, type) {
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.innerHTML = `
            <span class="notification-message">${message}</span>
            <span class="notification-close" onclick="this.parentElement.remove()">×</span>
        `;
        document.body.appendChild(notification);
        
        // Auto remove after 5 seconds
        setTimeout(() => {
            notification.classList.add('fade-out');
            setTimeout(() => notification.remove(), 500);
        }, 5000);
    }
});