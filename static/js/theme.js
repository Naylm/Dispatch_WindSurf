(function () {
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
    // Ignore storage errors
  }
})();
