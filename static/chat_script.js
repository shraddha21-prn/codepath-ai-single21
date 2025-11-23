const chatBox = document.getElementById("chat-box");
const userInput = document.getElementById("user-input");

async function sendMessage() {
    const userMessage = userInput.value.trim();
    if (!userMessage) return;

    appendMessage("user", userMessage);
    userInput.value = "";

    appendMessage("ai", "⏳ Thinking...");

    try {
        const res = await fetch("/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ prompt: userMessage })
        });

        const data = await res.json();
        chatBox.lastChild.textContent = data.reply || "⚠️ Error generating response.";
    } catch (err) {
        chatBox.lastChild.textContent = "⚠️ Network error!";
    }
}

function appendMessage(sender, text) {
    const msg = document.createElement("div");
    msg.classList.add("message", sender);
    msg.textContent = text;
    chatBox.appendChild(msg);
    chatBox.scrollTop = chatBox.scrollHeight;
}
