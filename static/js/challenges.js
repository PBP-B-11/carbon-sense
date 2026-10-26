/**
 * challenges.js
 * Menangani interaksi tombol Check-in, Ikuti, dan Berhenti secara asinkron (Fetch API)
 * serta menampilkan notifikasi menggunakan komponen toast.
 */

let toastTimer;

function showToast(title, message, type = 'normal', duration = 3000) {
  const toastComponent = document.getElementById('toast-component');
  const toastTitle = document.getElementById('toast-title');
  const toastMessage = document.getElementById('toast-message');

  if (!toastComponent) return;

  toastComponent.classList.remove('toast-success', 'toast-error', 'toast-normal');

  if (type === 'success') {
    toastComponent.classList.add('toast-success');
  } else if (type === 'error') {
    toastComponent.classList.add('toast-error');
  } else {
    toastComponent.classList.add('toast-normal');
  }

  toastTitle.textContent = title;
  toastMessage.textContent = message;

  clearTimeout(toastTimer);

  if (typeof toastComponent.showPopover === 'function') {
    if (!toastComponent.matches(':popover-open')) {
      toastComponent.showPopover();
      void toastComponent.offsetHeight;
    }
  } else {
    toastComponent.style.display = 'flex';
  }
  toastComponent.classList.remove('toast-hidden');
  toastComponent.classList.add('toast-show');

  toastTimer = setTimeout(() => {
    toastComponent.classList.remove('toast-show');
    toastComponent.classList.add('toast-hidden');
    toastTimer = setTimeout(() => {
      if (typeof toastComponent.hidePopover === 'function') {
        try {
          toastComponent.hidePopover();
        } catch (e) {
          // ignore if already hidden
        }
      } else {
        toastComponent.style.display = 'none';
      }
    }, 300);
  }, duration);
}

document.addEventListener('DOMContentLoaded', () => {
  const pendingToast = sessionStorage.getItem('pending_toast');
  if (pendingToast) {
    sessionStorage.removeItem('pending_toast');
    try {
      const data = JSON.parse(pendingToast);
      showToast(data.title, data.message, data.type);
    } catch (e) {}
  }

  function formatAngkaId(num) {
    if (typeof num !== 'number') return num;
    return num.toLocaleString('id-ID');
  }

  function bukaLencanaDiDOM(namaLencana) {
    if (!namaLencana) return;
    const badgeEl = document.querySelector(`.badge[data-badge-name="${namaLencana}"]`);
    if (badgeEl && badgeEl.classList.contains('badge--locked')) {
      const tone = badgeEl.getAttribute('data-badge-tone') || 'amber';
      const icon = badgeEl.getAttribute('data-badge-icon') || 'award';
      badgeEl.className = 'badge';
      badgeEl.innerHTML = `<span class="disc tone-${tone}"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><use href="#i-${icon}"/></svg></span>${namaLencana}`;

      const countEl = document.getElementById('badge-owned-count');
      if (countEl) {
        const saatIni = parseInt(countEl.textContent, 10) || 0;
        countEl.textContent = saatIni + 1;
      }
    }
  }

  document.querySelectorAll('form[data-challenge-form]').forEach((form) => {
    form.addEventListener('submit', async (event) => {
      event.preventDefault();

      const aksi = form.getAttribute('data-challenge-form');
      const challengeId = form.getAttribute('data-challenge-id');
      const csrfToken = form.querySelector('[name=csrfmiddlewaretoken]')?.value;

      const submitButton = form.querySelector('button[type=submit]');
      if (submitButton) {
        submitButton.disabled = true;
      }

      try {
        const response = await fetch(`/api/tantangan/${challengeId}/${aksi}/`, {
          method: 'POST',
          headers: {
            'X-CSRFToken': csrfToken,
            'Content-Type': 'application/json',
            'Accept': 'application/json',
          },
        });

        const data = await response.json();

        if (response.ok) {
          if (aksi === 'checkin') {
            showToast('Berhasil', data.message || 'Check-in hari ini tercatat!', 'success');

            const btnText = form.querySelector('#btn-checkin-text');
            if (btnText) {
              btnText.textContent = data.completed ? 'Tantangan selesai' : 'Sudah check-in hari ini';
            }
            if (submitButton) {
              submitButton.disabled = true;
            }

            if (data.data) {
              const headerPoints = document.getElementById('header-points');
              if (headerPoints && typeof data.data.total_points !== 'undefined') {
                headerPoints.textContent = formatAngkaId(data.data.total_points);
              }

              const headerStreak = document.getElementById('header-streak-text');
              if (headerStreak && typeof data.data.streak !== 'undefined') {
                headerStreak.textContent = `Streak ${data.data.streak} hari`;
              }

              const doneDaysEl = document.getElementById('active-done-days');
              if (doneDaysEl && typeof data.data.done_days !== 'undefined') {
                doneDaysEl.textContent = data.data.done_days;
              }

              const percentEl = document.getElementById('active-percent');
              if (percentEl && typeof data.data.percent !== 'undefined') {
                percentEl.textContent = `${data.data.percent}%`;
              }

              const sisaEl = document.getElementById('active-sisa');
              if (sisaEl) {
                const sisa = data.data.total_days - data.data.done_days;
                sisaEl.textContent = sisa > 0 ? `${sisa} hari lagi` : 'Selesai';
              }

              const dotsContainer = document.getElementById('active-dots');
              if (dotsContainer && typeof data.data.total_days !== 'undefined') {
                dotsContainer.innerHTML = '';
                for (let i = 0; i < data.data.total_days; i++) {
                  const dot = document.createElement('i');
                  if (i >= data.data.done_days) {
                    dot.className = 'todo';
                  }
                  dotsContainer.appendChild(dot);
                }
              }

              const riskAlert = document.getElementById('alert-streak-risk');
              if (riskAlert) {
                riskAlert.remove();
              }

              if (data.data.badge) {
                bukaLencanaDiDOM(data.data.badge);
              }
              if (Array.isArray(data.data.streak_badges)) {
                data.data.streak_badges.forEach(bukaLencanaDiDOM);
              }
            }
          } else if (aksi === 'ikut' || aksi === 'berhenti') {
            sessionStorage.setItem('pending_toast', JSON.stringify({
              title: 'Berhasil',
              message: data.message || 'Aksi berhasil dilakukan!',
              type: 'success'
            }));
            showToast('Berhasil', data.message || 'Aksi berhasil dilakukan!', 'success');
            setTimeout(() => {
              window.location.reload();
            }, 600);
          }
        } else if (response.status === 409) {
          showToast('Perhatian', data.error || 'Kamu sudah check-in hari ini.', 'error');
          if (aksi === 'checkin' && submitButton) {
            submitButton.disabled = true;
          }
        } else {
          showToast('Perhatian', data.error || 'Terjadi kesalahan. Silakan coba lagi.', 'error');
          if (submitButton) {
            submitButton.disabled = false;
          }
        }
      } catch (err) {
        console.error('Fetch error:', err);
        showToast('Koneksi Gagal', 'Gagal menghubungi server. Periksa koneksi internetmu.', 'error');
        if (submitButton) {
          submitButton.disabled = false;
        }
      }
    });
  });
});
