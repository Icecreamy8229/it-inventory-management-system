(function () {
  var images = [];
  var current = 0;
  var overlay = null;
  var img = null;

  function open(index) {
    current = index;
    overlay = document.createElement('div');
    overlay.className = 'lightbox-overlay';
    overlay.addEventListener('click', function (e) {
      if (e.target === overlay) close();
    });

    var closeBtn = document.createElement('button');
    closeBtn.className = 'lightbox-close';
    closeBtn.innerHTML = '&times;';
    closeBtn.setAttribute('aria-label', 'Close');
    closeBtn.addEventListener('click', close);

    img = document.createElement('img');
    img.src = images[current];
    img.alt = 'Full size image';

    overlay.appendChild(closeBtn);
    overlay.appendChild(img);

    if (images.length > 1) {
      var prev = document.createElement('button');
      prev.className = 'lightbox-nav lightbox-prev';
      prev.innerHTML = '&#8249;';
      prev.setAttribute('aria-label', 'Previous image');
      prev.addEventListener('click', function (e) { e.stopPropagation(); navigate(-1); });

      var next = document.createElement('button');
      next.className = 'lightbox-nav lightbox-next';
      next.innerHTML = '&#8250;';
      next.setAttribute('aria-label', 'Next image');
      next.addEventListener('click', function (e) { e.stopPropagation(); navigate(1); });

      overlay.appendChild(prev);
      overlay.appendChild(next);
    }

    document.body.appendChild(overlay);
    document.addEventListener('keydown', onKey);
  }

  function close() {
    if (overlay) {
      overlay.remove();
      overlay = null;
      img = null;
    }
    document.removeEventListener('keydown', onKey);
  }

  function navigate(dir) {
    current = (current + dir + images.length) % images.length;
    if (img) img.src = images[current];
  }

  function onKey(e) {
    if (e.key === 'Escape') close();
    else if (e.key === 'ArrowLeft') navigate(-1);
    else if (e.key === 'ArrowRight') navigate(1);
  }

  document.addEventListener('click', function (e) {
    var thumb = e.target.closest('[data-lightbox]');
    if (!thumb) return;
    e.preventDefault();

    // Gather all lightbox links in the same container
    var container = thumb.parentElement;
    var links = container.querySelectorAll('[data-lightbox]');
    images = [];
    var clickedIndex = 0;
    links.forEach(function (link, i) {
      images.push(link.href);
      if (link === thumb) clickedIndex = i;
    });

    open(clickedIndex);
  });
})();
