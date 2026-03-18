(function () {
  'use strict';

  var SCAN_THRESHOLD_MS = 50;

  function initBarcodeDetector(elementId, onScan) {
    var el = document.getElementById(elementId);
    if (!el) return;

    var buffer = [];
    var lastKeyTime = 0;

    el.addEventListener('keydown', function (e) {
      var now = Date.now();

      if (e.key === 'Enter') {
        // Check if we have buffered chars and all arrived within threshold
        if (buffer.length > 0 && isScan(buffer)) {
          e.preventDefault();
          var scanned = buffer.map(function (b) { return b.char; }).join('');
          buffer = [];
          lastKeyTime = 0;
          onScan(el, scanned);
        } else {
          // Normal enter — reset buffer
          buffer = [];
          lastKeyTime = 0;
        }
        return;
      }

      // Only track printable single characters
      if (e.key.length !== 1) return;

      if (buffer.length > 0 && (now - lastKeyTime) > SCAN_THRESHOLD_MS) {
        // Gap too large — reset, start fresh
        buffer = [];
      }

      buffer.push({ char: e.key, time: now });
      lastKeyTime = now;
    });
  }

  function isScan(buffer) {
    if (buffer.length < 2) return false;
    for (var i = 1; i < buffer.length; i++) {
      if ((buffer[i].time - buffer[i - 1].time) > SCAN_THRESHOLD_MS) {
        return false;
      }
    }
    return true;
  }

  // Search input: redirect to scan-lookup endpoint
  initBarcodeDetector('search-input', function (el, value) {
    window.location.href = '/equipment/scan-lookup?asset_tag=' + encodeURIComponent(value);
  });

  // Asset tag input: just populate the field value
  initBarcodeDetector('asset-tag-input', function (el, value) {
    el.value = value;
  });
})();
