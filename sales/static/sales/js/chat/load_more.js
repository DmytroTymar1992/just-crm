let currentPage = window.chatData.currentPage;
let hasPrevious = window.chatData.hasPrevious;
let prevPageNumber = hasPrevious ? (currentPage - 1) : null;

const loadMoreBtn = document.getElementById('load-more-btn');
if (hasPrevious) loadMoreBtn.style.display = 'block';

loadMoreBtn.addEventListener('click', function() {
  loadOlderMessages();
});

function loadOlderMessages() {
  if (!prevPageNumber) return;
  const url = `/sales/${window.chatData.roomId}/load_more_interactions/?page=${prevPageNumber}`;
  fetch(url)
    .then(response => response.json())
    .then(data => {
      const chatLog = document.getElementById('chat-log');
      const tempDiv = document.createElement('div');
      tempDiv.innerHTML = data.messages_html;
      chatLog.insertBefore(tempDiv, chatLog.firstChild);
      hasPrevious = data.has_previous;
      prevPageNumber = hasPrevious ? data.prev_page_number : null;
      if (!hasPrevious) loadMoreBtn.style.display = 'none';
    })
    .catch(err => console.error("Помилка при завантаженні старіших повідомлень:", err));
}