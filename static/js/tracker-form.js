(() => {
  const form = document.getElementById("catat-cepat");
  if (!form) return;

  const quantity = form.querySelector('[name="quantity"]');
  const label = form.querySelector("#quantity-label");
  const unit = form.querySelector("#quantity-unit");
  const activityFields = {
    car_travel: { label: "Jarak tempuh", unit: "km", placeholder: "12,5" },
    electricity: { label: "Pemakaian listrik", unit: "kWh", placeholder: "5" },
    meal: { label: "Jumlah porsi", unit: "porsi", placeholder: "1" },
  };

  function updateQuantityField() {
    const selected = form.querySelector('[name="activity_type"]:checked');
    const fields = activityFields[selected?.value];
    if (!fields) return;

    label.textContent = fields.label;
    unit.textContent = fields.unit;
    quantity.placeholder = fields.placeholder;
  }

  form.addEventListener("change", (event) => {
    if (event.target.name === "activity_type") updateQuantityField();
  });
  updateQuantityField();
})();
