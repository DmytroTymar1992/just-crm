const editModal = document.getElementById("editContactModal");
const editForm = document.getElementById("edit-contact-form");
const formErrors = document.getElementById("form-errors");
const addContactBtn = document.getElementById("add-contact-btn");

if (addContactBtn) {
  addContactBtn.addEventListener("click", function(e) {
    e.preventDefault();
    editForm.action = "/sales/contacts/create/";
    editForm.dataset.contactId = "0";

    resetForm();
    const modalInstance = new bootstrap.Modal(editModal);
    modalInstance.show();
  });
}

function bindEditButtons() {
  document.querySelectorAll(".edit-contact-btn").forEach(button => {
    button.addEventListener("click", function() {
      const contactId = this.dataset.contactId;
      const card = this.closest(".contact-card");

      editForm.action = `/sales/contacts/edit/${contactId}/`;
      editForm.dataset.contactId = contactId;

      if (formErrors) {
        formErrors.style.display = "none";
        formErrors.innerHTML = "";
      }

      populateForm(card);
      const modalInstance = new bootstrap.Modal(editModal);
      modalInstance.show();
    });
  });
}

editForm.addEventListener("submit", function(e) {
  e.preventDefault();
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
      searchContacts(document.getElementById("contact-search").value);
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

function resetForm() {
  editForm.querySelector("#first_name").value = "";
  editForm.querySelector("#last_name").value = "";
  editForm.querySelector("#position").value = "";
  editForm.querySelector("#phone").value = "";
  editForm.querySelector("#email").value = "";
  editForm.querySelector("#telegram_username").value = "";
  editForm.querySelector("#telegram_id").value = "";
  window.companyChoices.setChoiceByValue("");
  if (formErrors) {
    formErrors.style.display = "none";
    formErrors.innerHTML = "";
  }
}

function populateForm(card) {
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
  const selectedOption = Array.from(document.getElementById("company").options).find(option => option.dataset.name === companyName);
  window.companyChoices.setChoiceByValue(selectedOption ? selectedOption.value : "");
}

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