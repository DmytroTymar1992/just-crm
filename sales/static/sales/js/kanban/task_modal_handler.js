// Файл: static/sales/js/task_modal_handler.js

document.addEventListener("DOMContentLoaded", function() {

    // --- Функція для отримання CSRF токена ---
    function getCsrfToken() {
        // Спочатку шукаємо токен у формі модального вікна
        const form = document.getElementById('edit-task-form');
        if (form) {
            const csrfInput = form.querySelector('[name=csrfmiddlewaretoken]');
            if (csrfInput) {
                return csrfInput.value;
            }
        }
        // Якщо у формі немає, шукаємо в куках (запасний варіант)
        const csrfCookie = document.cookie.split('; ').find(row => row.startsWith('csrftoken='));
        if (csrfCookie) {
            return csrfCookie.split('=')[1];
        }
        console.error("CSRF Token not found!");
        return null; // Повертаємо null, якщо токен не знайдено
    }

    // --- Ініціалізація модального вікна ---
    const editTaskModalElement = document.getElementById('editTaskModal');
    let editTaskModalInstance = null;
    if (editTaskModalElement) {
        editTaskModalInstance = new bootstrap.Modal(editTaskModalElement);

        // --- Обробка події ПЕРЕД показом модального вікна ---
        editTaskModalElement.addEventListener('show.bs.modal', function (event) {
            const triggerElement = event.relatedTarget; // Елемент, що викликав модалку
            if (!triggerElement) return;

            const taskId = triggerElement.getAttribute('data-task-id');
            const modalForm = editTaskModalElement.querySelector('#edit-task-form');
            const taskIdInput = modalForm.querySelector('#edit-task-id');
            const taskTypeSelect = modalForm.querySelector('#edit-task-type');
            const taskDateInput = modalForm.querySelector('#edit-task-date');
            const taskTargetInput = modalForm.querySelector('#edit-task-target');
            const taskDescriptionTextarea = modalForm.querySelector('#edit-task-description');
            const completeBtnModal = modalForm.parentElement.querySelector('#complete-task-modal-btn'); // Кнопка "Завершити"

            // Очищення форми перед заповненням
            modalForm.reset(); // Скидає значення полів форми
            taskIdInput.value = '';
            if (completeBtnModal) completeBtnModal.style.display = 'none'; // Ховаємо кнопку завершення

            if (!taskId) {
                console.error("Task ID not found on trigger element");
                return;
            }

            // Показуємо індикатор завантаження (опціонально)
            // modalForm.classList.add('loading');

            // Завантажуємо дані задачі
            fetch(`/sales/get_task/${taskId}/`) // Переконайтесь, що URL правильний
                .then(response => {
                    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
                    return response.json();
                })
                .then(data => {
                    if (data.success) {
                        taskIdInput.value = taskId;
                        taskTypeSelect.value = data.task_type;
                        try {
                            const dateObj = new Date(data.task_date);
                            const year = dateObj.getFullYear();
                            const month = (dateObj.getMonth() + 1).toString().padStart(2, '0');
                            const day = dateObj.getDate().toString().padStart(2, '0');
                            const hours = dateObj.getHours().toString().padStart(2, '0');
                            const minutes = dateObj.getMinutes().toString().padStart(2, '0');
                            taskDateInput.value = `<span class="math-inline">\{year\}\-</span>{month}-<span class="math-inline">\{day\}T</span>{hours}:${minutes}`;
                        } catch (e) {
                            console.error("Error parsing task date:", e);
                        }
                        taskTargetInput.value = data.target;
                        taskDescriptionTextarea.value = data.description || '';

                        // Показуємо кнопку "Завершити", якщо задача не завершена (припускаємо, що бекенд це повертає)
                        if (completeBtnModal && data.is_completed === false) { // Потрібно додати is_completed в get_task view
                            completeBtnModal.style.display = 'inline-block';
                            completeBtnModal.setAttribute('data-task-id', taskId); // Встановлюємо ID для кнопки
                        }

                    } else {
                        alert('Помилка завантаження даних: ' + data.error);
                        if (editTaskModalInstance) editTaskModalInstance.hide();
                    }
                })
                .catch(err => {
                    console.error('Помилка при завантаженні задачі:', err);
                    alert('Не вдалося завантажити дані задачі.');
                    if (editTaskModalInstance) editTaskModalInstance.hide();
                })
                .finally(() => {
                     // Прибираємо індикатор завантаження (опціонально)
                     // modalForm.classList.remove('loading');
                });
        });
    } else {
        console.warn("Modal with ID 'editTaskModal' not found.");
    }

    // --- Обробка кнопки "Зберегти" в модалці ---
    const saveButton = document.querySelector('#edit-task-submit');
    if (saveButton) {
        saveButton.addEventListener('click', function() {
            const modalForm = document.getElementById('edit-task-form');
            const taskId = modalForm.querySelector('#edit-task-id').value;
            const formData = new FormData(modalForm); // Збираємо дані форми
            const jsonData = Object.fromEntries(formData.entries()); // Конвертуємо в JSON
            jsonData.task_id = taskId; // Додаємо task_id

            // Валідація
            if (!jsonData.task_type || !jsonData.task_date || !jsonData.target) {
                alert('Будь ласка, заповніть обов’язкові поля (Тип, Дата, Ціль)!');
                return;
            }

            const csrfToken = getCsrfToken();
            if (!csrfToken) {
                alert('Помилка безпеки: CSRF токен не знайдено.'); return;
            }

            fetch('/sales/edit_task/', { // Переконайтесь, що URL правильний
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken,
                },
                body: JSON.stringify(jsonData), // Відправляємо зібрані дані
            })
            .then(response => response.json().catch(() => response.text().then(text => { throw new Error(text) }))) // Обробка JSON або тексту помилки
            .then(data => {
                if (data.success) {
                    alert('Задачу оновлено!');
                    if (editTaskModalInstance) editTaskModalInstance.hide();
                    // Оновлюємо UI без перезавантаження (складніший варіант) або перезавантажуємо
                    location.reload(); // Найпростіший варіант
                    // TODO: Розглянути оновлення UI без перезавантаження (наприклад, оновити картку/хедер)
                } else {
                     let errorMessage = data.error || 'Помилка збереження.';
                     if (data.errors) {
                         errorMessage += "\n";
                         for (const field in data.errors) { errorMessage += `${field}: ${data.errors[field].join(', ')}\n`; }
                     }
                    alert('Помилка: ' + errorMessage);
                }
            })
            .catch(err => {
                console.error('Помилка при оновленні задачі:', err);
                alert('Сталася помилка під час збереження змін: ' + err.message);
            });
        });
    } else {
        console.warn("Save button with ID 'edit-task-submit' not found.");
    }


    // --- Функція для завершення задачі (використовується з різних місць) ---
    function completeTask(taskId, elementToRemove = null) {
         const csrfToken = getCsrfToken();
         if (!csrfToken) {
             alert('Помилка безпеки: CSRF токен не знайдено.'); return;
         }

         if (!confirm(`Ви впевнені, що хочете завершити задачу #${taskId}?`)) {
             return;
         }

         fetch('/sales/complete_task/', { // Переконайтесь, що URL правильний
             method: 'POST',
             headers: {
                 'Content-Type': 'application/json',
                 'X-CSRFToken': csrfToken,
             },
             body: JSON.stringify({ task_id: taskId }),
         })
         .then(response => response.json())
         .then(data => {
             if (data.success) {
                 alert('Задачу завершено!');
                 if (elementToRemove) {
                     elementToRemove.remove(); // Видаляємо картку з Kanban
                 }
                 // Якщо викликано з модалки, закриваємо її і оновлюємо UI
                 if (editTaskModalInstance && editTaskModalElement.classList.contains('show')) {
                      editTaskModalInstance.hide();
                 }
                 // Оновлюємо UI без перезавантаження або перезавантажуємо
                 location.reload(); // Найпростіший варіант
                 // TODO: Розглянути оновлення UI без перезавантаження
             } else {
                 alert('Помилка завершення задачі: ' + data.error);
             }
         })
         .catch(err => {
             console.error('Помилка при завершенні задачі:', err);
             alert('Сталася помилка під час завершення задачі.');
         });
    }

    // --- Обробка кнопки "Завершити" НА КАНБАН-КАРТЦІ ---
    document.querySelectorAll('.complete-task-btn').forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            const taskId = this.getAttribute('data-task-id');
            const card = this.closest('.kanban-card'); // Елемент для видалення - картка
            completeTask(taskId, card);
        });
    });

     // --- Обробка кнопки "Завершити" В МОДАЛЬНОМУ ВІКНІ ---
     const completeBtnModal = document.querySelector('#complete-task-modal-btn');
     if (completeBtnModal) {
         completeBtnModal.addEventListener('click', function(e) {
             e.preventDefault();
             const taskId = this.getAttribute('data-task-id');
             completeTask(taskId); // Передаємо null, бо не треба видаляти картку
         });
     }

}); // Кінець DOMContentLoaded