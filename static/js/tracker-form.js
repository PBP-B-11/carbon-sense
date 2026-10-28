(() => {
  const updateHandlers = new WeakMap();

  function initializeForm(form) {
    if (!form) return;
    //Formulir yang dipertahankan AJAX tetap perlu diselaraskan dengan pilihan terbaru.
    if (updateHandlers.has(form)) {
      updateHandlers.get(form)();
      return;
    }

    const quantity = form.querySelector('[name="quantity"]');
    const label = form.querySelector("[data-quantity-label]");
    const unit = form.querySelector("[data-quantity-unit]");
    const factorNote = form.querySelector("[data-factor-note]");
    const meatPortions = form.querySelector("[data-meat-portions]");
    if (!quantity || !label || !unit) return;

    //Siapkan satuan dan sumber faktor untuk setiap aktivitas.
    const activityFields = {
      car_travel: {
        label: "Jarak tempuh", unit: "km", placeholder: "12,5",
        note: "Mobil: perkiraan emisi penggunaan kendaraan berdasarkan data Amerika Serikat (US EPA 2025).",
      },
      electricity: {
        label: "Pemakaian listrik", unit: "kWh", placeholder: "5",
        note: "Listrik: faktor bauran produksi listrik Indonesia (Ember 2024).",
      },
      //Gunakan perkiraan berat mentah daging saja, bukan seluruh hidangan.
      chicken: {
        label: "Berat ayam mentah", unit: "g", placeholder: "150",
        note: "Ayam: masukkan perkiraan berat mentah daging saja dalam gram. Faktor total CONCITO/2-0 LCA, Prancis 2024, digunakan sebagai perkiraan; bukan faktor khusus Indonesia.",
      },
      beef: {
        label: "Berat daging sapi mentah", unit: "g", placeholder: "150",
        note: "Daging sapi: masukkan perkiraan berat mentah daging saja dalam gram. Faktor total CONCITO/2-0 LCA, Prancis 2024, digunakan sebagai perkiraan; bukan faktor khusus Indonesia.",
      },
    };

    //Perbarui satuan dan sumber faktor ketika pilihan aktivitas berubah.
    function updateQuantityField() {
      const selected = form.querySelector('[name="activity_type"]:checked');
      const fields = activityFields[selected?.value];
      if (!fields) return;

      label.textContent = fields.label;
      unit.textContent = fields.unit;
      quantity.placeholder = fields.placeholder;
      if (factorNote) factorNote.textContent = fields.note;
      if (meatPortions) {
        meatPortions.hidden = !["chicken", "beef"].includes(selected.value);
      }
    }

    //Tombol perkiraan mengisi gram tanpa mengirim formulir; pengguna dapat mengubahnya.
    form.querySelectorAll("[data-meat-grams]").forEach((button) => {
      button.addEventListener("click", () => {
        const selected = form.querySelector('[name="activity_type"]:checked');
        if (!["chicken", "beef"].includes(selected?.value)) return;
        quantity.value = button.dataset.meatGrams;
        quantity.focus();
      });
    });

    //Batasi pemilih tanggal sampai hari ini (waktu lokal); server tetap memvalidasi.
    const dateInput = form.querySelector('[name="date"]');
    if (dateInput) {
      const now = new Date();
      now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
      dateInput.max = now.toISOString().slice(0, 10);
    }

    const handleSelection = (event) => {
      if (event.target.name === "activity_type") updateQuantityField();
    };
    form.addEventListener("input", handleSelection);
    form.addEventListener("change", handleSelection);
    form.addEventListener("reset", () => window.requestAnimationFrame(updateQuantityField));
    updateHandlers.set(form, updateQuantityField);
    form.dataset.fieldsReady = "true";
    updateQuantityField();
  }

  //Inisialisasi formulir halaman dan modal secara terpisah tanpa menggandakan listener.
  function initializeForms() {
    document.querySelectorAll("[data-tracker-form]").forEach(initializeForm);
  }
  document.addEventListener("tracker:form-ready", initializeForms);
  //Browser dapat memulihkan radio tanpa change ketika halaman dibuka kembali.
  window.addEventListener("pageshow", () => {
    initializeForms();
    window.requestAnimationFrame(initializeForms);
  });
  initializeForms();
})();
