/**
 * theme.js
 * Mengatur sinkronisasi status dan label tombol tema saat dokumen selesai dimuat.
 */

function updateToggleAria() {
  const toggleBtn = document.getElementById('theme-toggle');
  if (!toggleBtn) return;
  const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
  const label = isDark ? 'Beralih ke mode terang' : 'Beralih ke mode gelap';
  toggleBtn.setAttribute('aria-label', label);
  toggleBtn.setAttribute('title', label);
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', updateToggleAria);
} else {
  updateToggleAria();
}
