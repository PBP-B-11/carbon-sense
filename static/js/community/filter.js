import {getJson} from './http.js';
import {toast} from './ui.js';

export function initFilter() {
  const list = document.getElementById('post-list');
  const moreWrap = document.getElementById('load-more-wrap');
  const moreBtn = moreWrap.querySelector('.js-load-more');
  const chips = document.querySelectorAll('.js-filter');

  async function load(category, page, replace) {
    const params = new URLSearchParams({page});
    if (category) params.set('category', category);
    const res = await getJson(`${window.location.pathname}?${params}`);
    if (!res.ok) throw new Error('load failed');
    const data = await res.json();

    if (replace) list.innerHTML = data.html;
    else list.insertAdjacentHTML('beforeend', data.html);
    list.dataset.category = category;
    moreWrap.hidden = !data.has_next;
    moreBtn.dataset.nextPage = data.next_page ?? '';
  }

  chips.forEach((chip) => {
    chip.addEventListener('click', async (event) => {
      event.preventDefault();
      const category = chip.dataset.category;
      list.setAttribute('aria-busy', 'true');
      try {
        await load(category, 1, true);
        chips.forEach((c) => {
          const active = c === chip;
          c.classList.toggle('chip--active', active);
          if (active) c.setAttribute('aria-current', 'true');
          else c.removeAttribute('aria-current');
        });
        window.history.replaceState(null, '', category ? `?category=${category}` : window.location.pathname);
      } catch {
        toast('Gagal memuat postingan. Coba lagi.', 'danger');
      } finally {
        list.removeAttribute('aria-busy');
      }
    });
  });

  moreBtn.addEventListener('click', async (event) => {
    event.preventDefault();
    moreBtn.setAttribute('aria-disabled', 'true');
    try {
      await load(list.dataset.category || '', Number(moreBtn.dataset.nextPage), false);
    } catch {
      toast('Gagal memuat postingan. Coba lagi.', 'danger');
    } finally {
      moreBtn.removeAttribute('aria-disabled');
    }
  });
}
