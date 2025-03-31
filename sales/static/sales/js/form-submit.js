const editForm = document.getElementById("edit-contact-form");
const editModal = document.getElementById("editContactModal");
const formErrors = document.getElementById("form-errors");
const searchInput = document.getElementById("contact-search");

editForm.addEventListener("submit", function(e) {
    e.preventDefault();
    const contactId = this.dataset.contactId;

    fetch(this.action, {
        method: "POST",
        body: new FormData(this),
        headers: {
            "X-CSRFToken": document.querySelector('input[name="csrfmiddlewaretoken"]').value
        }
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(data => { throw data; });
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            searchContacts(searchInput.value);
            bootstrap.Modal.getInstance(editModal).hide();
        } else {
            showFormErrors(data.error);
        }
    })
    .catch(errData => {
        if (errData && errData.error) {
            showFormErrors(errData.error);
        } else {
            console.error("Помилка:", errData);
            alert("Сталася помилка при збереженні");
        }
    });
});

function showFormErrors(error) {
    formErrors.style.display = "block";
    let errorMessages = "<strong>Помилки:</strong><br>";
    try {
        const parsed = typeof error === "string" ? JSON.parse(error) : error;
        for (const [field, errors] of Object.entries(parsed)) {
            errors.forEach(err => {
                errorMessages += `<i class="bi bi-exclamation-circle-fill text-danger me-1"></i> ${field}: ${err}<br>`;
            });
        }
    } catch (e) {
        errorMessages += `<i class="bi bi-exclamation-circle-fill text-danger me-1"></i> ${error}<br>`;
    }
    formErrors.innerHTML = errorMessages;
}