// static/js/contact_utils.js
window.contactApp = window.contactApp || {}; // Ensure namespace exists

window.contactApp.showFormErrors = function(error, formErrorsElement) {
  if (!formErrorsElement) {
    console.error("Form errors element not provided to showFormErrors.");
    alert("Сталася помилка валідації. Перевірте консоль."); // Fallback alert
    return;
  }
  formErrorsElement.style.display = "block";
  let errorMessages = "<strong>Помилки:</strong><br>";
  try {
    const parsed = typeof error === "string" ? JSON.parse(error) : error;
    for (const [field, errors] of Object.entries(parsed)) {
      // Try to find a label for the field for better error messages
      const inputElement = document.getElementById(`id_${field}`) || document.querySelector(`[name="${field}"]`);
      const labelElement = inputElement ? document.querySelector(`label[for="${inputElement.id}"]`) : null;
      const fieldName = labelElement ? labelElement.innerText.replace(':', '').trim() : field.replace(/_/g, ' '); // Use label text or format field name

      errors.forEach(err => {
        errorMessages += `<i class="bi bi-exclamation-circle-fill text-danger me-1"></i> ${fieldName}: ${err}<br>`;
      });
    }
  } catch (e) {
     console.warn("Could not parse error object:", error, e);
     const defaultError = typeof error === 'string' ? error : 'Невідома помилка валідації.';
     errorMessages += `<i class="bi bi-exclamation-circle-fill text-danger me-1"></i> ${defaultError}<br>`;
  }
  formErrorsElement.innerHTML = errorMessages;
};

// Add other utility functions if needed