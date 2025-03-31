// static/js/contact_choices.js
if (typeof Choices !== 'undefined') {
  const companySelect = document.getElementById("company");
  if (companySelect) {
    window.contactApp = window.contactApp || {}; // Ensure namespace exists
    window.contactApp.companyChoices = new Choices(companySelect, {
      searchEnabled: true,
      searchPlaceholderValue: "Пошук компанії...",
      noResultsText: "Компаній не знайдено",
      itemSelectText: "",
      shouldSort: false,
    });
    console.log("Choices.js initialized for company select.");
  } else {
    console.warn("Company select element (#company) not found for Choices.js initialization.");
  }
} else {
  console.error("Choices.js library not loaded.");
}