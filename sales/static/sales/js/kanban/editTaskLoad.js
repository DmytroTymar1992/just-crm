document.addEventListener("DOMContentLoaded", function() {
    function showTaskNotification(message) {
        const container = document.getElementById('task-notification-container');
        if (!container) return;
        const notification = document.createElement('div');
        notification.className = 'task-notification';
        notification.textContent = message;
        container.appendChild(notification);

        setTimeout(() => notification.classList.add('show'), 10);
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => notification.remove(), 500);
        }, 5000);
    }

    const suggestionsList = [
        "Перша дзвінок",
        "Нагадати за сайт",
        "Чи відвідували сайт",
        "Чи погодили з керівництвом",
        "Чи розглядали тарифи",
        "Запитати за релевантність відгуків"
    ];

    // Ініціалізація Flatpickr для дати
    const taskDateInput = document.querySelector('#task-date');
    if (taskDateInput) {
        flatpickr(taskDateInput, {
            dateFormat: "Y-m-d",
            disableMobile: true,
            allowInput: false,
            clickOpens: true,
            locale: "uk",
            onReady: function() {
                taskDateInput.addEventListener('click', function() {
                    this._flatpickr.open();
                });
            }
        });
    }

    const transferDateInput = document.querySelector('#transfer-task-date');
    if (transferDateInput) {
        flatpickr(transferDateInput, {
            dateFormat: "Y-m-d",
            disableMobile: true,
            allowInput: false,
            clickOpens: true,
            locale: "uk",
            onReady: function() {
                transferDateInput.addEventListener('click', function() {
                    this._flatpickr.open();
                });
            }
        });
    }

    // Функція для отримання contact_id із чату
    function getChatContactId() {
        return (window.chatData && window.chatData.contactId) ? window.chatData.contactId : '';
    }

    // Функція для отримання fallback contact_id з data-атрибута модалки (для taskModal)
    function getFallbackContactId() {
        const modal = document.getElementById('taskModal');
        return modal ? modal.dataset.contactId || '' : '';
    }

    // Уніфікована функція отримання contact_id – спочатку з параметру, потім із чату, потім fallback
    function getEffectiveContactId(passedId = '') {
        return passedId || getChatContactId() || getFallbackContactId();
    }

    // Функція ініціалізації модалки створення задачі
    function initializeTaskModal(contactIdFromCaller = '') {
        const targetInput = document.querySelector('#task-target');
        const targetWarning = document.querySelector('#target-warning');
        const suggestionsContainer = document.querySelector('#target-suggestions');
        const taskContactIdInput = document.querySelector('#task-contact-id');

        // Отримуємо ефективний contact_id
        const contactId = getEffectiveContactId(contactIdFromCaller);
        taskContactIdInput.value = contactId;
        console.log('initializeTaskModal - contactId:', contactId);

        // Дебаг: вивід contact_id у модалці
        let debugDisplay = document.getElementById('contact-id-display');
        if (!debugDisplay) {
            debugDisplay = document.createElement('p');
            debugDisplay.id = 'contact-id-display';
            debugDisplay.style.color = 'red';
            document.querySelector('#task-form').appendChild(debugDisplay);
        }
        debugDisplay.textContent = "Contact ID: " + contactId;

        if (!contactId) {
            showTaskNotification('Не вдалося визначити contact_id!');
            return;
        }

        function updateSuggestions(inputValue) {
            suggestionsContainer.innerHTML = '';
            const filteredSuggestions = suggestionsList.filter(suggestion =>
                suggestion.toLowerCase().includes(inputValue.toLowerCase())
            );

            if (filteredSuggestions.length > 0) {
                filteredSuggestions.forEach(suggestion => {
                    const div = document.createElement('div');
                    div.className = 'suggestion-item';
                    div.textContent = suggestion;
                    div.style.padding = '8px 12px';
                    div.style.cursor = 'pointer';
                    div.style.transition = 'background 0.2s ease';
                    div.addEventListener('click', () => {
                        targetInput.value = suggestion.slice(0, 50);
                        targetWarning.style.display = suggestion.length >= 50 ? 'block' : 'none';
                        suggestionsContainer.style.display = 'none';
                    });
                    div.addEventListener('mouseover', () => div.style.background = '#e5e7eb');
                    div.addEventListener('mouseout', () => div.style.background = '#fff');
                    suggestionsContainer.appendChild(div);
                });
                suggestionsContainer.style.display = 'block';
            } else {
                suggestionsContainer.style.display = 'none';
            }
        }

        targetInput.addEventListener('input', function() {
            if (this.value.length > 50) {
                this.value = this.value.slice(0, 50);
            }
            targetWarning.style.display = this.value.length >= 50 ? 'block' : 'none';
            updateSuggestions(this.value);
        });

        targetInput.addEventListener('focus', function() {
            updateSuggestions(this.value || '');
        });

        targetInput.addEventListener('blur', () => {
            setTimeout(() => suggestionsContainer.style.display = 'none', 200);
        });

        document.querySelector('#task-submit').onclick = function() {
            const taskType = document.querySelector('#task-type').value;
            const selectedDate = document.querySelector('#task-date').value;
            const taskTarget = document.querySelector('#task-target').value;
            const taskDescription = document.querySelector('#task-description').value;
            const contactId = taskContactIdInput.value;

            if (!taskType || !selectedDate || !taskTarget || !contactId) {
                showTaskNotification('Будь ласка, заповніть усі обов’язкові поля, включаючи contact_id!');
                return;
            }

            // Формуємо дату із часом "12:00:00"
            const taskDateTime = `${selectedDate}T12:00:00`;
            const payload = {
                task_type: taskType,
                task_date: taskDateTime,
                target: taskTarget,
                description: taskDescription,
                contact_id: contactId
            };

            console.log('Task creation payload:', payload);

            fetch('/sales/create_task/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken(),
                },
                body: JSON.stringify(payload),
            })
            .then(response => response.json())
            .then(data => {
                console.log('Task creation response:', data);
                if (data.success) {
                    showTaskNotification('Задачу створено!');
                    const modal = bootstrap.Modal.getInstance(document.getElementById('taskModal'));
                    modal.hide();
                    document.querySelector('#task-form').reset();
                    setTimeout(() => location.reload(), 500);
                } else {
                    showTaskNotification('Помилка: ' + (data.error || 'Невідома помилка'));
                }
            })
            .catch(err => {
                console.error('Task creation error:', err);
                showTaskNotification('Помилка при створенні задачі');
            });
        };
    }

    // 1. Для створення задачі "з нуля" (на сторінках чату – використовуємо window.chatData)
    const createTaskBtn = document.querySelector('#create-task-btn');
    if (createTaskBtn) {
        createTaskBtn.addEventListener('click', function() {
            const modal = new bootstrap.Modal(document.getElementById('taskModal'));
            const contactIdFromChat = getChatContactId();
            initializeTaskModal(contactIdFromChat);
            modal.show();
        });
    }

    // 2. Для створення задачі на основі закритої (на інших сторінках – контактний ID передається через карточку)
    // Змінимо делегування подій для .edit-task-target, щоб зчитувати data-contact-id із карточки
    document.addEventListener('click', function(e) {
        const target = e.target.closest('.edit-task-target');
        if (target) {
            e.preventDefault();
            const taskId = target.getAttribute('data-task-id');
            const card = target.closest('.kanban-card');
            const fallbackContactId = card ? card.dataset.contactId : "";
            if (taskId) {
                initializeEditTaskModal(taskId, fallbackContactId);
            }
        }
    });

    // Функція ініціалізації модалки редагування задачі.
    // Додатковий параметр fallbackContactId використовується, якщо сервер не поверне contact_id.
    function initializeEditTaskModal(taskId, fallbackContactId = "") {
        fetch(`/sales/get_task/${taskId}/`)
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    document.querySelector('#edit-task-id').value = taskId;
                    document.querySelector('#edit-task-type').value = data.task_type;
                    document.querySelector('#edit-task-target').value = data.target;
                    document.querySelector('#edit-task-description').value = data.description || '';
                    // Використовуємо contact_id із сервера або fallback, якщо його немає
                    document.querySelector('#edit-contact-id').value = data.contact_id || fallbackContactId;
                    document.querySelector('#transfer-task-date').value = '';
                    document.querySelector('#transfer-reason').value = '';

                    const modal = new bootstrap.Modal(document.getElementById('editTaskModal'));
                    modal.show();

                    const slider = document.querySelector('#task-complete-slider');
                    const sliderTrack = document.querySelector('.slider-track');
                    const sliderThumb = document.querySelector('.slider-thumb');
                    const sliderLabel = document.querySelector('.slider-label');
                    const mainSection = document.querySelector('#main-section');
                    const transferSection = document.querySelector('#transfer-section');
                    const toggleTransferBtn = document.querySelector('#toggle-transfer-btn');
                    const transferSubmitBtn = document.querySelector('#transfer-task-submit');
                    const editSubmitBtn = document.querySelector('#edit-task-submit');
                    const targetInput = document.querySelector('#edit-task-target');
                    const targetWarning = document.querySelector('#edit-target-warning');
                    const suggestionsContainer = document.querySelector('#edit-target-suggestions');

                    slider.value = 0;
                    sliderTrack.style.width = '0%';
                    sliderThumb.style.left = '0%';
                    sliderLabel.style.display = 'block';
                    mainSection.style.display = 'block';
                    transferSection.style.display = 'none';
                    toggleTransferBtn.style.display = 'block';
                    transferSubmitBtn.style.display = 'none';
                    editSubmitBtn.style.display = 'block';

                    function updateSuggestions(inputValue) {
                        suggestionsContainer.innerHTML = '';
                        const filteredSuggestions = suggestionsList.filter(suggestion =>
                            suggestion.toLowerCase().includes(inputValue.toLowerCase())
                        );

                        if (filteredSuggestions.length > 0) {
                            filteredSuggestions.forEach(suggestion => {
                                const div = document.createElement('div');
                                div.className = 'suggestion-item';
                                div.textContent = suggestion;
                                div.style.padding = '8px 12px';
                                div.style.cursor = 'pointer';
                                div.style.transition = 'background 0.2s ease';
                                div.addEventListener('click', () => {
                                    targetInput.value = suggestion.slice(0, 50);
                                    targetWarning.style.display = suggestion.length >= 50 ? 'block' : 'none';
                                    suggestionsContainer.style.display = 'none';
                                });
                                div.addEventListener('mouseover', () => div.style.background = '#e5e7eb');
                                div.addEventListener('mouseout', () => div.style.background = '#fff');
                                suggestionsContainer.appendChild(div);
                            });
                            suggestionsContainer.style.display = 'block';
                        } else {
                            suggestionsContainer.style.display = 'none';
                        }
                    }

                    targetInput.addEventListener('input', function() {
                        if (this.value.length > 50) {
                            this.value = this.value.slice(0, 50);
                        }
                        targetWarning.style.display = this.value.length >= 50 ? 'block' : 'none';
                        updateSuggestions(this.value);
                    });

                    targetInput.addEventListener('focus', function() {
                        updateSuggestions(this.value || '');
                    });

                    targetInput.addEventListener('blur', () => {
                        setTimeout(() => suggestionsContainer.style.display = 'none', 200);
                    });

                    slider.addEventListener('input', function() {
                        const value = this.value;
                        const percentage = `${value}%`;
                        sliderTrack.style.width = percentage;
                        sliderThumb.style.left = percentage;
                        if (value > 50) sliderLabel.style.display = 'none';
                        if (value === '100') {
                            fetch('/sales/complete_task/', {
                                method: 'POST',
                                headers: {
                                    'Content-Type': 'application/json',
                                    'X-CSRFToken': getCsrfToken(),
                                },
                                body: JSON.stringify({ task_id: taskId }),
                            })
                            .then(response => response.json())
                            .then(data => {
                                if (data.success) {
                                    showTaskNotification('Задачу виконано!');
                                    modal.hide();

                                    // Передаємо contact_id із модалки редагування в suggest-модалку
                                    const contactIdFromEdit = document.querySelector('#edit-contact-id').value;
                                    const suggestModalEl = document.getElementById('suggestNewTaskModal');
                                    let hiddenContactField = suggestModalEl.querySelector('#contact-id');
                                    if (!hiddenContactField) {
                                        hiddenContactField = document.createElement('input');
                                        hiddenContactField.type = 'hidden';
                                        hiddenContactField.id = 'contact-id';
                                        suggestModalEl.querySelector('.modal-body').appendChild(hiddenContactField);
                                    }
                                    hiddenContactField.value = contactIdFromEdit;
                                    console.log("Suggest modal - contact_id:", hiddenContactField.value);

                                    const suggestModal = new bootstrap.Modal(suggestModalEl);
                                    suggestModal.show();

                                    let shouldCreateNewTask = false;

                                    document.querySelector('#create-new-task-btn').onclick = function() {
                                        shouldCreateNewTask = true;
                                        suggestModal.hide();
                                        const createModalEl = document.getElementById('taskModal');
                                        const createModal = new bootstrap.Modal(createModalEl);
                                        let newContactId = document.querySelector('#contact-id').value;
                                        if (!newContactId) {
                                            newContactId = document.querySelector('#edit-contact-id') ? document.querySelector('#edit-contact-id').value : '';
                                            console.log("Fallback contact_id:", newContactId);
                                        }
                                        console.log("Creating new task with contact_id:", newContactId);
                                        initializeTaskModal(newContactId);
                                        createModal.show();

                                        createModalEl.addEventListener('hidden.bs.modal', function() {
                                            location.reload();
                                        }, { once: true });
                                    };

                                    suggestModalEl.addEventListener('hidden.bs.modal', function() {
                                        if (!shouldCreateNewTask) {
                                            location.reload();
                                        }
                                    }, { once: true });
                                } else {
                                    showTaskNotification('Помилка: ' + data.error);
                                    slider.value = 0;
                                    sliderTrack.style.width = '0%';
                                    sliderThumb.style.left = '0%';
                                    sliderLabel.style.display = 'block';
                                }
                            })
                            .catch(err => {
                                showTaskNotification('Помилка при виконанні задачі');
                                slider.value = 0;
                                sliderTrack.style.width = '0%';
                                sliderThumb.style.left = '0%';
                                sliderLabel.style.display = 'block';
                            });
                        }
                    });

                    editSubmitBtn.addEventListener('click', function() {
                        const taskId = document.querySelector('#edit-task-id').value;
                        const taskType = document.querySelector('#edit-task-type').value;
                        const taskTarget = document.querySelector('#edit-task-target').value;
                        const taskDescription = document.querySelector('#edit-task-description').value;

                        if (!taskType || !taskTarget) {
                            showTaskNotification('Будь ласка, заповніть усі обов’язкові поля!');
                            return;
                        }

                        fetch('/sales/edit_task/', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                                'X-CSRFToken': getCsrfToken(),
                            },
                            body: JSON.stringify({
                                task_id: taskId,
                                task_type: taskType,
                                task_date: data.task_date,
                                target: taskTarget,
                                description: taskDescription,
                            }),
                        })
                        .then(response => response.json())
                        .then(data => {
                            if (data.success) {
                                showTaskNotification('Задачу оновлено!');
                                modal.hide();
                                setTimeout(() => location.reload(), 500);
                            } else {
                                showTaskNotification('Помилка: ' + data.error);
                            }
                        })
                        .catch(err => {
                            showTaskNotification('Помилка при оновленні задачі');
                        });
                    });

                    toggleTransferBtn.onclick = function() {
                        mainSection.style.display = 'none';
                        transferSection.style.display = 'block';
                        toggleTransferBtn.style.display = 'none';
                        transferSubmitBtn.style.display = 'block';
                        editSubmitBtn.style.display = 'none';
                    };

                    transferSubmitBtn.onclick = function() {
                        const selectedDate = document.querySelector('#transfer-task-date').value;
                        const reason = document.querySelector('#transfer-reason').value;

                        if (!selectedDate || !reason) {
                            showTaskNotification('Вкажіть нову дату і причину перенесення!');
                            return;
                        }

                        const newTaskDateTime = `${selectedDate}T12:00:00`;

                        fetch('/sales/transfer_task/', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                                'X-CSRFToken': getCsrfToken(),
                            },
                            body: JSON.stringify({
                                task_id: taskId,
                                new_task_date: newTaskDateTime,
                                reason: reason,
                            }),
                        })
                        .then(response => response.json())
                        .then(data => {
                            if (data.success) {
                                showTaskNotification('Задачу перенесено!');
                                modal.hide();
                                setTimeout(() => location.reload(), 500);
                            } else {
                                showTaskNotification('Помилка: ' + data.error);
                            }
                        })
                        .catch(err => {
                            showTaskNotification('Помилка при перенесенні задачі');
                        });
                    };
                } else {
                    showTaskNotification('Помилка: ' + data.error);
                }
            })
            .catch(err => {
                showTaskNotification('Помилка при завантаженні задачі');
            });
    }
});
