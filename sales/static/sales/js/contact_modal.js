// static/js/contact_modal.js
window.contactApp = window.contactApp || {}; // Ensure namespace exists

function setupContactModal() {
    const editModalElement = document.getElementById("editContactModal");
    const editForm = document.getElementById("edit-contact-form");
    const formErrors = document.getElementById("form-errors");
    const addContactBtn = document.getElementById("add-contact-btn");
    const companySelect = document.getElementById("company"); // Needed for companyChoices

    if (!editModalElement || !editForm || !addContactBtn) {
        console.warn("One or more required elements for contact modal not found (editContactModal, edit-contact-form, add-contact-btn).");
        return;
    }

    const editModal = new bootstrap.Modal(editModalElement);

    // Function to bind edit buttons - make it part of the app namespace
    window.contactApp.bindEditButtons = function() {
        document.querySelectorAll(".edit-contact-btn").forEach(button => {
            // Remove existing listener to prevent duplicates if called multiple times
            button.replaceWith(button.cloneNode(true));
        });
        // Add new listeners
        document.querySelectorAll(".edit-contact-btn").forEach(button => {
            button.addEventListener("click", function() {
                const contactId = this.dataset.contactId;
                const card = this.closest(".contact-card");
                const editUrl = this.dataset.editUrlTemplate.replace('0', contactId); // Get URL from data attribute

                editForm.action = editUrl;
                editForm.dataset.contactId = contactId; // Store ID for submission logic

                if (formErrors) {
                    formErrors.style.display = "none";
                    formErrors.innerHTML = "";
                }

                // Populate form fields from the card data
                const nameEl = card.querySelector(".contact-name");
                const nameParts = nameEl ? nameEl.textContent.trim().split(" ") : ["", ""];
                editForm.querySelector("#id_first_name").value = nameParts[0] || ""; // Use Django form IDs
                editForm.querySelector("#id_last_name").value = nameParts.slice(1).join(" ") || "";

                const positionEl = card.querySelector(".contact-position"); // Use a specific class
                editForm.querySelector("#id_position").value = positionEl ? positionEl.textContent.trim() : "";

                const phoneEl = card.querySelector(".contact-phone"); // Use a specific class
                editForm.querySelector("#id_phone").value = phoneEl ? phoneEl.textContent.replace(/[^0-9+]/g, "") : "";

                const emailEl = card.querySelector("a.contact-email"); // Use a specific class
                editForm.querySelector("#id_email").value = emailEl ? emailEl.textContent.trim() : "";

                // Handle Telegram - look for specific data attributes if possible, fallback to parsing
                const telegramUserEl = card.querySelector(".contact-telegram-username");
                const telegramIdEl = card.querySelector(".contact-telegram-id");
                editForm.querySelector("#id_telegram_username").value = telegramUserEl ? telegramUserEl.dataset.username || "" : "";
                editForm.querySelector("#id_telegram_id").value = telegramIdEl ? telegramIdEl.dataset.id || "" : "";

                // Handle Company
                const companyEl = card.querySelector(".contact-company a"); // Use a specific class
                const companyId = companyEl ? companyEl.dataset.companyId : ""; // Get company ID from data attribute
                if (window.contactApp.companyChoices) {
                     window.contactApp.companyChoices.setChoiceByValue(companyId || "");
                } else {
                     // Fallback if Choices isn't ready or available
                     const companySelectElement = document.getElementById('id_company');
                     if(companySelectElement) companySelectElement.value = companyId || "";
                }


                editModal.show();
            });
        });
        console.log("Edit contact button listeners bound/re-bound.");
    };

    // "Add Contact" button listener
    addContactBtn.addEventListener("click", function(e) {
        e.preventDefault();
        const createUrl = this.dataset.createUrl; // Get URL from data attribute

        editForm.action = createUrl;
        editForm.reset(); // Reset the form fields
        editForm.dataset.contactId = "0"; // Indicate new contact

        if (window.contactApp.companyChoices) {
            window.contactApp.companyChoices.setChoiceByValue(""); // Clear Choices selection
        } else {
             const companySelectElement = document.getElementById('id_company');
             if(companySelectElement) companySelectElement.value = "";
        }


        if (formErrors) {
            formErrors.style.display = "none";
            formErrors.innerHTML = "";
        }

        editModal.show();
    });

    // Form submission listener
    editForm.addEventListener("submit", function(e) {
        e.preventDefault();
        const submitButton = editForm.querySelector('button[type="submit"]');
        const originalButtonText = submitButton.innerHTML;
        submitButton.disabled = true;
        submitButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Збереження...';


        // Ensure CSRF token is included (should be in the form via {% csrf_token %})
        const formData = new FormData(this);
        const csrfToken = this.querySelector('input[name="csrfmiddlewaretoken"]').value;

        fetch(this.action, {
            method: "POST",
            body: formData,
            headers: {
                "X-CSRFToken": csrfToken,
                "X-Requested-With": "XMLHttpRequest" // Important for Django request.is_ajax()
            }
        })
        .then(response => {
            if (response.headers.get("Content-Type")?.includes("application/json")) {
                return response.json().then(data => ({ ok: response.ok, status: response.status, data }));
            }
             // Handle non-JSON responses (e.g., full page refresh on error)
             if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}. Expected JSON response.`);
             }
             // If OK but not JSON, maybe it's a redirect or unexpected success response
             return { ok: true, status: response.status, data: { success: true } }; // Assume success if OK and not JSON
        })
         .then(({ ok, status, data }) => {
            if (ok && data.success) {
                editModal.hide();
                // Refresh the contact list using the search function
                const currentSearch = document.getElementById("contact-search")?.value || "";
                if (window.contactApp.searchContacts) {
                    window.contactApp.searchContacts(currentSearch);
                } else {
                    console.warn("searchContacts function not found after form submission.");
                    // Fallback: reload the page? Or show a success message.
                     window.location.reload(); // Simple fallback
                }
            } else if (!ok && data && data.error) {
                // Handle validation errors returned as JSON
                if (window.contactApp.showFormErrors) {
                   window.contactApp.showFormErrors(data.error, formErrors);
                } else {
                   alert("Помилка валідації: " + JSON.stringify(data.error));
                }
            } else {
                // Generic error
                throw new Error(data?.message || `Помилка збереження. Status: ${status}`);
            }
        })
        .catch(error => {
             console.error("Form Submission Error:", error);
             // Display error using the utility function if possible
             if (window.contactApp.showFormErrors && formErrors) {
                 window.contactApp.showFormErrors(error.message || "Сталася невідома помилка при збереженні.", formErrors);
             } else {
                 alert("Сталася помилка при збереженні: " + error.message);
             }
        })
        .finally(() => {
            // Re-enable the button and restore its text
            submitButton.disabled = false;
            submitButton.innerHTML = originalButtonText;
        });
    });

    console.log("Contact modal listeners (Add, Submit) attached.");
}

 // Run setup when the script loads
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", setupContactModal);
} else {
  setupContactModal(); // DOM is already ready
}