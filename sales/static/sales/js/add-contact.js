if (addContactBtn) {
    addContactBtn.addEventListener("click", function(e) {
        e.preventDefault();
        editForm.action = "{% url 'create_contact' %}";
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