const addContactBtn = document.getElementById("add-contact-btn");
const editForm = document.getElementById("edit-contact-form");
const editModal = document.getElementById("editContactModal");
const formErrors = document.getElementById("form-errors");
const companySelect = document.getElementById("company");

if (addContactBtn) {
    addContactBtn.addEventListener("click", function(e) {
        e.preventDefault();
        editForm.action = editForm.dataset.createUrl; // Використовуємо data-атрибут як у попередньому рішенні
        editForm.dataset.contactId = "0";

        editForm.querySelector("#first_name").value = "";
        editForm.querySelector("#last_name").value = "";
        editForm.querySelector("#position").value = "";
        editForm.querySelector("#phone").value = "";
        editForm.querySelector("#email").value = "";
        editForm.querySelector("#telegram_username").value = "";
        editForm.querySelector("#telegram_id").value = "";
        companyChoices.setChoiceByValue("");

        if (formErrors) {
            formErrors.style.display = "none";
            formErrors.innerHTML = "";
        }

        const modalInstance = new bootstrap.Modal(editModal);
        modalInstance.show();
    });
}