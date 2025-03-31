function loadVacancies() {
  const vacanciesList = document.getElementById('vacancies-list');
  fetch(`/sales/${roomId}/vacancies/`)
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        vacanciesList.innerHTML = '';
        if (data.vacancies.length === 0) {
          vacanciesList.innerHTML = '<p class="text-muted text-center py-3">Вакансій немає</p>';
        } else {
          data.vacancies.forEach(vacancy => {
            const vacancyHtml = `
              <div class="list-group-item vacancy-item ${vacancy.is_hot ? 'hot' : ''} p-3">
                <h6 class="mb-1 fw-bold">${vacancy.title}</h6>
                <p class="mb-1 text-muted small">${vacancy.city || 'Місто не вказано'}</p>
                <small class="text-muted">Додано: ${vacancy.created_at || 'Невідомо'}</small>
                ${vacancy.work_id ? `<a href="https://www.work.ua/jobs/${vacancy.work_id}/" target="_blank" class="d-block text-primary small">Переглянути на Work.ua</a>` : ''}
              </div>
            `;
            vacanciesList.insertAdjacentHTML('beforeend', vacancyHtml);
          });
        }
      } else {
        vacanciesList.innerHTML = '<p class="text-muted text-center py-3">Помилка завантаження вакансій</p>';
      }
    })
    .catch(error => {
      console.error('Помилка:', error);
      vacanciesList.innerHTML = '<p class="text-muted text-center py-3">Щось пішло не так</p>';
    });
}