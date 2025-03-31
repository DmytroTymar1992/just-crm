const currentUser = "{{ request.user.username }}";
const roomId = "{{ room_id }}";
const chatSocket = new WebSocket('ws://' + window.location.host + '/ws/sales/' + roomId + '/');
const chatUrl = `/sales/${roomId}/`;
const contactFirstName = "{{ room.contact.first_name|escapejs }}";
const contactLastName = "{{ room.contact.last_name|default:''|escapejs }}";
const contactFullName = `${contactFirstName} ${contactLastName}`.trim() || "Контакт";

chatSocket.onopen = function(e) {
  console.log('Chat WebSocket connection opened for room:', roomId);
};

chatSocket.onmessage = function(e) {
  const data = JSON.parse(e.data);
  console.log('Chat WebSocket message received:', data);
  const username = data.username || 'User';
  const payload = data.payload || {};
  handleIncomingPayload(username, payload); // Імпортується з chat_messages.js
};

chatSocket.onclose = function(e) {
  console.error('Chat WebSocket closed:', e);
};

chatSocket.onerror = function(e) {
  console.error('Chat WebSocket error:', e);
};

document.addEventListener("DOMContentLoaded", function() {
  const chatLog = document.getElementById("chat-log");
  if (chatLog) chatLog.scrollTop = chatLog.scrollHeight;
  loadVacancies(); // Імпортується з vacancies.js
});