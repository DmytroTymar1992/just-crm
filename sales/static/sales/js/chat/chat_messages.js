document.querySelector('#chat-message-submit').onclick = sendTelegram;

document.querySelector('#chat-message-input').addEventListener('keydown', function(e) {
  if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
    e.preventDefault();
    sendTelegram();
  }
});

function sendTelegram() {
  const textarea = document.querySelector('#chat-message-input');
  const message = textarea.value.trim();
  if (!message) return;
  chatSocket.send(JSON.stringify({ 'message': message, 'channel_type': 'telegram' }));
  textarea.value = '';
  textarea.style.height = 'auto';
}

document.querySelector('#email-message-submit').onclick = sendEmail;
function sendEmail() {
  const input = document.querySelector('#email-message-input');
  const message = input.value.trim();
  if (!message) return;
  chatSocket.send(JSON.stringify({ 'message': message, 'channel_type': 'email' }));
  bootstrap.Modal.getInstance(document.getElementById('emailModal')).hide();
  input.value = '';
}

document.querySelector('#email-template-submit').onclick = sendEmailTemplate;
function sendEmailTemplate() {
  const subject = document.querySelector('#email-subject-input')?.value || 'Ласкаво просимо!';
  chatSocket.send(JSON.stringify({ 'message': '', 'subject': subject, 'channel_type': 'email_template' }));
  bootstrap.Modal.getInstance(document.getElementById('emailModal')).hide();
}

function handleIncomingPayload(username, payload) {
  const msgType = payload.msg_type || '';
  if (msgType === 'email') renderEmailMessage(payload);
  else if (msgType === 'telegram') renderTelegramMessage(payload);
  else if (msgType === 'call') renderCallMessage(payload);
  else renderUnknownMessage(payload);
}

function renderEmailMessage(payload) {
  const tpl = document.getElementById('emailMessageTpl').innerHTML;
  let html = tpl
    .replace('__SUBJECT__', payload.subject || '')
    .replace('__BODY__', (payload.body || "").replace(/\n/g, "<br>"))
    .replace('__TIME__', payload.created_at || '')
    .replace('__SENDER_CLASS__', payload.sender_type === 'contact' ? 'justify-content-start' : 'justify-content-end')
    .replace('__BG_COLOR__', payload.sender_type === 'contact' ? '#ffffff' : '#e9f7ef')
    .replace('__BORDER__', payload.sender_type === 'contact' ? 'border-left: 4px solid #28a745' : 'border-right: 4px solid #28a745')
    .replace('__ALIGN__', payload.sender_type === 'contact' ? 'text-end' : 'text-start');
  appendMessage(html);

  if (payload.sender_type === 'contact') {
    const notificationContent = `
      <strong>Email від ${contactFullName}</strong><br>
      <strong>Тема:</strong> ${payload.subject || ''}<br>
      <p class="message-text">${payload.body || ''}</p>
      <small>${payload.created_at || ''}</small>
    `;
    showNotification('email', notificationContent);
  }
}

function renderTelegramMessage(payload) {
  const tpl = document.getElementById('telegramMessageTpl').innerHTML;
  let html = tpl
    .replace('__BODY__', (payload.body || "").replace(/\n/g, "<br>"))
    .replace('__TIME__', payload.created_at || '')
    .replace('__SENDER_CLASS__', payload.sender_type === 'contact' ? 'justify-content-start' : 'justify-content-end')
    .replace('__BG_COLOR__', payload.sender_type === 'contact' ? '#ffffff' : '#e6f0fa')
    .replace('__BORDER__', payload.sender_type === 'contact' ? 'border-left: 4px solid #007bff' : 'border-right: 4px solid #007bff')
    .replace('__ALIGN__', payload.sender_type === 'contact' ? 'text-end' : 'text-start');
  appendMessage(html);

  if (payload.sender_type === 'contact') {
    const notificationContent = `
      <strong>Telegram від ${contactFullName}</strong><br>
      <p class="message-text">${payload.body || ''}</p>
      <small>${payload.created_at || ''}</small>
    `;
    showNotification('telegram', notificationContent);
  }
}

