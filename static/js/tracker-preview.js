(() => {
  const refreshDashboard = window.CarbonTracker.refreshDashboard;

  function initializeRequests(form) {
    if (!form || !window.fetch || form.dataset.requestsReady) return;
    form.dataset.requestsReady = "true";

    const result = form.querySelector("[data-preview-result]");
    const value = form.querySelector("[data-preview-value]");
    const status = form.querySelector("[data-preview-status]");
    const errorSlots = [...form.querySelectorAll("[data-form-errors]")];
    let pending = false;

    //Tampilkan pesan sebagai teks agar isi respons tidak dijalankan sebagai HTML.
    function showErrors(errors) {
      for (const [field, messages] of Object.entries(errors)) {
        const slot = errorSlots.find((item) => item.dataset.formErrors === field)
          || errorSlots.find((item) => item.dataset.formErrors === "__all__");
        slot.id = `${form.id}-errors-${slot.dataset.formErrors}`;
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

    async function submitActivity(button) {
      const action = button.value;
      const saving = action === "save";
      //FormData membawa token CSRF; nilai tombol submit perlu ditambahkan sendiri.
      const body = new FormData(form);
      body.set("action", action);
      const controls = [...form.querySelectorAll("input, select, textarea, button")];
      const disabledStates = controls.map((control) => control.disabled);
      const buttonText = button.textContent;
      const controller = new AbortController();
      //Batas waktu hanya untuk pratinjau; penyimpanan tidak dibatalkan di tengah jalan.
      const timeout = saving ? null : window.setTimeout(() => controller.abort(), 20000);
      let saveConfirmed = false;
      const modalClose = form.closest("[data-edit-modal]")?.querySelector("[data-edit-close]");

      //Cegah pengiriman ganda dan perubahan data selama perhitungan berlangsung.
      pending = true;
      if (saving) {
        form.dataset.saving = "true";
        if (modalClose) modalClose.disabled = true;
      }
      controls.forEach((control) => { control.disabled = true; });
      form.setAttribute("aria-busy", "true");
      button.textContent = saving ? "Menyimpan…" : "Menghitung…";
      clearPreview();
      errorSlots.forEach((slot) => slot.replaceChildren());
      controls.forEach((control) => { control.removeAttribute("aria-invalid"); });
      status.textContent = saving ? "Sedang menyimpan aktivitas…" : "Sedang menghitung estimasi emisi…";
      status.hidden = false;

      try {
        //Tombol bernama action dapat menutupi properti form.action di browser.
        const response = await fetch(form.getAttribute("action") || window.location.href, {
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

        if (saving) {
          if (data.activity_id == null) throw new Error("Save confirmation missing");
          saveConfirmed = true;
          form.dataset.saveConfirmed = "true";
          await refreshDashboard(form.dataset.dashboardUrl, data.message);
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
        if (saveConfirmed) {
          showErrors({ __all__: [{ message: "Aktivitas sudah tersimpan, tetapi tampilan belum diperbarui. Perbarui tampilan tanpa menyimpan ulang." }] });
          //Ulangi GET saja jika pembaruan tampilan gagal setelah penyimpanan berhasil.
          const retry = document.createElement("button");
          retry.type = "button";
          retry.className = "btn";
          retry.textContent = "Perbarui tampilan";
          retry.addEventListener("click", async () => {
            retry.disabled = true;
            try {
              await refreshDashboard(form.dataset.dashboardUrl, "Aktivitas berhasil disimpan.");
            } catch {
              retry.disabled = false;
            }
          });
          errorSlots.find((slot) => slot.dataset.formErrors === "__all__").append(retry);
        } else {
          showErrors({
            __all__: [{ message: saving
              ? "Hasil penyimpanan belum dapat dipastikan. Periksa riwayat atau muat ulang halaman sebelum mencoba menyimpan lagi."
              : "Gagal menghitung emisi. Coba lagi atau muat ulang halaman jika masalah berlanjut." }],
          });
        }
      } finally {
        //Pulihkan formulir setelah berhasil, gagal, atau melewati batas waktu.
        window.clearTimeout(timeout);
        controls.forEach((control, index) => { control.disabled = disabledStates[index]; });
        //Jangan izinkan penyimpanan ganda jika hanya pembaruan tampilan yang gagal.
        if (saveConfirmed) button.disabled = true;
        button.textContent = buttonText;
        form.removeAttribute("aria-busy");
        status.hidden = true;
        pending = false;
        delete form.dataset.saving;
        if (modalClose) modalClose.disabled = false;
      }
    }

    //Gunakan AJAX untuk Hitung dan Simpan, termasuk saat mengedit aktivitas.
    form.addEventListener("submit", (event) => {
      if (pending) {
        event.preventDefault();
        return;
      }
      if (!["estimate", "save"].includes(event.submitter?.value)) return;
      event.preventDefault();
      if (event.submitter.value === "save" && form.dataset.saveConfirmed) return;
      submitActivity(event.submitter);
    });
  }

  //Inisialisasi ulang hanya formulir baru agar listener tidak terpasang berulang.
  function initializeForms() {
    document.querySelectorAll("[data-tracker-form]").forEach(initializeRequests);
  }
  document.addEventListener("tracker:form-ready", initializeForms);
  initializeForms();
})();
