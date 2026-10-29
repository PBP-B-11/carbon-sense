// Header ini yang membuat server menjawab dengan JSON (lihat `_is_ajax` di views.py)
const AJAX_HEADERS = {'X-Requested-With': 'XMLHttpRequest'};

// Kirim isi form lewat POST tanpa pindah halaman
export function sendForm(form) {
  return fetch(form.action, {
    method: 'POST',
    body: new FormData(form),
    headers: AJAX_HEADERS,
    credentials: 'same-origin',
  });
}

// GET yang meminta jawaban JSON
export function getJson(url) {
  return fetch(url, {headers: AJAX_HEADERS, credentials: 'same-origin'});
}

// Mengembalikan {ok, data}. Mengembalikan null jika server mengarahkan ke
// halaman login; halaman ikut berpindah ke sana.
export async function parse(res) {
  if (res.redirected) {
    window.location.href = res.url;
    return null;
  }
  return {ok: res.ok, data: await res.json()};
}
