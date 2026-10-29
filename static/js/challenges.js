/**
 * challenges.js
 * Menangani interaksi tombol Check-in, Ikuti, Berhenti, serta Filter Kategori
 * secara asinkron (AJAX / Fetch API) dan menampilkan notifikasi popover toast.
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

  if (toastTitle) toastTitle.textContent = title;
  if (toastMessage) toastMessage.textContent = message;

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
          // Abaikan jika popover sudah ditutup
        }
      } else {
        toastComponent.style.display = 'none';
      }
    }, 300);
  }, duration);
}

function formatAngkaId(num) {
  if (typeof num !== 'number') return num;
  return num.toLocaleString('id-ID');
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function getCsrfToken(form) {
  return (
    form?.querySelector('[name=csrfmiddlewaretoken]')?.value ||
    document.querySelector('[name=csrfmiddlewaretoken]')?.value ||
    (document.cookie.match(/csrftoken=([^;]+)/) || [])[1] ||
    ''
  );
}

function bukaLencanaDiDOM(namaLencana) {
  if (!namaLencana) return;
  const badgeEl = document.querySelector(`.badge[data-badge-name="${namaLencana}"]`);
  if (badgeEl && badgeEl.classList.contains('badge--locked')) {
    const tone = badgeEl.getAttribute('data-badge-tone') || 'amber';
    const icon = badgeEl.getAttribute('data-badge-icon') || 'award';
    badgeEl.className = 'badge';
    badgeEl.innerHTML = `<span class="disc tone-${tone}"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><use href="#i-${icon}"/></svg></span>${escapeHtml(namaLencana)}`;

    const countEl = document.getElementById('badge-owned-count');
    if (countEl) {
      const saatIni = parseInt(countEl.textContent, 10) || 0;
      countEl.textContent = saatIni + 1;
    }
  }
}

function perbaruiDOMCheckin(detail) {
  if (!detail) return;
  const headerPoints = document.getElementById('header-points');
  if (headerPoints && typeof detail.total_points !== 'undefined') {
    headerPoints.textContent = formatAngkaId(detail.total_points);
  }

  const headerStreak = document.getElementById('header-streak-text');
  if (headerStreak && typeof detail.streak !== 'undefined') {
    headerStreak.textContent = `Streak ${detail.streak} hari`;
  }

  const doneDaysEl = document.getElementById('active-done-days');
  if (doneDaysEl && typeof detail.done_days !== 'undefined') {
    doneDaysEl.textContent = detail.done_days;
  }

  const percentEl = document.getElementById('active-percent');
  if (percentEl && typeof detail.percent !== 'undefined') {
    percentEl.textContent = `${detail.percent}%`;
  }

  const sisaEl = document.getElementById('active-sisa');
  if (sisaEl && typeof detail.total_days !== 'undefined' && typeof detail.done_days !== 'undefined') {
    const sisa = detail.total_days - detail.done_days;
    sisaEl.textContent = sisa > 0 ? `${sisa} hari lagi` : 'Selesai';
  }

  const dotsContainer = document.getElementById('active-dots');
  if (dotsContainer && typeof detail.total_days !== 'undefined') {
    dotsContainer.innerHTML = '';
    for (let i = 0; i < detail.total_days; i++) {
      const dot = document.createElement('i');
      if (i >= detail.done_days) {
        dot.className = 'todo';
      }
      dotsContainer.appendChild(dot);
    }
  }

  const riskAlert = document.getElementById('alert-streak-risk');
  if (riskAlert) {
    riskAlert.remove();
  }

  if (detail.badge) {
    bukaLencanaDiDOM(detail.badge);
  }
  if (Array.isArray(detail.streak_badges)) {
    detail.streak_badges.forEach(bukaLencanaDiDOM);
  }
}

const cycleClasses = ['card--a', 'card--b', 'card--c', 'card--d'];

function renderChallengesList(items) {
  const grid = document.getElementById('challenge-grid');
  if (!grid) return;

  if (!items || items.length === 0) {
    grid.innerHTML = '<li class="card card--a challenge"><p>Belum ada tantangan di kategori ini.</p></li>';
    return;
  }

  const isAuth = grid.getAttribute('data-is-authenticated') === 'true';
  const isSuperuser = grid.getAttribute('data-is-superuser') === 'true';
  const loginUrl = grid.getAttribute('data-login-url') || '/profil/login/';
  const csrfToken = getCsrfToken();

  let html = '';
  items.forEach((item, index) => {
    const cycleClass = cycleClasses[index % cycleClasses.length];
    const emphasisClass = item.is_joined ? ' card--emphasis' : '';

    let superuserActions = '';
    if (isSuperuser) {
      superuserActions = `
        <a class="btn-edit" href="/challenges/${item.id}/ubah/" title="Ubah tantangan" style="color: var(--color-stone-text-subtle); display: inline-flex; align-items: center; padding: 4px;" aria-label="Ubah tantangan ${escapeHtml(item.title)}">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><use href="#i-pencil"/></svg>
        </a>
        <a class="btn-delete" href="/challenges/${item.id}/hapus/" title="Hapus tantangan" style="color: var(--color-error-text); display: inline-flex; align-items: center; padding: 4px;" aria-label="Hapus tantangan ${escapeHtml(item.title)}">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><use href="#i-trash-2"/></svg>
        </a>
      `;
    }

    let joinAction = '';
    if (isAuth) {
      if (item.is_joined) {
        joinAction = '<span class="join join--on"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><use href="#i-check"/></svg>Diikuti</span>';
      } else {
        joinAction = `
          <form method="post" data-challenge-form="ikut" data-challenge-id="${item.id}">
            <input type="hidden" name="csrfmiddlewaretoken" value="${csrfToken}">
            <input type="hidden" name="aksi" value="ikut">
            <input type="hidden" name="tantangan_id" value="${item.id}">
            <button class="join" type="submit">Ikuti</button>
          </form>
        `;
      }
    } else {
      joinAction = `<a class="join" href="${loginUrl}">Ikuti</a>`;
    }

    html += `
      <li class="card ${cycleClass}${emphasisClass} challenge">
        <div class="top">
          <span class="icon-disc tone-${item.tone || 'amber'}"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><use href="#i-${item.icon || 'star'}"/></svg></span>
          <div style="display: flex; gap: 8px; align-items: center;">
            <span class="pill pill--amber">+${formatAngkaId(item.points)} poin</span>
            ${superuserActions}
          </div>
        </div>
        <h3>${escapeHtml(item.title)}</h3>
        <p>${escapeHtml(item.description)}</p>
        <div class="foot">
          <small>${item.duration_days} hari, ${formatAngkaId(item.participants)} peserta</small>
          ${joinAction}
        </div>
      </li>
    `;
  });

  grid.innerHTML = html;
}

function initCategoryFilter() {
  const chipsContainer = document.getElementById('challenge-category-chips');
  if (!chipsContainer) return;

  chipsContainer.addEventListener('click', async (event) => {
    const chip = event.target.closest('a[data-category]');
    if (!chip) return;

    event.preventDefault();

    const category = chip.getAttribute('data-category');
    const href = chip.getAttribute('href');

    chipsContainer.querySelectorAll('.chip').forEach((c) => c.classList.remove('chip--active'));
    chip.classList.add('chip--active');

    if (window.location.search !== (category ? `?kategori=${category}` : '')) {
      window.history.pushState({ category }, '', href);
    }

    const grid = document.getElementById('challenge-grid');
    if (grid) {
      grid.style.opacity = '0.5';
      grid.style.pointerEvents = 'none';
      grid.style.transition = 'opacity 0.15s ease';
    }

    try {
      const url = category ? `/api/tantangan/?kategori=${encodeURIComponent(category)}` : '/api/tantangan/';
      const response = await fetch(url, {
        headers: { 'Accept': 'application/json' }
      });
      if (response.ok) {
        const data = await response.json();
        renderChallengesList(data);
      }
    } catch (err) {
      console.error('Category filter fetch error:', err);
    } finally {
      if (grid) {
        grid.style.opacity = '1';
        grid.style.pointerEvents = '';
      }
    }
  });

  window.addEventListener('popstate', (event) => {
    const category = event.state?.category ?? new URLSearchParams(window.location.search).get('kategori') ?? '';
    const targetChip = chipsContainer.querySelector(`a[data-category="${category}"]`);
    if (targetChip) {
      chipsContainer.querySelectorAll('.chip').forEach((c) => c.classList.remove('chip--active'));
      targetChip.classList.add('chip--active');
    }
    const grid = document.getElementById('challenge-grid');
    if (grid) {
      grid.style.opacity = '0.5';
      grid.style.pointerEvents = 'none';
      grid.style.transition = 'opacity 0.15s ease';
    }
    const url = category ? `/api/tantangan/?kategori=${encodeURIComponent(category)}` : '/api/tantangan/';
    fetch(url, { headers: { 'Accept': 'application/json' } })
      .then((res) => res.json())
      .then((data) => renderChallengesList(data))
      .catch((err) => console.error(err))
      .finally(() => {
        if (grid) {
          grid.style.opacity = '1';
          grid.style.pointerEvents = '';
        }
      });
  });
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

  initCategoryFilter();

  document.addEventListener('submit', async (event) => {
    const form = event.target.closest('form[data-challenge-form]');
    if (!form) return;

    event.preventDefault();

    const aksi = form.getAttribute('data-challenge-form');
    const challengeId = form.getAttribute('data-challenge-id');
    const csrfToken = getCsrfToken(form);

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

          perbaruiDOMCheckin(data.data);
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
