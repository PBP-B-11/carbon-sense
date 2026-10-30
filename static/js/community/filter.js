import {getJson} from './http.js';
import {appendNew, toast} from './ui.js';

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

  function buildParams({category, query, sort}, page) {
    const params = new URLSearchParams();
    if (category) params.set('category', category);
    if (query) params.set('q', query);
    if (sort !== 'new') params.set('sort', sort);
    if (page) params.set('page', page);
    return params;
  }

  // Yang sedang diketik di form, dan yang dipakai untuk merender isi `list` saat ini
  const typed = (category) => ({category, query: queryInput.value.trim(), sort: sortSelect.value});
  const rendered = () => ({
    category: list.dataset.category || '',
    query: list.dataset.query || '',
    sort: list.dataset.sort || 'new',
  });

  async function fetchPage(filters, page) {
    const res = await getJson(`${window.location.pathname}?${buildParams(filters, page)}`);
    if (!res.ok) throw new Error('load failed');
    return res.json();
  }

  function showMore(data) {
    moreWrap.hidden = !data.has_next;
    moreBtn.dataset.nextPage = data.next_page ?? '';
  }

  // Dibaca modul lain untuk memutuskan apakah kartu baru boleh disisipkan
  function remember({category, query, sort}) {
    list.dataset.category = category;
    list.dataset.query = query;
    list.dataset.sort = sort;
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
    const filters = typed(category);
    list.setAttribute('aria-busy', 'true');
    try {
      const data = await fetchPage(filters, 1);
      if (mine !== latest) return;
      list.innerHTML = data.html;
      remember(filters);
      markActive(category);
      showMore(data);
      const url = buildParams(filters).toString();
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

  // Halaman berikutnya diminta dengan filter yang dipakai merender `list`, bukan isi form
  // saat ini, dan dibuang jika `list` keburu diganti oleh reload.
  moreBtn.addEventListener('click', async (event) => {
    event.preventDefault();
    const page = Number(moreBtn.dataset.nextPage);
    if (!page || moreBtn.hasAttribute('aria-disabled')) return;
    const mine = latest;
    moreBtn.setAttribute('aria-disabled', 'true');
    try {
      const data = await fetchPage(rendered(), page);
      if (mine !== latest) return;
      appendNew(list, data.html);
      showMore(data);
    } catch {
      if (mine === latest) toast('Gagal memuat postingan. Coba lagi.', 'danger');
    } finally {
      moreBtn.removeAttribute('aria-disabled');
    }
  });
}
