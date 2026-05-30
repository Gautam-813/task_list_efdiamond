document.querySelectorAll("form[data-confirm]").forEach((form) => {
  form.addEventListener("submit", (event) => {
    const message = form.getAttribute("data-confirm") || "Are you sure?";
    if (!window.confirm(message)) {
      event.preventDefault();
    }
  });
});

document.querySelectorAll(".filter-bar input[type='radio']").forEach((input) => {
  input.addEventListener("change", () => {
    input.closest("form").submit();
  });
});
