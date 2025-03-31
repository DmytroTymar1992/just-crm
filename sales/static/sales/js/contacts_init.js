// static/js/contacts_init.js
document.addEventListener("DOMContentLoaded", function() {
  console.log("Initializing contact page scripts...");
  window.contactApp = window.contactApp || {}; // Ensure namespace exists

  // Initial scroll (if needed)
  const container = document.getElementById("contacts-container");
  if (container) {
    // Optional: Scroll only on initial load, not after searches etc.
    // Could add a check or remove if not desired.
    // container.scrollTop = container.scrollHeight;
    console.log("Scrolled contact container.");
  }

  // Call initializers/setup functions from other files if they haven't run yet
  // Note: The previous files were set up to run their setup on DOMContentLoaded or immediately
  // So, explicit calls might not be needed unless you restructure them to ONLY define functions.

  // Ensure Choices.js instance is available (it should be initialized by contact_choices.js)
  if (!window.contactApp.companyChoices) {
      console.warn("Choices.js instance (window.contactApp.companyChoices) not found during init.");
      // Optional: try to initialize it here as a fallback?
  }

  // Initial binding of edit buttons
  if (window.contactApp.bindEditButtons) {
    window.contactApp.bindEditButtons();
  } else {
    console.error("bindEditButtons function not found for initial binding.");
  }

  console.log("Contact page scripts initialization complete.");
});