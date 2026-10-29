document.querySelectorAll('[data-city-picker]').forEach((picker) => {
  const queryInput = picker.querySelector('[data-city-query]');
  const cityValue = picker.querySelector('[data-city-value]');
  const suggestions = picker.querySelector('[data-city-suggestions]');
  const status = picker.querySelector('[data-city-status]');
  const saveForm = picker.querySelector('[data-city-save-form]');
  const saveButton = saveForm?.querySelector('button[type="submit"]');
  const saveStatus = picker.querySelector('[data-city-save-status]');
  let timer;
  let controller;

  const hideSuggestions = () => {
    suggestions.hidden = true;
    suggestions.replaceChildren();
    queryInput.setAttribute('aria-expanded', 'false');
  };

  const showSuggestions = (results) => {
    suggestions.replaceChildren(...results.map(({label, token}) => {
      const option = document.createElement('button');
      option.type = 'button';
      option.className = 'city-suggestion';
      option.textContent = label;
      option.addEventListener('click', () => {
        cityValue.value = token;
        queryInput.value = label;
        hideSuggestions();
        status.textContent = saveButton ? 'Kota dipilih. Klik "Simpan kota" untuk menerapkan.' : 'Kota dipilih.';
        if (saveButton) saveButton.disabled = false;
        if (saveStatus) {
          saveStatus.textContent = '';
          saveStatus.hidden = true;
        }
        queryInput.focus();
      });
      return option;
    }));
    suggestions.hidden = results.length === 0;
    queryInput.setAttribute('aria-expanded', String(results.length > 0));
  };

  queryInput.addEventListener('input', () => {
    if (saveStatus) {
      saveStatus.textContent = '';
      saveStatus.hidden = true;
    }
    clearTimeout(timer);
    controller?.abort();
    cityValue.value = '';
    if (saveButton) saveButton.disabled = true;
    hideSuggestions();
    const query = queryInput.value.trim();

    if (query.length < 2) {
      status.textContent = 'Ketik minimal 2 karakter untuk mencari.';
      return;
    }

    status.textContent = 'Mencari kota...';
    timer = setTimeout(async () => {
      controller = new AbortController();
      const url = new URL(picker.dataset.cityUrl, window.location.origin);
      url.searchParams.set('q', query);

      try {
        const response = await fetch(url, {signal: controller.signal});
        if (!response.ok) throw new Error('City search failed');
        const {results} = await response.json();
        if (query !== queryInput.value.trim()) return;

        showSuggestions(results);
        status.textContent = results.length ? 'Pilih kota dari saran.' : 'Tidak ada kota yang ditemukan.';
      } catch (error) {
        if (error.name !== 'AbortError' && query === queryInput.value.trim()) {
          hideSuggestions();
          status.textContent = 'Pencarian kota gagal. Coba lagi.';
        }
      }
    }, 300);
  });

  queryInput.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') hideSuggestions();
    if (event.key === 'ArrowDown' && !suggestions.hidden) {
      event.preventDefault();
      suggestions.querySelector('button')?.focus();
    }
  });

  if (saveForm) {
    saveButton.disabled = !cityValue.value;
    saveForm.addEventListener('submit', async (event) => {
      event.preventDefault();
      const formData = new FormData(saveForm);
      let failure = 'Gagal menyimpan kota. Coba lagi.';
      saveButton.disabled = true;
      queryInput.disabled = true;
      cityValue.disabled = true;
      saveStatus.hidden = false;
      saveStatus.textContent = 'Menyimpan kota...';

      try {
        const response = await fetch(saveForm.action, {
          method: 'POST',
          body: formData,
          headers: {Accept: 'application/json'},
        });
        if (response.redirected) {
          failure = 'Sesi berakhir. Muat ulang halaman untuk masuk kembali.';
          throw new Error();
        }
        const result = await response.json();
        if (!response.ok) {
          failure = result.error || failure;
          throw new Error();
        }

        document.querySelectorAll('[data-profile-city]').forEach((element) => {
          element.textContent = result.city;
        });
        document.querySelector('[data-profile-air]').outerHTML = result.air_html;
        saveStatus.textContent = 'Kota berhasil disimpan.';
      } catch {
        saveStatus.textContent = failure;
      } finally {
        saveButton.disabled = !cityValue.value;
        queryInput.disabled = false;
        cityValue.disabled = false;
      }
    });
  }

  if (cityValue.value) status.textContent = 'Kota dipilih.';
  else if (queryInput.value.trim().length >= 2) queryInput.dispatchEvent(new Event('input'));
});
