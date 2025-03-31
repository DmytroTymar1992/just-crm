document.querySelector('#chat-message-input').addEventListener('input', function() {
  this.style.height = 'auto';
  this.style.height = `${this.scrollHeight}px`;
});

function getCsrfToken() {
  return document.querySelector('[name=csrfmiddlewaretoken]').value;
}