const AJAX_HEADERS = {'X-Requested-With': 'XMLHttpRequest'};

export function sendForm(form) {
  return fetch(form.action, {
    method: 'POST',
    body: new FormData(form),
    headers: AJAX_HEADERS,
    credentials: 'same-origin',
  });
}

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
