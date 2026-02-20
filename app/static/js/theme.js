/**
 * theme.js - Handles Dark/Light theme toggling
 * Theme is applied EARLY via inline script in <head> (base.html).
 * This file only handles the toggle button interaction.
 */
document.addEventListener('DOMContentLoaded', function () {
  const toggleBtn = document.getElementById('themeToggle');
  if (!toggleBtn) return;

  // Set initial icon based on current state
  const isLight = document.documentElement.classList.contains('light-mode');
  toggleBtn.textContent = isLight ? '☀️' : '🌙';

  toggleBtn.addEventListener('click', function (e) {
    e.preventDefault();
    document.documentElement.classList.toggle('light-mode');
    document.body.classList.toggle('light-mode');

    const nowLight = document.documentElement.classList.contains('light-mode');
    localStorage.setItem('theme', nowLight ? 'light' : 'dark');
    toggleBtn.textContent = nowLight ? '☀️' : '🌙';
  });
});
