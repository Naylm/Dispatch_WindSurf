/**
 * theme.js - Handles Dark/Light theme application and toggling
 */
(function () {
  // Apply theme on load
  try {
    var theme = localStorage.getItem('theme');
    if (theme === 'dark') {
      document.documentElement.classList.add('dark');
      if (document.body) {
        document.body.classList.add('dark');
      } else {
        document.addEventListener('DOMContentLoaded', function () {
          document.body.classList.add('dark');
        });
      }
    }
  } catch (e) {
    console.error('Theme storage error:', e);
  }

  // Handle Toggle Button
  document.addEventListener('DOMContentLoaded', function () {
    const toggleBtn = document.getElementById('themeToggle');
    if (toggleBtn) {
      toggleBtn.addEventListener('click', function (e) {
        e.preventDefault();
        document.body.classList.toggle('dark');
        document.documentElement.classList.toggle('dark'); // Ensure html tag is also toggled for Tailwind/tokens compatibility
        const isDark = document.body.classList.contains('dark');
        localStorage.setItem('theme', isDark ? 'dark' : 'light');

        // Optional: Update icon if needed (if using specific icons for states)
        // toggleBtn.textContent = isDark ? '☀️' : '🌙'; 
      });
    }
  });
})();
