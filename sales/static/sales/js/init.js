document.addEventListener("DOMContentLoaded", function() {
    const container = document.getElementById("contacts-container");
    if (container) {
        container.scrollTop = container.scrollHeight;
    }
});