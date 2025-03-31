document.addEventListener("DOMContentLoaded", function() {
    const container = document.getElementById("contacts-container");
    const searchInput = document.getElementById("contact-search");
    const contactsList = document.getElementById("contacts-list");
    const editModal = document.getElementById("editContactModal");
    const editForm = document.getElementById("edit-contact-form");
    const formErrors = document.getElementById("form-errors");
    const addContactBtn = document.getElementById("add-contact-btn");
    const companySelect = document.getElementById("company");

    if (container) {
        container.scrollTop = container.scrollHeight;
    }
});