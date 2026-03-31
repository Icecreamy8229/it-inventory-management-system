(function () {
  'use strict';

  var STORAGE_KEY = 'theme';

  function getPreferred() {
    var stored = localStorage.getItem(STORAGE_KEY);
    if (stored === 'light' || stored === 'dark') return stored;
    return 'dark'; // default
  }

  function apply(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem(STORAGE_KEY, theme);
  }

  // Apply immediately (before paint) — this script should be in <head> or early in <body>
  apply(getPreferred());

  // Bind all toggle buttons once DOM is ready
  document.addEventListener('DOMContentLoaded', function () {
    var buttons = document.querySelectorAll('[data-toggle-theme]');
    buttons.forEach(function (btn) {
      btn.addEventListener('click', function () {
        var current = document.documentElement.getAttribute('data-theme') || 'dark';
        apply(current === 'dark' ? 'light' : 'dark');
      });
    });
  });
})();
