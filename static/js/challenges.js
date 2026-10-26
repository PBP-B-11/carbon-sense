/**
 * challenges.js
 * Menangani interaksi tombol Check-in, Ikuti, dan Berhenti secara asinkron (Fetch API).
 */

document.addEventListener('DOMContentLoaded', () => {
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
              btnText.textContent = 'Sudah check-in hari ini';
            }
            if (submitButton) {
              submitButton.disabled = true;
            }

            if (data.data && typeof data.data.streak !== 'undefined') {
              const streakPill = document.querySelector('.pill--streak');
              if (streakPill) {
                streakPill.innerHTML = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><use href="#i-flame"/></svg>Streak ${data.data.streak} hari`;
              }
            }

            setTimeout(() => {
              window.location.reload();
            }, data.completed ? 1200 : 1000);
          } else if (aksi === 'ikut' || aksi === 'berhenti') {
            setTimeout(() => {
              window.location.reload();
            }, 800);
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
