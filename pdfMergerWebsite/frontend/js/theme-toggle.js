document.addEventListener('DOMContentLoaded', function() {
  console.log("Theme toggle script loaded"); // Add this line for debugging
  
  // Make sure the theme toggle button exists in the DOM
  const themeToggle = document.getElementById('theme-toggle');
  if (!themeToggle) {
    console.error("Theme toggle button not found in the DOM");
    return;
  }
  
  const prefersDarkScheme = window.matchMedia('(prefers-color-scheme: dark)');
  
  // Add transition class to body after page load to prevent flash
  setTimeout(() => {
    document.body.classList.add('theme-transition');
  }, 100);
  
  // Check for saved theme preference or use OS preference
  const getCurrentTheme = () => {
    const savedTheme = localStorage.getItem('theme');
    console.log("Saved theme from localStorage:", savedTheme); // Add this line for debugging
    if (savedTheme) {
      return savedTheme;
    }
    return prefersDarkScheme.matches ? 'dark' : 'light';
  };
  
  // Apply the current theme
  const applyTheme = (theme) => {
    console.log("Applying theme:", theme); // Add this line for debugging
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
  };
  
  // Initialize theme
  const currentTheme = getCurrentTheme();
  applyTheme(currentTheme);
  
  // Toggle theme when button is clicked
  themeToggle.addEventListener('click', () => {
    console.log("Theme toggle button clicked"); // Add this line for debugging
    const currentTheme = document.documentElement.getAttribute('data-theme');
    console.log("Current theme:", currentTheme); // Add this line for debugging
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    console.log("Switching to:", newTheme); // Add this line for debugging
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
});