import {getJson} from './http.js';
import {toast} from './ui.js';

const SEARCH_DELAY = 300;

// Filter kategori, pencarian, urutan, dan "Muat lebih banyak" di feed tanpa reload halaman
export function initFilter() {
  const list = document.getElementById('post-list');
  const moreWrap = document.getElementById('load-more-wrap');
  const moreBtn = moreWrap.querySelector('.js-load-more');
  const chips = document.querySelectorAll('.js-filter');
  const form = document.querySelector('.feed-search');
  const queryInput = form.elements.q;
  const sortSelect = form.elements.sort;
  let latest = 0;
  let timer;

  function buildParams(category, page) {
    const params = new URLSearchParams();
    const query = queryInput.value.trim();
    if (category) params.set('category', category);
    if (query) params.set('q', query);
    if (sortSelect.value !== 'new') params.set('sort', sortSelect.value);
    if (page) params.set('page', page);
    return params;
  }

  async function fetchPage(category, page) {
    const res = await getJson(`${window.location.pathname}?${buildParams(category, page)}`);
    if (!res.ok) throw new Error('load failed');
    return res.json();
  }

  function showMore(data) {
    moreWrap.hidden = !data.has_next;
    moreBtn.dataset.nextPage = data.next_page ?? '';
  }

  // Dibaca modul lain untuk memutuskan apakah kartu baru boleh disisipkan
  function remember(category) {
    list.dataset.category = category;
    list.dataset.query = queryInput.value.trim();
    list.dataset.sort = sortSelect.value;
  }

  function markActive(category) {
    chips.forEach((chip) => {
      const active = chip.dataset.category === category;
      chip.classList.toggle('chip--active', active);
      if (active) chip.setAttribute('aria-current', 'true');
      else chip.removeAttribute('aria-current');
    });
  }

  // Hasil yang datang terlambat (kalah cepat oleh pencarian berikutnya) dibuang
  async function reload(category) {
    const mine = ++latest;
    list.setAttribute('aria-busy', 'true');
    try {
      const data = await fetchPage(category, 1);
      if (mine !== latest) return;
      list.innerHTML = data.html;
      remember(category);
      markActive(category);
      showMore(data);
      const url = buildParams(category).toString();
      window.history.replaceState(null, '', url ? `?${url}` : window.location.pathname);
    } catch {
      if (mine === latest) toast('Gagal memuat postingan. Coba lagi.', 'danger');
    } finally {
      if (mine === latest) list.removeAttribute('aria-busy');
    }
  }

  const currentCategory = () => list.dataset.category || '';

  chips.forEach((chip) => {
    chip.addEventListener('click', (event) => {
      event.preventDefault();
      reload(chip.dataset.category);
    });
  });

  form.addEventListener('submit', (event) => {
    event.preventDefault();
    clearTimeout(timer);
    reload(currentCategory());
  });

  queryInput.addEventListener('input', () => {
    clearTimeout(timer);
    timer = setTimeout(() => reload(currentCategory()), SEARCH_DELAY);
  });

  sortSelect.addEventListener('change', () => reload(currentCategory()));

  moreBtn.addEventListener('click', async (event) => {
    event.preventDefault();
    const page = Number(moreBtn.dataset.nextPage);
    if (!page) return;
    moreBtn.setAttribute('aria-disabled', 'true');
    try {
      const data = await fetchPage(currentCategory(), page);
      list.insertAdjacentHTML('beforeend', data.html);
      showMore(data);
    } catch {
      toast('Gagal memuat postingan. Coba lagi.', 'danger');
    } finally {
      moreBtn.removeAttribute('aria-disabled');
    }
  });
}
