const profileForm = document.querySelector("#profileForm");
const chatForm = document.querySelector("#chatForm");
const messageInput = document.querySelector("#messageInput");
const messages = document.querySelector("#messages");
const sendButton = document.querySelector("#sendButton");
const statusPill = document.querySelector("#statusPill");
const sourceChips = document.querySelector("#sourceChips");

const surplusEl = document.querySelector("#surplus");
const targetEl = document.querySelector("#target");
const rateEl = document.querySelector("#rate");
const spentBar = document.querySelector("#spentBar");

const chatHistory = [];

function money(value) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(Number.isFinite(value) ? value : 0);
}

function percent(value) {
  return `${Number.isFinite(value) ? value.toFixed(1) : "0.0"}%`;
}

function getProfile() {
  const data = new FormData(profileForm);
  return Object.fromEntries(data.entries());
}

function updateMetrics() {
  const profile = getProfile();
  const income = Number(profile.monthlyIncome || 0);
  const fixed = Number(profile.fixedExpenses || 0);
  const flexible = Number(profile.flexibleExpenses || 0);
  const goal = Number(profile.goalAmount || 0);
  const months = Math.max(Number(profile.months || 1), 1);
  const spending = fixed + flexible;
  const surplus = income - spending;
  const target = goal > 0 ? goal / months : 0;
  const rate = income > 0 ? (surplus / income) * 100 : 0;
  const spent = income > 0 ? Math.min(Math.max((spending / income) * 100, 0), 100) : 0;

  surplusEl.textContent = money(surplus);
  targetEl.textContent = money(target);
  rateEl.textContent = percent(rate);
  spentBar.style.width = `${spent}%`;
}

function addMessage(role, content) {
  const article = document.createElement("article");
  article.className = `message ${role}`;

  const avatar = document.createElement("div");
  avatar.className = "avatar";
  avatar.textContent = role === "user" ? "You" : "AI";

  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.textContent = content;

  article.append(avatar, bubble);
  messages.append(article);
  messages.scrollTop = messages.scrollHeight;
}

function renderSources(sources) {
  sourceChips.replaceChildren();
  for (const source of sources || []) {
    const chip = document.createElement("span");
    chip.className = "source-chip";
    chip.textContent = source.title;
    sourceChips.append(chip);
  }
}

async function checkHealth() {
  try {
    const response = await fetch("/api/health");
    const data = await response.json();
    statusPill.textContent = data.has_api_key ? `OpenAI ${data.model}` : "offline demo";
    statusPill.classList.toggle("offline", !data.has_api_key);
  } catch {
    statusPill.textContent = "server issue";
    statusPill.classList.add("offline");
  }
}

profileForm.addEventListener("input", updateMetrics);

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = messageInput.value.trim();
  if (!message) return;

  messageInput.value = "";
  addMessage("user", message);
  chatHistory.push({ role: "user", content: message });
  sendButton.disabled = true;
  sendButton.textContent = "Thinking";

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message,
        profile: getProfile(),
        history: chatHistory,
      }),
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || "Request failed");
    }

    addMessage("assistant", data.answer);
    chatHistory.push({ role: "assistant", content: data.answer });
    renderSources(data.sources);
    statusPill.textContent = data.mode === "openai" ? `OpenAI ${data.model}` : "offline demo";
    statusPill.classList.toggle("offline", data.mode !== "openai");
    if (data.apiError) {
      console.warn("OpenAI fallback reason:", data.apiError);
    }
  } catch (error) {
    addMessage("assistant", `Something went wrong: ${error.message}`);
  } finally {
    sendButton.disabled = false;
    sendButton.textContent = "Send";
    messageInput.focus();
  }
});

updateMetrics();
checkHealth();
