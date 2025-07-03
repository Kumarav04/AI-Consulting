document.querySelectorAll('.use-case').forEach(box => {
  box.addEventListener('click', () => {
    // Redirect to chatbot for that use case
    window.location.href = ''; // Update this path as needed
  });
});

document.getElementById("uploadForm").addEventListener("submit", function (e) {
  e.preventDefault();
  const file = document.getElementById("fileInput").files[0];
  if (file) {
    document.getElementById("uploadStatus").textContent = `Selected: ${file.name}`;
    // Upload logic here
  }
});

document.getElementById("chatForm").addEventListener("submit", function (e) {
  e.preventDefault();
  const input = document.getElementById("chatInput");
  const message = input.value.trim();
  if (message) {
    const chatWindow = document.getElementById("chatWindow");
    const msgDiv = document.createElement("div");
    msgDiv.textContent = "You: " + message;
    chatWindow.appendChild(msgDiv);
    chatWindow.scrollTop = chatWindow.scrollHeight;
    input.value = "";
    // Chat API call goes here
  }
});
