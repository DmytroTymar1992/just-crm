
const protocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
const chatSocket = new WebSocket(protocol + window.location.host + '/ws/sales/' + window.chatData.roomId + '/');
const chatUrl = `/sales/${window.chatData.roomId}/`;

chatSocket.onopen = function(e) {
  console.log('Chat WebSocket connection opened for room:', window.chatData.roomId);
};

chatSocket.onmessage = function(e) {
  const data = JSON.parse(e.data);
  console.log('Chat WebSocket message received:', data);
  const username = data.username || 'User';
  const payload = data.payload || {};
  handleIncomingPayload(username, payload); // З chat_messages.js
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
  loadVacancies(); // З vacancies.js
});