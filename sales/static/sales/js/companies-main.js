document.addEventListener("DOMContentLoaded", function() {
  const container = document.getElementById("companies-container");
  if (container) {
    container.style.maxHeight = "calc(100vh - 200px)";
    container.style.overflowY = "auto";
  }
});