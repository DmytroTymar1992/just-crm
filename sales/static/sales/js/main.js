document.addEventListener("DOMContentLoaded", function() {
  const container = document.getElementById("contacts-container");
  const companySelect = document.getElementById("company");

  if (container) {
    container.scrollTop = container.scrollHeight;
  }

  if (companySelect) {
    const companyChoices = new Choices(companySelect, {
      searchEnabled: true,
      searchPlaceholderValue: "Пошук компанії...",
      noResultsText: "Компаній не знайдено",
      itemSelectText: "",
      shouldSort: false,
    });
    window.companyChoices = companyChoices; // Зберігаємо для доступу в інших файлах
  }

  bindEditButtons(); // Ініціалізація кнопок редагування
});