function renderCallMessage(payload) {
  const chatLog = document.getElementById('chat-log');
  const existingMessage = chatLog.querySelector(`[data-uuid="${payload.uuid}"]`);
  const tpl = document.getElementById('callMessageTpl').innerHTML;

  if (existingMessage) {
    const currentMessage = existingMessage.querySelector('.rounded-3');
    let dialAt = currentMessage.querySelector('.mt-1').innerHTML.match(/Початок: (.*)<br>/)?.[1] || '';
    let bridgeAt = currentMessage.querySelector('.mt-1').innerHTML.match(/Підняття слухавки: (.*)<br>/)?.[1] || '';
    let hangupAt = currentMessage.querySelector('.mt-1').innerHTML.match(/Завершення: (.*)$/m)?.[1] || '';

    dialAt = payload.dial_at || dialAt;
    bridgeAt = payload.bridge_at || bridgeAt;
    hangupAt = payload.hangup_at || hangupAt;

    let html = tpl
      .replace('__IS_INCOMING__', payload.direction === 'incoming' ? '(Вхідний)' : '(Вихідний)')
      .replace('__CLIENT_PHONE__', payload.phone || '')
      .replace('__DIAL_AT__', dialAt)
      .replace('__BRIDGE_AT__', bridgeAt)
      .replace('__HANGUP_AT__', hangupAt)
      .replace('__TIME__', payload.created_at || '')
      .replace('__SENDER_CLASS__', payload.direction === 'incoming' ? 'justify-content-start' : 'justify-content-end')
      .replace('__ALIGN__', payload.direction === 'incoming' ? 'text-end' : 'text-start');

    existingMessage.outerHTML = `<div data-uuid="${payload.uuid}" class="mb-3 d-flex ${payload.direction === 'incoming' ? 'justify-content-start' : 'justify-content-end'}">${html}</div>`;
  } else {
    let html = tpl
      .replace('__IS_INCOMING__', payload.direction === 'incoming' ? '(Вхідний)' : '(Вихідний)')
      .replace('__CLIENT_PHONE__', payload.phone || '')
      .replace('__DIAL_AT__', payload.dial_at || '')
      .replace('__BRIDGE_AT__', payload.bridge_at || '')
      .replace('__HANGUP_AT__', payload.hangup_at || '')
      .replace('__TIME__', payload.created_at || '')
      .replace('__SENDER_CLASS__', payload.direction === 'incoming' ? 'justify-content-start' : 'justify-content-end')
      .replace('__ALIGN__', payload.direction === 'incoming' ? 'text-end' : 'text-start');

    const wrapper = document.createElement('div');
    wrapper.setAttribute('data-uuid', payload.uuid);
    wrapper.classList.add('mb-3', 'd-flex', payload.direction === 'incoming' ? 'justify-content-start' : 'justify-content-end');
    wrapper.innerHTML = html;
    chatLog.appendChild(wrapper);
  }
  chatLog.scrollTop = chatLog.scrollHeight;
}

function renderUnknownMessage(payload) {
  const chatLog = document.getElementById('chat-log');
  const wrapper = document.createElement('div');
  wrapper.classList.add('mb-3', 'd-flex', 'justify-content-end');
  const msgDiv = document.createElement('div');
  msgDiv.classList.add('p-3', 'rounded-3', 'shadow-sm', 'bg-warning', 'text-dark');
  msgDiv.style.maxWidth = '70%';
  msgDiv.innerHTML = `UNKNOWN type message: <pre>${JSON.stringify(payload, null, 2)}</pre>`;
  wrapper.appendChild(msgDiv);
  chatLog.appendChild(wrapper);
  chatLog.scrollTop = chatLog.scrollHeight;
}

function appendMessage(html) {
  const chatLog = document.getElementById('chat-log');
  const wrapper = document.createElement('div');
  wrapper.innerHTML = html;
  chatLog.appendChild(wrapper);
  chatLog.scrollTop = chatLog.scrollHeight;
}