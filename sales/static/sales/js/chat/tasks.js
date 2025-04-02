document.addEventListener("DOMContentLoaded", function() {
    function showTaskNotification(message) {
        const container = document.getElementById('task-notification-container');
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
        "Запитати за релевантність відгуків",

    ];

    const taskDateInput = document.querySelector('#task-date');
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

    document.querySelector('#create-task-btn').addEventListener('click', function() {
        const modal = new bootstrap.Modal(document.getElementById('taskModal'));
        modal.show();

        const targetInput = document.querySelector('#task-target');
        const targetWarning = document.querySelector('#target-warning');
        const suggestionsContainer = document.querySelector('#target-suggestions');

        // Логіка для підказок і обмеження
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
            updateSuggestions(this.value || ''); // Відкриваємо список одразу
        });

        targetInput.addEventListener('blur', () => {
            setTimeout(() => suggestionsContainer.style.display = 'none', 200);
        });
    });

    document.querySelector('#task-submit').onclick = createTask;

    function createTask() {
        const taskType = document.querySelector('#task-type').value;
        const selectedDate = document.querySelector('#task-date').value;
        const taskTarget = document.querySelector('#task-target').value;
        const taskDescription = document.querySelector('#task-description').value;

        if (!taskType || !selectedDate || !taskTarget) {
            showTaskNotification('Будь ласка, заповніть усі обов’язкові поля!');
            return;
        }

        const taskDateTime = `${selectedDate}T12:00`;

        fetch('/sales/create_task/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken(),
            },
            body: JSON.stringify({
                room_id: window.chatData.roomId,
                task_type: taskType,
                task_date: taskDateTime,
                target: taskTarget,
                description: taskDescription,
            }),
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showTaskNotification('Задачу створено!');
                const modal = bootstrap.Modal.getInstance(document.getElementById('taskModal'));
                modal.hide();
                document.querySelector('#task-form').reset();
            } else {
                showTaskNotification('Помилка: ' + data.error);
            }
        })
        .catch(err => {
            showTaskNotification('Помилка при створенні задачі');
        });
    }
});