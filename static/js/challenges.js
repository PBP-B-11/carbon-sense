/**
 * challenges.js
 * Menangani interaksi tombol Check-in, Ikuti, dan Berhenti secara asinkron (Fetch API).
 */

document.addEventListener('DOMContentLoaded', () => {
  function formatAngkaId(num) {
    if (typeof num !== 'number') return num;
    return num.toLocaleString('id-ID');
  }

  function tampilkanPesan(pesan, tipe = 'success') {
    let alertContainer = document.querySelector('.container .alert-container');
    if (!alertContainer) {
      alertContainer = document.createElement('div');
      alertContainer.className = 'alert-container';
      const pageTitle = document.querySelector('.container .page-title');
      if (pageTitle && pageTitle.nextSibling) {
        pageTitle.parentNode.insertBefore(alertContainer, pageTitle.nextSibling);
      }
    }

    const alertDiv = document.createElement('div');
    alertDiv.className = 'alert';
    alertDiv.setAttribute('role', 'status');
    alertDiv.innerHTML = `
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><use href="#i-triangle-alert"/></svg>
      <div><p>${pesan}</p></div>
    `;

    alertContainer.prepend(alertDiv);
    setTimeout(() => {
      alertDiv.remove();
    }, 5000);
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
          tampilkanPesan(data.message || 'Aksi berhasil dilakukan!');

          if (aksi === 'checkin') {
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
            setTimeout(() => {
              window.location.reload();
            }, 600);
          }
        } else if (response.status === 409) {
          tampilkanPesan(data.error || 'Kamu sudah check-in hari ini.', 'warning');
          if (aksi === 'checkin' && submitButton) {
            submitButton.disabled = true;
          }
        } else {
          tampilkanPesan(data.error || 'Terjadi kesalahan. Silakan coba lagi.', 'error');
          if (submitButton) {
            submitButton.disabled = false;
          }
        }
      } catch (err) {
        console.error('Fetch error:', err);
        tampilkanPesan('Gagal menghubungi server. Periksa koneksi internetmu.', 'error');
        if (submitButton) {
          submitButton.disabled = false;
        }
      }
    });
  });
});
