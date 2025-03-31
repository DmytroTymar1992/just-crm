const searchInput = document.getElementById("contact-search");
const contactsList = document.getElementById("contacts-list");

if (searchInput) {
    let debounceTimer;
    searchInput.addEventListener("input", function(e) {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => {
            const query = e.target.value.trim();
            searchContacts(query);
        }, 300);
    });
}

function searchContacts(query) {
    contactsList.innerHTML = '<div class="text-center py-5"><i class="bi bi-arrow-clockwise spin" style="font-size: 2rem;"></i><p class="text-muted">Завантаження...</p></div>';
    fetch(`/sales/contacts/search/?q=${encodeURIComponent(query)}`, {
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
        bindEditButtons();
    })
    .catch(error => {
        console.error("Помилка:", error);
        contactsList.innerHTML = '<div class="col-12 text-center py-5"><p class="text-muted">Щось пішло не так</p></div>';
    });
}