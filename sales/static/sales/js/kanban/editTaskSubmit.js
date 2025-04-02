document.addEventListener("DOMContentLoaded", function() {
    document.querySelector('#edit-task-submit').addEventListener('click', function() {
      const taskId = document.querySelector('#edit-task-id').value;
      const taskType = document.querySelector('#edit-task-type').value;
      const taskDate = document.querySelector('#edit-task-date').value;
      const taskTarget = document.querySelector('#edit-task-target').value;
      const taskDescription = document.querySelector('#edit-task-description').value;

      if (!taskType || !taskDate || !taskTarget) {
        alert('Будь ласка, заповніть усі обов’язкові поля!');
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
          task_date: taskDate,
          target: taskTarget,
          description: taskDescription,
        }),
      })
      .then(response => response.json())
      .then(data => {
        if (data.success) {
          alert('Задачу оновлено!');
          bootstrap.Modal.getInstance(document.getElementById('editTaskModal')).hide();
          location.reload();
        } else {
          alert('Помилка: ' + data.error);
        }
      })
      .catch(err => console.error('Помилка при оновленні задачі:', err));
    });
});