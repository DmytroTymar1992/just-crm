document.querySelector('#task-submit').onclick = createTask;

function createTask() {
  const taskType = document.querySelector('#task-type').value;
  const taskDate = document.querySelector('#task-date').value;
  const taskTarget = document.querySelector('#task-target').value;
  const taskDescription = document.querySelector('#task-description').value;

  if (!taskType || !taskDate || !taskTarget) {
    alert('Будь ласка, заповніть усі обов’язкові поля!');
    return;
  }

  fetch('/sales/create_task/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCsrfToken(),
    },
    body: JSON.stringify({
      room_id: window.chatData.roomId,
      task_type: taskType,
      task_date: taskDate,
      target: taskTarget,
      description: taskDescription,
    }),
  })
  .then(response => response.json())
  .then(data => {
    if (data.success) {
      alert('Задачу створено!');
      bootstrap.Modal.getInstance(document.getElementById('taskModal')).hide();
      document.querySelector('#task-form').reset();
    } else {
      alert('Помилка: ' + data.error);
    }
  })
  .catch(err => console.error('Помилка при створенні задачі:', err));
}