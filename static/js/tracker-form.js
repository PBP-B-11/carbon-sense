(() => {
  function initializeForm() {
    const form = document.getElementById("catat-cepat");
    if (!form || form.dataset.fieldsReady) return;
    form.dataset.fieldsReady = "true";

    const quantity = form.querySelector('[name="quantity"]');
    const label = form.querySelector("#quantity-label");
    const unit = form.querySelector("#quantity-unit");
    const factorNote = form.querySelector("#activity-factor-note");
    const meatPortions = form.querySelector("#meat-portions");

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

    form.addEventListener("change", (event) => {
      if (event.target.name === "activity_type") updateQuantityField();
    });
    updateQuantityField();
  }

  //Pasang kembali pilihan satuan setelah formulir diganti melalui AJAX.
  document.addEventListener("tracker:form-ready", initializeForm);
  initializeForm();
})();
