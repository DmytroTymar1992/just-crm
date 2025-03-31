const searchInput = document.getElementById("company-search");
const companiesList = document.getElementById("companies-list");

if (searchInput) {
  let debounceTimer;
  searchInput.addEventListener("input", function(e) {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      const query = e.target.value.trim();
      searchCompanies(query);
    }, 300);
  });
}

function searchCompanies(query) {
  const companiesContainer = document.getElementById("companies-container");
  companiesContainer.innerHTML = '<div class="text-center py-5"><i class="bi bi-arrow-clockwise spin" style="font-size: 2rem;"></i><p class="text-muted">Завантаження...</p></div>';

  fetch(`/sales/companies/search/?q=${encodeURIComponent(query)}`, {
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
    companiesContainer.innerHTML = html;
  })
  .catch(error => {
    console.error("Помилка:", error);
    companiesContainer.innerHTML = '<div class="col-12 text-center py-5"><p class="text-muted">Щось пішло не так</p></div>';
  });
}