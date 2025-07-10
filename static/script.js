// ---------------------------------------------------------
//  script.js — shared client logic
// ---------------------------------------------------------
console.log("🔗 script.js connected");

/* ---------- 0. shared helpers ---------- */
const SESSION_KEY = "consultbot-session-id";
if (!localStorage.getItem(SESSION_KEY)) localStorage.setItem(SESSION_KEY, crypto.randomUUID());
const addSession = (h = {}) => ({ ...h, "X-Session-ID": localStorage.getItem(SESSION_KEY) });

function formatGPT(txt) {              // very light markdown → HTML
  return txt
    .replace(/\b\w+\.png\b/g, "")
    .replace(/^###\s*(.+)$/gm, "<h3>$1</h3>")
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/^- /gm, "• ")
    .replace(/\n+/g, "<br>")
    .trim();
}

/* ---------- 1. landing-page routing ---------- */
document.querySelectorAll(".use-case").forEach(box => {
  box.addEventListener("click", () => {
    const uc = encodeURIComponent(box.dataset.usecase || "");
    window.location.href = `/chat.html?use_case=${uc}`;
  });
});

/* ---------- 2. chatbot page ---------- */
if (document.querySelector(".chatbot-panel")) {
  // 2-A) use-case context
  const params   = new URLSearchParams(window.location.search);
  const USE_CASE = params.get("use_case") || "General";
  document.title = `ConsultBot – ${USE_CASE}`;           
  ["uc-header", "uc-subhead", "uc-flow"].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.textContent = USE_CASE;                  
  });

  // 2-B) stage flags
  const chartsPanel = document.getElementById("chartsPanel");
  let fileUploaded   = false;   // user provided a dataset?
  let goalsCollected = false;   // user has told us their goals?

  const chatWindow = document.getElementById("chatWindow");
  const appendMsg  = (role, html) => {
    const div  = document.createElement("div");
    div.innerHTML = `<strong>${role}:</strong> ${html}`;
    chatWindow.appendChild(div);
    chatWindow.scrollTop = chatWindow.scrollHeight;
  };

  /* ---------- 2-C) upload pipeline ---------- */
  document.getElementById("uploadForm")
    .addEventListener("submit", async (e) => {
      e.preventDefault();
      const fileInput = document.getElementById("fileInput");
      const file      = fileInput.files[0];
      const status    = document.getElementById("uploadStatus");
      if (!file) { status.textContent = "Please choose a file."; return; }

      status.textContent = `Uploading ${file.name} …`;
      const formData = new FormData();
      formData.append("file", file);

      try {
        const res = await fetch(`/upload?use_case=${encodeURIComponent(USE_CASE)}`, {
          method: "POST",
          body: formData,
          headers: addSession()
        });
        if (!res.ok) throw new Error(`Server responded ${res.status}`);
        const data = await res.json();
        if (data.session_id) {
          localStorage.setItem(SESSION_KEY, data.session_id);
        }

        status.textContent = "File received ✅";
        fileUploaded = true;

        // prompt user for goals
        appendMsg("Bot", "Thanks! What specific questions or goals do you have for this dataset?");
      } catch (err) { status.textContent = `❌ ${err.message}`; }
    });

  /* ---------- 2-D) chat pipeline ---------- */
  document.getElementById("chatForm")
    .addEventListener("submit", async (e) => {
      e.preventDefault();
      const input    = document.getElementById("chatInput");
      const message  = input.value.trim();
      if (!message) return;
      input.value = "";

      appendMsg("You", message);

      // gate: have they uploaded a file yet?
      if (!fileUploaded) {
        appendMsg("Bot", "Please upload a file first so I can analyse it.");
        return;
      }

      // first user reply after upload = goals
      const stage = goalsCollected ? "follow_up" : "user_goals";
      goalsCollected = true;

      // placeholder while waiting
      const waitDiv = document.createElement("div");
      waitDiv.innerHTML = "<em>ConsultBot is thinking…</em>";
      chatWindow.appendChild(waitDiv);
      chatWindow.scrollTop = chatWindow.scrollHeight;

      try {
        const res = await fetch("/chat", {
          method : "POST",
          headers: addSession({ "Content-Type": "application/json",
                                "X-Use-Case"  : USE_CASE,
                                "X-Chat-Stage": stage }),
          body   : JSON.stringify({ prompt: message })
        });
        if (!res.ok) throw new Error(`Server ${res.status}`);

        const data = await res.json();   // backend returns { reply, charts? }

        // charts appear only after goals have been supplied
        if (data.chart_paths?.length) {
          chartsPanel.innerHTML = "";             // clear old charts
          data.chart_paths.forEach(p => {
            const img = document.createElement("img");
            img.src = `/generated/${p}`;
            img.alt = p;
            chartsPanel.appendChild(img);         
          });
        }        

        waitDiv.innerHTML = formatGPT(data.reply);
      } catch (err) {
        waitDiv.textContent = `Error: ${err.message}`;
      }
    });
}


window.addEventListener("DOMContentLoaded", () => {
  document.body.classList.remove("preload");
});
