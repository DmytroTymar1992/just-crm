// static/js/contact_search.js
window.contactApp = window.contactApp || {}; // Ensure namespace exists

window.contactApp.searchContacts = function(query) {
  const contactsList = document.getElementById("contacts-list");
  const searchUrl = document.getElementById('contact-search-form')?.dataset.searchUrl || '/sales/contacts/search/'; // Get URL from data attribute or fallback

  if (!contactsList) {
    console.error("Contacts list element (#contacts-list) not found.");
    return;
  }

  contactsList.innerHTML = '<div class="text-center py-5"><i class="bi bi-arrow-clockwise spin" style="font-size: 2rem;"></i><p class="text-muted">Завантаження...</p></div>';

  // Ensure the search URL ends with a slash if it doesn't have one
  const url = searchUrl.endsWith('/') ? searchUrl : searchUrl + '/';

  fetch(`<span class="math-inline">\{url\}?q\=</span>{encodeURIComponent(query)}`, {
    method: "GET",
    headers: {
      "X-Requested-With": "XMLHttpRequest"
    }
  })
  .then(response => {
    if (!response.ok) throw new Error(`HTTP error! Status: ${response.status}`);
    return response.text();
  })
  .then(html => {
    contactsList.innerHTML = html;
    // Re-bind edit buttons after updating the list
    if (window.contactApp.bindEditButtons) {
      window.contactApp.bindEditButtons();
    } else {
      console.warn("bindEditButtons function not found after search.");
    }
  })
  .catch(error => {
    console.error("Search Error:", error);
    contactsList.innerHTML = '<div class="col-12 text-center py-5"><p class="text-danger">Помилка завантаження контактів.</p></div>';
  });
};

function setupContactSearch() {
    const searchInput = document.getElementById("contact-search");
    if (searchInput) {
        let debounceTimer;
        searchInput.addEventListener("input", function(e) {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => {
                const query = e.target.value.trim();
                window.contactApp.searchContacts(query);
            }, 300); // 300ms debounce
        });
        console.log("Contact search input listener attached.");
    } else {
        console.warn("Contact search input (#contact-search) not found.");
    }
}

// Run setup when the script loads (assuming DOM is ready or will be handled by main init)
// Or defer execution until DOMContentLoaded in the main init script
// For simplicity here, let's assume it might be loaded after DOM ready
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", setupContactSearch);
} else {
  setupContactSearch(); // DOM is already ready
}