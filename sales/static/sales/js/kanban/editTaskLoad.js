document.addEventListener("DOMContentLoaded", function() {
    document.querySelectorAll('.edit-task-target').forEach(link => {
      link.addEventListener('click', function(e) {
        e.preventDefault();
        const taskId = this.getAttribute('data-task-id');
        console.log('Task ID:', taskId); // Перевіряємо, чи правильно береться ID

        fetch(`/sales/get_task/${taskId}/`)
          .then(response => {
            console.log('Response status:', response.status); // Перевіряємо статус відповіді
            return response.json();
          })
          .then(data => {
            console.log('Server data:', data); // Виводимо всю відповідь сервера
            if (data.success) {
              document.querySelector('#edit-task-id').value = taskId;
              document.querySelector('#edit-task-type').value = data.task_type;
              const formattedDate = data.task_date.slice(0, 16);
              console.log('Raw task_date:', data.task_date); // Сире значення дати
              console.log('Formatted date:', formattedDate); // Оброблене значення
              document.querySelector('#edit-task-date').value = formattedDate;
              console.log('Input value after set:', document.querySelector('#edit-task-date').value); // Перевіряємо, чи встановилось
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