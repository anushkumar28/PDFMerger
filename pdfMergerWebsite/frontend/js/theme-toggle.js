// Immediately-invoked function expression to avoid global scope pollution
(function() {
    // Wait for DOM to be fully loaded
    document.addEventListener('DOMContentLoaded', function() {
        console.log('Theme toggle script loaded');
        
        // Get the theme toggle button
        const themeToggle = document.getElementById('theme-toggle');
        
        if (!themeToggle) {
            console.error('Theme toggle button not found in the DOM');
            return;
        }
        
        // Function to set the theme with forced repaint
        function setTheme(themeName) {
            console.log('Setting theme to:', themeName);
            
            // Set the data attribute
            document.documentElement.setAttribute('data-theme', themeName);
            localStorage.setItem('theme', themeName);
            
            // Force a repaint by temporarily modifying the body
            const bodyElement = document.body;
            const originalDisplay = bodyElement.style.display;
            
            // Force a repaint
            bodyElement.style.display = 'none';
            const _ = bodyElement.offsetHeight; // Trigger a reflow
            bodyElement.style.display = originalDisplay;
            
            // Update body class as well for redundancy
            if (themeName === 'dark') {
                document.body.classList.add('dark-theme');
                document.body.classList.remove('light-theme');
            } else {
                document.body.classList.add('light-theme');
                document.body.classList.remove('dark-theme');
            }
            
            console.log('Theme application complete, data-theme is:', 
                       document.documentElement.getAttribute('data-theme'));
        }
        
        // Function to toggle the theme
        function toggleTheme() {
            console.log('Toggle theme clicked');
            
            // Get the current theme directly from the attribute
            const currentTheme = document.documentElement.getAttribute('data-theme') || 'light';
            console.log('Current theme detected as:', currentTheme);
            
            // Toggle to the opposite theme
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            console.log('Switching to:', newTheme);
            
            setTheme(newTheme);
            
            // Add this to your toggleTheme function after setting the theme
            function inspectThemeApplication() {
                // Check computed styles for key elements
                const bodyStyles = window.getComputedStyle(document.body);
                console.log('Body background color:', bodyStyles.backgroundColor);
                console.log('Body text color:', bodyStyles.color);
                
                // Check if variables are being computed
                const rootStyles = window.getComputedStyle(document.documentElement);
                console.log('--bg-color computed value:', rootStyles.getPropertyValue('--bg-color'));
                console.log('--text-color computed value:', rootStyles.getPropertyValue('--text-color'));
            }
            
            // Call this function after theme changes
            inspectThemeApplication();
        }
        
        // Set the initial theme on page load
        function initTheme() {
            console.log('Initializing theme');
            const savedTheme = localStorage.getItem('theme');
            
            if (savedTheme) {
                console.log('Found saved theme:', savedTheme);
                setTheme(savedTheme);
            } else if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
                console.log('Using system preference: dark');
                setTheme('dark');
            } else {
                console.log('Using default theme: light');
                setTheme('light');
            }
        }
        
        // Set initial theme
        initTheme();
        
        // Add click event to button
        themeToggle.addEventListener('click', toggleTheme);
    });
})();