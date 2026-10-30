/**
 * challenges.js
 * Modul interaktivitas client-side untuk Eco-Challenges (Modul 3).
 */

// ============================================================================
// 1. TOAST MANAGER
// ============================================================================
const ToastManager = {
  timer: null,

  show(title, message, type = 'normal', duration = 3000) {
    const el = document.getElementById('toast-component');
    const titleEl = document.getElementById('toast-title');
    const msgEl = document.getElementById('toast-message');

    if (!el) return;

    el.classList.remove('toast-success', 'toast-error', 'toast-normal');
    if (type === 'success') {
      el.classList.add('toast-success');
    } else if (type === 'error') {
      el.classList.add('toast-error');
    } else {
      el.classList.add('toast-normal');
    }

    if (titleEl) titleEl.textContent = title;
    if (msgEl) msgEl.textContent = message;

    clearTimeout(this.timer);

    if (typeof el.showPopover === 'function') {
      if (!el.matches(':popover-open')) {
        el.showPopover();
        void el.offsetHeight;
      }
    } else {
      el.style.display = 'flex';
    }

    el.classList.remove('toast-hidden');
    el.classList.add('toast-show');

    this.timer = setTimeout(() => {
      el.classList.remove('toast-show');
      el.classList.add('toast-hidden');
      setTimeout(() => {
        if (typeof el.hidePopover === 'function') {
          try {
            el.hidePopover();
          } catch (e) {
            // Abaikan jika popover sudah ditutup
          }
        } else {
          el.style.display = 'none';
        }
      }, 300);
    }, duration);
  },

  checkPending() {
    const pending = sessionStorage.getItem('pending_toast');
    if (pending) {
      sessionStorage.removeItem('pending_toast');
      try {
        const data = JSON.parse(pending);
        this.show(data.title, data.message, data.type);
      } catch (e) {
        // Abaikan parse error
      }
    }
  },
};

// ============================================================================
// 2. HELPER UTILITIES
// ============================================================================
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

// ============================================================================
// 3. OPTIMISTIC UI UPDATES & ROLLBACK HANDLERS
// ============================================================================
const OptimisticManager = {
  // Simpan snapshot state sebelumnya untuk rollback bila request gagal
  snapshot: {},

  applyCheckin(form) {
    const submitBtn = form.querySelector('button[type=submit]');
    const btnText = form.querySelector('#btn-checkin-text');
    const doneDaysEl = document.getElementById('active-done-days');
    const percentEl = document.getElementById('active-percent');
    const dotsEl = document.getElementById('active-dots');

    const totalDays = parseInt(dotsEl?.getAttribute('data-total-days'), 10) || 7;
    const currentDone = parseInt(doneDaysEl?.textContent, 10) || 0;

    this.snapshot.checkin = {
      buttonDisabled: submitBtn ? submitBtn.disabled : false,
      buttonText: btnText ? btnText.textContent : '',
      doneDays: doneDaysEl ? doneDaysEl.textContent : '',
      percent: percentEl ? percentEl.textContent : '',
      dotsHTML: dotsEl ? dotsEl.innerHTML : '',
    };

    // Optimistic Visual Update
    if (submitBtn) submitBtn.disabled = true;
    if (btnText) btnText.textContent = 'Mencatat check-in...';

    const newDone = Math.min(currentDone + 1, totalDays);
    if (doneDaysEl) doneDaysEl.textContent = newDone;
    if (percentEl) percentEl.textContent = `${Math.round((newDone / totalDays) * 100)}%`;

    if (dotsEl) {
      dotsEl.innerHTML = '';
      for (let i = 0; i < totalDays; i++) {
        const dot = document.createElement('i');
        if (i >= newDone) {
          dot.className = 'todo';
        }
        dotsEl.appendChild(dot);
      }
    }
  },

  rollbackCheckin(form, isAlreadyChecked = false) {
    const s = this.snapshot.checkin;
    if (!s) return;

    const submitBtn = form.querySelector('button[type=submit]');
    const btnText = form.querySelector('#btn-checkin-text');
    const doneDaysEl = document.getElementById('active-done-days');
    const percentEl = document.getElementById('active-percent');
    const dotsEl = document.getElementById('active-dots');

    if (submitBtn) submitBtn.disabled = isAlreadyChecked ? true : s.buttonDisabled;
    if (btnText) btnText.textContent = isAlreadyChecked ? 'Sudah check-in hari ini' : s.buttonText;
    if (doneDaysEl) doneDaysEl.textContent = s.doneDays;
    if (percentEl) percentEl.textContent = s.percent;
    if (dotsEl) dotsEl.innerHTML = s.dotsHTML;
  },

  applyIkuti(cardEl) {
    if (!cardEl) return;
    const footEl = cardEl.querySelector('.foot');
    this.snapshot.ikuti = {
      card: cardEl,
      footHTML: footEl ? footEl.innerHTML : '',
      hadEmphasis: cardEl.classList.contains('card--emphasis'),
    };

    cardEl.classList.add('card--emphasis');
    const joinBtn = cardEl.querySelector('button.join');
    if (joinBtn) {
      joinBtn.disabled = true;
      joinBtn.textContent = 'Mengikuti...';
    }
  },

  rollbackIkuti() {
    const s = this.snapshot.ikuti;
    if (!s || !s.card) return;
    if (!s.hadEmphasis) s.card.classList.remove('card--emphasis');
    const footEl = s.card.querySelector('.foot');
    if (footEl && s.footHTML) footEl.innerHTML = s.footHTML;
  },
};

