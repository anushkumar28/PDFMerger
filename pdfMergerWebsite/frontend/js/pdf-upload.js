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
                <li class="file-item" tabindex="0">
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
    
    // Validate files before upload
    function validateFiles(files) {
        const errors = [];
        const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB limit
        
        if (files.length < 2) {
            errors.push('Please select at least two PDF files.');
            return errors;
        }
        
        for (let i = 0; i < files.length; i++) {
            const file = files[i];
            
            // Check file type
            if (!file.type || file.type !== 'application/pdf') {
                errors.push(`"${file.name}" is not a PDF file.`);
            }
            
            // Check file size
            if (file.size > MAX_FILE_SIZE) {
                errors.push(`"${file.name}" exceeds the 10MB file size limit.`);
            }
            
            // Check for empty files
            if (file.size === 0) {
                errors.push(`"${file.name}" is empty.`);
            }
        }
        
        return errors;
    }
    
    uploadForm.addEventListener('submit', function(event) {
        event.preventDefault();
        const files = fileInput.files;
        
        const validationErrors = validateFiles(files);
        if (validationErrors.length > 0) {
            showNotification(validationErrors.join('<br>'), 'error');
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
            
            // Track successful merge event
            trackEvent('PDF', 'Merge', 'Success');
            
            // Clear file input for next merge
            fileInput.value = '';
            fileListContainer.innerHTML = '';
            
            // Scroll to result
            resultDiv.scrollIntoView({ behavior: 'smooth' });
        })
        .catch(error => {
            console.error('Error:', error);
            
            // Handle specific errors
            handleApiError(error);
            
            // Track error event
            trackEvent('PDF', 'Merge', 'Error: ' + error.message);
        });
    });
    
    // More sophisticated error handling
    function handleApiError(error) {
        // Check for specific error types
        if (error.message.includes('size')) {
            showNotification('The files you selected exceed the maximum allowed size.', 'error');
        } else if (error.message.includes('type')) {
            showNotification('Only PDF files are supported.', 'error');
        } else if (navigator.onLine === false) {
            showNotification('You appear to be offline. Please check your connection.', 'warning');
        } else {
            resultDiv.innerHTML = `
                <div class="error-container">
                    <div class="error-icon">!</div>
                    <h3>Error Merging PDFs</h3>
                    <p>${error.message || 'Something went wrong. Please try again.'}</p>
                    <button class="retry-button" onclick="location.reload()">Try Again</button>
                </div>
            `;
        }
    }
    
    function showNotification(message, type) {
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.setAttribute('role', 'alert');
        notification.setAttribute('aria-live', 'assertive');
        notification.innerHTML = `
            <span class="notification-message">${message}</span>
            <button aria-label="Close notification" class="notification-close" onclick="this.parentElement.remove()">×</button>
        `;
        document.body.appendChild(notification);
        
        // Auto remove after 5 seconds
        setTimeout(() => {
            notification.classList.add('fade-out');
            setTimeout(() => notification.remove(), 500);
        }, 5000);
    }
    
    // Simple analytics tracking
    function trackEvent(category, action, label) {
        if (window.localStorage.getItem('allow_analytics') === 'true') {
            console.log('Tracked:', category, action, label);
        }
    }
    
    // Keyboard navigation
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && document.activeElement.classList.contains('file-item')) {
            // Handle keyboard selection of files
            document.activeElement.click();
        }
    });
    
    // Lazy load the Features section
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
                observer.unobserve(entry.target);
            }
        });
    }, {threshold: 0.1});

    document.querySelectorAll('.feature-card').forEach(card => {
        observer.observe(card);
    });
    
    // Theme toggle functionality
    const themeToggle = document.getElementById('theme-toggle');
    const prefersDarkScheme = window.matchMedia('(prefers-color-scheme: dark)');
    
    // Add transition class to body after page load to prevent flash
    setTimeout(() => {
        document.body.classList.add('theme-transition');
    }, 100);
    
    // Check for saved theme preference or use OS preference
    const getCurrentTheme = () => {
        const savedTheme = localStorage.getItem('theme');
        if (savedTheme) {
            return savedTheme;
        }
        return prefersDarkScheme.matches ? 'dark' : 'light';
    };
    
    // Apply the current theme
    const applyTheme = (theme) => {
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem('theme', theme);
    };
    
    // Initialize theme
    const currentTheme = getCurrentTheme();
    applyTheme(currentTheme);
    
    // Toggle theme when button is clicked
    themeToggle.addEventListener('click', () => {
        const newTheme = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
        applyTheme(newTheme);
        
        // Add animation effect
        themeToggle.classList.add('rotate');
        setTimeout(() => {
            themeToggle.classList.remove('rotate');
        }, 500);
    });
    
    // Listen for OS theme changes
    prefersDarkScheme.addEventListener('change', (e) => {
        const newTheme = e.matches ? 'dark' : 'light';
        applyTheme(newTheme);
    });
    
    // Add client-side validation
    uploadForm.addEventListener('submit', function(event) {
        // Prevent form submission if validation fails
        if (!validateFiles()) {
            event.preventDefault();
            return false;
        }
    });
    
    function validateFiles() {
        const files = fileInput.files;
        
        // Check if files exist
        if (!files || files.length < 2) {
            showError('Please select at least two PDF files.');
            return false;
        }
        
        // Check each file
        for (let i = 0; i < files.length; i++) {
            const file = files[i];
            
            // Check file type
            if (file.type !== 'application/pdf') {
                showError(`"${file.name}" is not a PDF file.`);
                return false;
            }
            
            // Check file size (10MB limit)
            const maxSize = 10 * 1024 * 1024;
            if (file.size > maxSize) {
                showError(`"${file.name}" exceeds the maximum file size of 10MB.`);
                return false;
            }
        }
        
        return true;
    }
    
    function showError(message) {
        // Display error message to user
        const errorElement = document.createElement('div');
        errorElement.className = 'error-message';
        errorElement.textContent = message;
        
        const result = document.getElementById('result');
        result.innerHTML = '';
        result.appendChild(errorElement);
    }
});