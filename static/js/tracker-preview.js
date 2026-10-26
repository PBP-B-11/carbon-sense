(() => {
  const form = document.getElementById("catat-cepat");
  if (!form || !window.fetch) return;

  const result = form.querySelector("#preview-result");
  const value = form.querySelector("#preview-value");
  const status = form.querySelector("#preview-status");
  const errorSlots = [...form.querySelectorAll("[data-form-errors]")];
  let pending = false;

  //Tampilkan pesan sebagai teks agar isi respons tidak dijalankan sebagai HTML.
  function showErrors(errors) {
    for (const [field, messages] of Object.entries(errors)) {
      const slot = errorSlots.find((item) => item.dataset.formErrors === field)
        || errorSlots.find((item) => item.dataset.formErrors === "__all__");
      slot.id = `tracker-errors-${slot.dataset.formErrors}`;
      const list = document.createElement("ul");
      list.className = "errorlist";
      for (const error of messages) {
        const item = document.createElement("li");
        item.textContent = error.message;
        list.append(item);
      }
      slot.append(list);
      form.querySelectorAll("[name]").forEach((control) => {
        if (control.name !== field) return;
        control.setAttribute("aria-invalid", "true");
        const describedBy = new Set((control.getAttribute("aria-describedby") || "").split(/\s+/).filter(Boolean));
        describedBy.add(slot.id);
        control.setAttribute("aria-describedby", [...describedBy].join(" "));
      });
      //Buka catatan opsional jika kesalahannya berada di dalam elemen details.
      const details = slot.closest("details");
      if (details) details.open = true;
    }
  }

  //Hapus hasil lama setelah pengguna mengganti data atau memilih perkiraan gram.
  function clearPreview() {
    result.hidden = true;
    value.textContent = "";
  }
  form.addEventListener("input", clearPreview);
  form.addEventListener("change", clearPreview);
  form.addEventListener("click", (event) => {
    if (event.target.closest("[data-meat-grams]")) clearPreview();
  });

  async function previewEmissions(button) {
    //FormData membawa token CSRF; nilai tombol submit perlu ditambahkan sendiri.
    const body = new FormData(form);
    body.set("action", "estimate");
    const controls = [...form.querySelectorAll("input, select, textarea, button")];
    const disabledStates = controls.map((control) => control.disabled);
    const buttonText = button.textContent;
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 20000);

    //Cegah pengiriman ganda dan perubahan data selama perhitungan berlangsung.
    pending = true;
    controls.forEach((control) => { control.disabled = true; });
    form.setAttribute("aria-busy", "true");
    button.textContent = "Menghitung…";
    clearPreview();
    errorSlots.forEach((slot) => slot.replaceChildren());
    controls.forEach((control) => { control.removeAttribute("aria-invalid"); });
    status.textContent = "Sedang menghitung estimasi emisi…";
    status.hidden = false;

    try {
      const response = await fetch(form.action, {
        method: "POST",
        body,
        credentials: "same-origin",
        headers: { "X-Requested-With": "XMLHttpRequest", Accept: "application/json" },
        signal: controller.signal,
      });
      if (!response.headers.get("content-type")?.includes("application/json")) {
        throw new Error("Unexpected response");
      }
      const data = await response.json();
      if (!response.ok) {
        if (!data.errors || !Object.keys(data.errors).length) {
          throw new Error("Missing errors");
        }
        showErrors(data.errors);
        return;
      }

      //Gunakan empat angka desimal seperti pratinjau yang dirender Django.
      const emissions = Number(data.estimate?.co2e);
      if (data.estimate?.co2e == null || !Number.isFinite(emissions)) {
        throw new Error("Missing estimate");
      }
      value.textContent = `${emissions.toLocaleString("id-ID", {
        minimumFractionDigits: 4, maximumFractionDigits: 4,
      })} kg CO₂e`;
      result.hidden = false;
    } catch (error) {
      showErrors({
        __all__: [{ message: "Gagal menghitung emisi. Coba lagi atau muat ulang halaman jika masalah berlanjut." }],
      });
    } finally {
      //Pulihkan formulir setelah berhasil, gagal, atau melewati batas waktu.
      window.clearTimeout(timeout);
      controls.forEach((control, index) => { control.disabled = disabledStates[index]; });
      button.textContent = buttonText;
      form.removeAttribute("aria-busy");
      status.hidden = true;
      pending = false;
    }
  }

  //Tangani Hitung dengan AJAX; tombol Simpan tetap mengikuti alur yang sudah ada.
  form.addEventListener("submit", (event) => {
    if (pending) {
      event.preventDefault();
      return;
    }
    if (event.submitter?.value !== "estimate") return;
    event.preventDefault();
    previewEmissions(event.submitter);
  });
})();
