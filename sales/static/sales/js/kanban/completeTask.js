document.addEventListener("DOMContentLoaded", function() {
    document.querySelectorAll('.complete-task-btn').forEach(btn => {
      btn.addEventListener('click', function(e) {
        e.preventDefault();
        const taskId = this.getAttribute('data-task-id');
        const card = this.closest('.kanban-card');

        fetch('/sales/complete_task/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken(),
          },
          body: JSON.stringify({
            task_id: taskId,
          }),
        })
        .then(response => response.json())
        .then(data => {
          if (data.success) {
            alert('Задачу закрито!');
            card.remove();
          } else {
            alert('Помилка: ' + data.error);
          }
        })
        .catch(err => {
          console.error('Помилка при закритті задачі:', err);
          alert('Помилка при закритті задачі');
        });
      });
    });
});