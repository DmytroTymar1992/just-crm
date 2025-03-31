const editForm = document.getElementById("edit-contact-form");
const editModal = document.getElementById("editContactModal");
const formErrors = document.getElementById("form-errors");
const companySelect = document.getElementById("company");

function bindEditButtons() {
    document.querySelectorAll(".edit-contact-btn").forEach(button => {
        button.addEventListener("click", function() {
            const contactId = this.dataset.contactId;
            const card = this.closest(".contact-card");

            editForm.action = `${editForm.dataset.editUrl}${contactId}/`; // Використовуємо data-атрибут
            editForm.dataset.contactId = contactId;

            if (formErrors) {
                formErrors.style.display = "none";
                formErrors.innerHTML = "";
            }

            const nameEl = card.querySelector(".contact-name");
            const nameParts = nameEl.textContent.trim().split(" ");
            editForm.querySelector("#first_name").value = nameParts[0] || "";
            editForm.querySelector("#last_name").value = nameParts.slice(1).join(" ") || "";

            const positionEl = card.querySelector(".text-muted:not(a)");
            editForm.querySelector("#position").value = positionEl ? positionEl.textContent : "";

            const phoneEl = card.querySelector("p:has(.bi-telephone-fill)");
            editForm.querySelector("#phone").value = phoneEl ? phoneEl.textContent.replace(/[^0-9+]/g, "") : "";

            const emailEl = card.querySelector("a[href^='mailto:']");
            editForm.querySelector("#email").value = emailEl ? emailEl.textContent : "";

            const telegramEl = card.querySelector("p:has(.bi-telegram)");
            if (telegramEl) {
                const telegramText = telegramEl.textContent;
                if (telegramText.includes("@")) {
                    editForm.querySelector("#telegram_username").value = telegramText.split("@")[1].trim();
                    editForm.querySelector("#telegram_id").value = "";
                } else if (telegramText.includes("ID:")) {
                    editForm.querySelector("#telegram_username").value = "";
                    editForm.querySelector("#telegram_id").value = telegramText.split("ID:")[1].trim();
                } else {
                    editForm.querySelector("#telegram_username").value = "";
                    editForm.querySelector("#telegram_id").value = "";
                }
            } else {
                editForm.querySelector("#telegram_username").value = "";
                editForm.querySelector("#telegram_id").value = "";
            }

            const companyEl = card.querySelector("p:has(.bi-building) a");
            const companyName = companyEl ? companyEl.textContent : "";
            const selectedOption = Array.from(companySelect.options).find(option => option.dataset.name === companyName);
            companyChoices.setChoiceByValue(selectedOption ? selectedOption.value : "");

            const modalInstance = new bootstrap.Modal(editModal);
            modalInstance.show();
        });
    });
}