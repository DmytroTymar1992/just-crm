document.addEventListener("DOMContentLoaded", function() {
    document.querySelectorAll('.edit-task-target').forEach(link => {
      link.addEventListener('click', function(e) {
        e.preventDefault();
        const taskId = this.getAttribute('data-task-id');

        fetch(`/sales/get_task/${taskId}/`)
          .then(response => response.json())
          .then(data => {
            if (data.success) {
              document.querySelector('#edit-task-id').value = taskId;
              document.querySelector('#edit-task-type').value = data.task_type;
              // Обрізаємо дату до формату YYYY-MM-DDTHH:MM
              const formattedDate = data.task_date.slice(0, 16); // "2025-04-01T14:30"
              document.querySelector('#edit-task-date').value = formattedDate;
              document.querySelector('#edit-task-target').value = data.target;
              document.querySelector('#edit-task-description').value = data.description || '';
            } else {
              alert('Помилка: ' + data.error);
            }
          })
          .catch(err => console.error('Помилка при завантаженні задачі:', err));
      });
    });
});