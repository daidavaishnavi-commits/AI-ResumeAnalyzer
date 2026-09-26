// Drag and drop plus a client-side size/type check. The server validates again:
// this is only to give quick feedback.
(function () {
  const MAX_BYTES = 5 * 1024 * 1024;
  const form = document.getElementById("upload-form");
  const input = document.getElementById("resume");
  const dropzone = document.getElementById("dropzone");
  const fileName = document.getElementById("file-name");
  const submitBtn = document.getElementById("submit-btn");

  if (!form || !input || !dropzone) return;

  function showFile(file) {
    if (!file) return;
    const sizeMb = (file.size / (1024 * 1024)).toFixed(2);
    fileName.textContent = `${file.name} (${sizeMb} MB)`;
  }

  ["dragenter", "dragover"].forEach((type) =>
    dropzone.addEventListener(type, (event) => {
      event.preventDefault();
      dropzone.classList.add("is-dragover");
    })
  );

  ["dragleave", "drop"].forEach((type) =>
    dropzone.addEventListener(type, (event) => {
      event.preventDefault();
      dropzone.classList.remove("is-dragover");
    })
  );

  dropzone.addEventListener("drop", (event) => {
    const file = event.dataTransfer.files[0];
    if (!file) return;
    input.files = event.dataTransfer.files;
    showFile(file);
  });

  input.addEventListener("change", () => showFile(input.files[0]));

  form.addEventListener("submit", (event) => {
    const file = input.files[0];
    if (!file) return;

    if (!file.name.toLowerCase().endsWith(".pdf")) {
      event.preventDefault();
      alert("Please choose a PDF file.");
      return;
    }
    if (file.size > MAX_BYTES) {
      event.preventDefault();
      alert("That file is larger than 5 MB.");
      return;
    }

    submitBtn.disabled = true;
    submitBtn.textContent = "Extracting...";
  });
})();
