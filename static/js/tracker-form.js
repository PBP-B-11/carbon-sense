(() => {
  const form = document.getElementById("catat-cepat");
  if (!form) return;

  const quantity = form.querySelector('[name="quantity"]');
  const label = form.querySelector("#quantity-label");
  const unit = form.querySelector("#quantity-unit");
  const factorNote = form.querySelector("#activity-factor-note");

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
    //LPG dicatat sebagai gas yang terpakai, bukan berat tabung.
    lpg: {
      label: "Gas LPG yang dikonsumsi", unit: "kg", placeholder: "0,1",
      note: "Gas LPG: catat kg gas yang dikonsumsi, bukan berat tabung. Faktor pembakaran UK Government 2025 (Inggris), tanpa emisi produksi/distribusi.",
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
  }

  form.addEventListener("change", (event) => {
    if (event.target.name === "activity_type") updateQuantityField();
  });
  updateQuantityField();
})();