// ============================================================================
// 4. DOM RE-RENDERING & STATE MUTATIONS
// ============================================================================
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
    riskAlert.style.display = 'none';
  }

  if (detail.badge_earned) {
    bukaLencanaDiDOM(detail.badge_earned);
  }
  if (Array.isArray(detail.streak_badges)) {
    detail.streak_badges.forEach((b) => bukaLencanaDiDOM(b));
  }
}

const cycleClasses = ['card--a', 'card--b', 'card--c', 'card--d'];

function renderChallengesList(items) {
  const grid = document.getElementById('challenge-grid');
  if (!grid) return;

  if (!items || items.length === 0) {
    grid.innerHTML = '<li class="card card--a challenge"><p>Belum ada tantangan yang sesuai.</p></li>';
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

// ============================================================================
// 5. DYNAMIC FILTERING & LIVE SEARCH WITH DEBOUNCE
// ============================================================================
const ChallengeFilter = {
  currentCategory: '',
  searchQuery: '',
  debounceTimer: null,

  async fetchAndRender() {
    const grid = document.getElementById('challenge-grid');
    if (grid) {
      grid.style.opacity = '0.5';
      grid.style.pointerEvents = 'none';
      grid.style.transition = 'opacity 0.15s ease';
    }

    const params = new URLSearchParams();
    if (this.currentCategory) params.set('kategori', this.currentCategory);
    if (this.searchQuery) params.set('q', this.searchQuery);

    const queryString = params.toString() ? `?${params.toString()}` : '';
    const apiUrl = `/api/tantangan/${queryString}`;

    try {
      const response = await fetch(apiUrl, {
        headers: { 'Accept': 'application/json' },
      });
      if (response.ok) {
        const data = await response.json();
        renderChallengesList(data);
      }
    } catch (err) {
      console.error('Filter fetch error:', err);
    } finally {
      if (grid) {
        grid.style.opacity = '1';
        grid.style.pointerEvents = '';
      }
    }
  },

  init() {
    const chipsContainer = document.getElementById('challenge-category-chips');
    const searchInput = document.getElementById('challenge-search-input');

    if (chipsContainer) {
      const activeChip = chipsContainer.querySelector('.chip--active');
      this.currentCategory = activeChip ? activeChip.getAttribute('data-category') || '' : '';

      chipsContainer.addEventListener('click', (e) => {
        const chip = e.target.closest('a[data-category]');
        if (!chip) return;
        e.preventDefault();

        this.currentCategory = chip.getAttribute('data-category') || '';
        chipsContainer.querySelectorAll('.chip').forEach((c) => c.classList.remove('chip--active'));
        chip.classList.add('chip--active');

        const params = new URLSearchParams(window.location.search);
        if (this.currentCategory) {
          params.set('kategori', this.currentCategory);
        } else {
          params.delete('kategori');
        }
        const newUrl = `${window.location.pathname}${params.toString() ? '?' + params.toString() : ''}`;
        window.history.pushState({ category: this.currentCategory, q: this.searchQuery }, '', newUrl);

        this.fetchAndRender();
      });
    }

    if (searchInput) {
      this.searchQuery = searchInput.value.trim();
      searchInput.addEventListener('input', (e) => {
        this.searchQuery = e.target.value.trim();
        clearTimeout(this.debounceTimer);
        this.debounceTimer = setTimeout(() => {
          this.fetchAndRender();
        }, 250);
      });
    }

    window.addEventListener('popstate', (e) => {
      const urlParams = new URLSearchParams(window.location.search);
      this.currentCategory = e.state?.category ?? urlParams.get('kategori') ?? '';
      this.searchQuery = e.state?.q ?? urlParams.get('q') ?? '';

      if (searchInput) searchInput.value = this.searchQuery;

      if (chipsContainer) {
        const targetChip = chipsContainer.querySelector(`a[data-category="${this.currentCategory}"]`);
        if (targetChip) {
          chipsContainer.querySelectorAll('.chip').forEach((c) => c.classList.remove('chip--active'));
          targetChip.classList.add('chip--active');
        }
      }

      this.fetchAndRender();
    });
  },
};

// ============================================================================
// 6. MAIN CONTROLLER & GLOBAL EVENT DELEGATION
// ============================================================================
document.addEventListener('DOMContentLoaded', () => {
  ToastManager.checkPending();
  ChallengeFilter.init();

  document.addEventListener('submit', async (event) => {
    const form = event.target.closest('form[data-challenge-form]');
    if (!form) return;

    event.preventDefault();

    const aksi = form.getAttribute('data-challenge-form');
    const challengeId = form.getAttribute('data-challenge-id');
    const csrfToken = getCsrfToken(form);

    // Apply Optimistic Visual Feedback
    if (aksi === 'checkin') {
      OptimisticManager.applyCheckin(form);
    } else if (aksi === 'ikut') {
      const cardEl = form.closest('.card.challenge');
      OptimisticManager.applyIkuti(cardEl);
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
          ToastManager.show('Berhasil', data.message || 'Check-in hari ini tercatat!', 'success');

          const btnText = form.querySelector('#btn-checkin-text');
          if (btnText) {
            btnText.textContent = data.completed ? 'Tantangan selesai' : 'Sudah check-in hari ini';
          }
          const submitButton = form.querySelector('button[type=submit]');
          if (submitButton) {
            submitButton.disabled = true;
          }

          perbaruiDOMCheckin(data.data);
        } else if (aksi === 'ikut' || aksi === 'berhenti') {
          sessionStorage.setItem('pending_toast', JSON.stringify({
            title: 'Berhasil',
            message: data.message || 'Aksi berhasil dilakukan!',
            type: 'success',
          }));
          ToastManager.show('Berhasil', data.message || 'Aksi berhasil dilakukan!', 'success');
          setTimeout(() => {
            window.location.reload();
          }, 600);
        }
      } else if (response.status === 409) {
        OptimisticManager.rollbackCheckin(form, true);
        ToastManager.show('Perhatian', data.error || 'Kamu sudah check-in hari ini.', 'error');
      } else if (response.status === 429) {
        if (aksi === 'checkin') OptimisticManager.rollbackCheckin(form);
        if (aksi === 'ikut') OptimisticManager.rollbackIkuti();
        ToastManager.show('Terlalu Cepat', data.error || 'Mohon tunggu beberapa detik sebelum mencoba lagi.', 'error');
      } else {
        if (aksi === 'checkin') OptimisticManager.rollbackCheckin(form);
        if (aksi === 'ikut') OptimisticManager.rollbackIkuti();
        ToastManager.show('Perhatian', data.error || 'Terjadi kesalahan. Silakan coba lagi.', 'error');
      }
    } catch (err) {
      console.error('Fetch error:', err);
      if (aksi === 'checkin') OptimisticManager.rollbackCheckin(form);
      if (aksi === 'ikut') OptimisticManager.rollbackIkuti();
      ToastManager.show('Koneksi Gagal', 'Gagal menghubungi server. Periksa koneksi internetmu.', 'error');
    }
  });
});
