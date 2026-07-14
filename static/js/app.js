/* Global UI behavior: theme toggle, sidebar toggle, drag-and-drop uploads,
   AJAX loading states, and score-ring rendering. */

document.addEventListener('DOMContentLoaded', function () {
  const root = document.documentElement;
  const themeToggle = document.getElementById('themeToggle');
  const sidebarToggle = document.getElementById('sidebarToggle');
  const sidebar = document.getElementById('sidebar');

  if (themeToggle) {
    themeToggle.addEventListener('click', function () {
      const current = root.getAttribute('data-theme');
      const next = current === 'dark' ? 'light' : 'dark';
      root.setAttribute('data-theme', next);
      localStorage.setItem('resumeOptimizerTheme', next);
    });
  }
  const savedTheme = localStorage.getItem('resumeOptimizerTheme');
  if (savedTheme) root.setAttribute('data-theme', savedTheme);

  if (sidebarToggle) {
    sidebarToggle.addEventListener('click', () => sidebar.classList.toggle('open'));
  }

  // Drag & drop upload zones (used on the resume upload page)
  document.querySelectorAll('[data-upload-zone]').forEach(function (zone) {
    const input = document.getElementById(zone.dataset.inputId);
    zone.addEventListener('click', () => input && input.click());
    ['dragenter', 'dragover'].forEach(evt =>
      zone.addEventListener(evt, e => { e.preventDefault(); zone.classList.add('dragover'); })
    );
    ['dragleave', 'drop'].forEach(evt =>
      zone.addEventListener(evt, e => { e.preventDefault(); zone.classList.remove('dragover'); })
    );
    zone.addEventListener('drop', function (e) {
      if (input && e.dataTransfer.files.length) {
        input.files = e.dataTransfer.files;
        input.dispatchEvent(new Event('change'));
      }
    });
    if (input) {
      input.addEventListener('change', function () {
        const label = zone.querySelector('[data-filename-label]');
        if (label && input.files.length) label.textContent = input.files[0].name;
      });
    }
  });

  // Character counter for the job description textarea
  const jdTextarea = document.getElementById('jd-textarea');
  const jdCounter = document.getElementById('jd-char-counter');
  if (jdTextarea && jdCounter) {
    const update = () => { jdCounter.textContent = jdTextarea.value.length + ' characters'; };
    jdTextarea.addEventListener('input', update);
    update();
  }

  // Simple SVG score rings: <div class="score-ring" data-score="82" data-color="#12D6B8">
  document.querySelectorAll('.score-ring[data-score]').forEach(function (el) {
    const score = Math.max(0, Math.min(100, parseInt(el.dataset.score, 10) || 0));
    const color = el.dataset.color || '#12D6B8';
    const radius = 50, circumference = 2 * Math.PI * radius;
    const offset = circumference * (1 - score / 100);
    el.innerHTML = `
      <svg width="118" height="118" viewBox="0 0 118 118">
        <circle cx="59" cy="59" r="${radius}" stroke="rgba(128,128,128,0.2)" stroke-width="10" fill="none"/>
        <circle cx="59" cy="59" r="${radius}" stroke="${color}" stroke-width="10" fill="none"
          stroke-linecap="round" stroke-dasharray="${circumference}" stroke-dashoffset="${offset}"
          style="transition: stroke-dashoffset 1s ease;"/>
      </svg>
      <div class="ring-value">${score}</div>`;
  });

  // Forms that trigger long-running AI calls: show a loading overlay
  document.querySelectorAll('form[data-ai-loading]').forEach(function (form) {
    form.addEventListener('submit', function () {
      const btn = form.querySelector('button[type=submit]');
      if (btn) {
        btn.disabled = true;
        btn.dataset.originalText = btn.innerHTML;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span> Analyzing with AI...';
      }
    });
  });
});
