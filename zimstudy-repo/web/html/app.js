// ZIMStudy AI — Web Edition frontend. Vanilla JS, no build step.

const screens = {};
document.querySelectorAll(".screen").forEach((el) => {
  screens[el.id.replace("screen-", "")] = el;
});
const mainNav = document.getElementById("main-nav");

function showScreen(name) {
  Object.values(screens).forEach((s) => s.classList.add("hidden"));
  screens[name].classList.remove("hidden");
  mainNav.classList.toggle("hidden", name === "onboarding" || name === "timer");
}

async function api(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const text = await res.text();
  const data = text ? JSON.parse(text) : null;
  if (!res.ok) {
    const err = new Error(data?.error || `API error ${res.status}`);
    err.status = res.status;
    err.data = data;
    throw err;
  }
  return data;
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str ?? "";
  return div.innerHTML;
}

// ---------- Navigation ----------

document.querySelectorAll("[data-nav]").forEach((btn) => {
  btn.addEventListener("click", () => goTo(btn.dataset.nav));
});

async function goTo(target) {
  const loaders = {
    dashboard: loadDashboard,
    subjects: loadSubjectsScreen,
    library: loadLibraryScreen,
    teacher: loadTeacherScreen,
    quiz: loadQuizScreen,
    examiner: loadExaminerScreen,
    progress: loadProgressScreen,
    mastery: loadMasteryScreen,
    report: loadReportScreen,
    agenda: loadAgendaScreen,
  };
  if (loaders[target]) await loaders[target]();
  else showScreen(target);
}

// ---------- Onboarding ----------

document.getElementById("onboarding-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  await api("/api/profile", {
    method: "POST",
    body: JSON.stringify({
      name: document.getElementById("ob-name").value || "Student",
      school: document.getElementById("ob-school").value,
      grade: document.getElementById("ob-grade").value,
      exam_board: document.getElementById("ob-board").value,
      exam_year: document.getElementById("ob-year").value,
    }),
  });
  await loadDashboard();
});

// ---------- Dashboard ----------

async function loadDashboard() {
  const [profile, subjects, exams, schedule, progress] = await Promise.all([
    api("/api/profile"),
    api("/api/subjects"),
    api("/api/exams"),
    api("/api/schedule/today").catch(() => null),
    api("/api/progress").catch(() => null),
  ]);

  document.getElementById("welcome-text").textContent = `Welcome back, ${profile?.name || "Student"}`;

  const examInfo = document.getElementById("exam-info");
  if (exams.length > 0) {
    const next = exams.slice().sort((a, b) => new Date(a.exam_date) - new Date(b.exam_date))[0];
    const days = Math.max(0, Math.ceil((new Date(next.exam_date) - new Date()) / 86400000));
    examInfo.innerHTML = `<strong>${escapeHtml(next.subject_name)}${
      next.paper_number ? " — Paper " + escapeHtml(next.paper_number) : ""
    }</strong><br/>${days} days remaining`;
  } else {
    examInfo.textContent = "No exam dates added yet.";
  }

  const missionInfo = document.getElementById("mission-info");
  if (schedule && schedule.mission) {
    missionInfo.innerHTML = `<strong>${escapeHtml(schedule.mission.subject)} — ${escapeHtml(
      schedule.mission.topic
    )}</strong><br/><span class="small">${escapeHtml(schedule.mission.reason)}</span>`;
  } else {
    missionInfo.textContent = "Add subjects and quiz activity to get a suggestion.";
  }

  const list = document.getElementById("subjects-list");
  list.innerHTML = "";
  if (subjects.length === 0) {
    list.innerHTML = `<p class="muted">No subjects yet. Tap "Manage Subjects" to add some.</p>`;
  } else {
    subjects.forEach((s) => {
      const card = document.createElement("div");
      card.className = "subject-card";
      card.innerHTML = `
        <div>
          <div class="name">${escapeHtml(s.name)}</div>
          <div class="target">Target: ${escapeHtml(s.target_grade)}</div>
        </div>
        <button class="btn primary">Start</button>
      `;
      card.querySelector("button").addEventListener("click", () => startTimer(s.name, "Focused session"));
      list.appendChild(card);
    });
  }

  if (progress) {
    document.getElementById("dashboard-kpis").innerHTML = [
      ["Today", `${progress.today.minutes}m`],
      ["Study streak", `${progress.streak}d`],
      ["This week", `${progress.week.minutes}m`],
      ["Weak areas", progress.weak_areas.length]
    ].map(([label, value]) => `<div class="kpi card"><div class="label">${label}</div><strong>${value}</strong></div>`).join("");
  }

  showScreen("dashboard");
}

document.getElementById("exam-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  await api("/api/exams", {
    method: "POST",
    body: JSON.stringify({
      subject_name: document.getElementById("exam-subject").value,
      paper_number: document.getElementById("exam-paper").value,
      exam_date: document.getElementById("exam-date").value,
    }),
  });
  e.target.reset();
  await loadDashboard();
});

// ---------- Subjects management ----------

async function loadSubjectsScreen() {
  document.getElementById("subject-error").classList.add("hidden");
  const subjects = await api("/api/subjects");
  const list = document.getElementById("subject-manage-list");
  list.innerHTML = "";
  subjects.forEach((s) => {
    const li = document.createElement("li");
    li.innerHTML = `<span>${escapeHtml(s.name)}</span><button>Remove</button>`;
    li.querySelector("button").addEventListener("click", async () => {
      await api(`/api/subjects/${s.id}`, { method: "DELETE" });
      await loadSubjectsScreen();
    });
    list.appendChild(li);
  });
  showScreen("subjects");
}

document.getElementById("subject-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const input = document.getElementById("new-subject");
  const errBox = document.getElementById("subject-error");
  errBox.classList.add("hidden");
  if (!input.value.trim()) return;
  try {
    await api("/api/subjects", { method: "POST", body: JSON.stringify({ name: input.value.trim() }) });
    input.value = "";
    await loadSubjectsScreen();
  } catch (err) {
    errBox.textContent = err.message;
    errBox.classList.remove("hidden");
  }
});

// ---------- Timer + Focus Mode ----------

let timerInterval = null;
let secondsElapsed = 0;
let timerRunning = true;
let timerSubject = "";
let timerTopic = "";
let interruptionCount = 0;

function startTimer(subject, topic) {
  timerSubject = subject;
  timerTopic = topic;
  secondsElapsed = 0;
  timerRunning = true;
  interruptionCount = 0;
  document.getElementById("timer-subject").textContent = subject;
  document.getElementById("timer-topic").textContent = topic;
  document.getElementById("timer-pause").textContent = "Pause";
  document.getElementById("timer-complete-state").classList.add("hidden");
  updateClock();
  updateInterruptionDisplay();

  api("/api/focus-events", { method: "POST", body: JSON.stringify({ event_type: "session_start", note: subject }) });

  clearInterval(timerInterval);
  timerInterval = setInterval(() => {
    if (timerRunning) {
      secondsElapsed++;
      updateClock();
    }
  }, 1000);

  showScreen("timer");
}

function updateClock() {
  const m = String(Math.floor(secondsElapsed / 60)).padStart(2, "0");
  const s = String(secondsElapsed % 60).padStart(2, "0");
  document.getElementById("timer-clock").textContent = `${m}:${s}`;
}

function updateInterruptionDisplay() {
  const el = document.getElementById("timer-interruptions");
  el.textContent = interruptionCount > 0 ? `${interruptionCount} interruption(s) detected` : "";
}

// Focus Mode: count it as an interruption if the user switches away from
// this tab while a session is actively running (spec section 19).
document.addEventListener("visibilitychange", () => {
  if (screens.timer.classList.contains("hidden")) return;
  if (document.hidden && timerRunning) {
    interruptionCount++;
    updateInterruptionDisplay();
    api("/api/focus-events", { method: "POST", body: JSON.stringify({ event_type: "interruption" }) });
  }
});

document.getElementById("timer-pause").addEventListener("click", (e) => {
  timerRunning = !timerRunning;
  e.target.textContent = timerRunning ? "Pause" : "Resume";
  api("/api/focus-events", {
    method: "POST",
    body: JSON.stringify({ event_type: timerRunning ? "resume" : "pause" }),
  });
});

document.getElementById("timer-complete").addEventListener("click", async () => {
  clearInterval(timerInterval);
  const minutes = Math.max(1, Math.round(secondsElapsed / 60));
  await api("/api/sessions", {
    method: "POST",
    body: JSON.stringify({
      subject_name: timerSubject,
      topic: timerTopic,
      duration_minutes: minutes,
      interruptions: interruptionCount,
    }),
  });
  await api("/api/focus-events", { method: "POST", body: JSON.stringify({ event_type: "session_end" }) });
  document.getElementById("timer-complete-state").innerHTML = `<div class="label">SESSION SAVED</div><h2>${minutes} minutes locked in</h2><p class="muted">${escapeHtml(timerSubject)} · ${escapeHtml(timerTopic)}</p><button class="btn primary" id="timer-done">Back to dashboard</button>`;
  document.getElementById("timer-complete-state").classList.remove("hidden");
  document.getElementById("timer-done").onclick = loadDashboard;
});

document.getElementById("timer-cancel").addEventListener("click", async () => {
  clearInterval(timerInterval);
  await loadDashboard();
});

// ---------- Library (documents) ----------

async function loadLibraryScreen() {
  document.getElementById("doc-search-results").innerHTML = "";
  document.getElementById("doc-upload-status").textContent = "";
  const docs = await api("/api/documents");
  renderDocumentsList(docs);
  showScreen("library");
}

function renderDocumentsList(docs) {
  const list = document.getElementById("documents-list");
  list.innerHTML = "";
  if (docs.length === 0) {
    list.innerHTML = `<p class="muted">No documents yet.</p>`;
    return;
  }
  docs.forEach((d) => {
    const li = document.createElement("li");
    const meta = [d.doc_type, d.subject, d.page_count ? `${d.page_count}p` : null].filter(Boolean).join(" · ");
    li.innerHTML = `<span><strong>${escapeHtml(d.title)}</strong><br/><span class="small muted">${escapeHtml(meta)}</span></span><button>Remove</button>`;
    li.querySelector("button").addEventListener("click", async () => {
      await api(`/api/documents/${d.id}`, { method: "DELETE" });
      await loadLibraryScreen();
    });
    list.appendChild(li);
  });
}

function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result.split(",")[1]);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

document.getElementById("doc-upload-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const status = document.getElementById("doc-upload-status");
  const fileInput = document.getElementById("doc-file");
  const file = fileInput.files[0];
  if (!file) return;

  status.textContent = "Uploading and extracting text...";
  try {
    const content_b64 = await fileToBase64(file);
    const result = await api("/api/documents", {
      method: "POST",
      body: JSON.stringify({
        title: document.getElementById("doc-title").value,
        doc_type: document.getElementById("doc-type").value,
        subject: document.getElementById("doc-subject").value,
        filename: file.name,
        content_b64,
      }),
    });
    status.textContent = `Added — extracted ${result.extracted_chars} characters from ${result.pages} page(s).`;
    e.target.reset();
    const docs = await api("/api/documents");
    renderDocumentsList(docs);
  } catch (err) {
    status.textContent = `Error: ${err.message}`;
  }
});

document.getElementById("doc-paste-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  await api("/api/documents", {
    method: "POST",
    body: JSON.stringify({
      title: document.getElementById("paste-title").value,
      doc_type: "notes",
      subject: document.getElementById("paste-subject").value,
      text: document.getElementById("paste-text").value,
    }),
  });
  e.target.reset();
  const docs = await api("/api/documents");
  renderDocumentsList(docs);
});

document.getElementById("youtube-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  await api("/api/youtube/transcript", {
    method: "POST",
    body: JSON.stringify({
      url: document.getElementById("yt-url").value,
      subject: document.getElementById("yt-subject").value,
      transcript_text: document.getElementById("yt-transcript").value,
    }),
  });
  e.target.reset();
  const docs = await api("/api/documents");
  renderDocumentsList(docs);
});

document.getElementById("doc-search-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const q = document.getElementById("doc-search-query").value;
  const results = await api(`/api/documents/search?q=${encodeURIComponent(q)}`);
  const box = document.getElementById("doc-search-results");
  box.innerHTML = "";
  if (results.length === 0) {
    box.innerHTML = `<p class="muted small">No matches.</p>`;
    return;
  }
  results.forEach((r) => {
    const card = document.createElement("div");
    card.className = "card";
    card.innerHTML = `<strong>${escapeHtml(r.title)}</strong><div class="small muted">${r.excerpt}</div>`;
    box.appendChild(card);
  });
});

// ---------- AI Teacher (chat + voice) ----------

let chatHistory = [];

async function loadTeacherScreen() {
  const status = await api("/api/ai/status");
  document.getElementById("ai-offline-banner").classList.toggle("hidden", status.configured);
  showScreen("teacher");
}

function appendChatBubble(role, content) {
  const log = document.getElementById("chat-log");
  const bubble = document.createElement("div");
  bubble.className = `chat-bubble ${role}`;
  bubble.textContent = content;
  log.appendChild(bubble);
  log.scrollTop = log.scrollHeight;
}

async function sendChatMessage(message) {
  if (!message.trim()) return;
  appendChatBubble("user", message);
  chatHistory.push({ role: "user", content: message });

  const subject = document.getElementById("teacher-subject").value || "General";
  const topic = document.getElementById("teacher-topic").value || "";
  const useDocs = document.getElementById("teacher-use-docs").checked;

  try {
    const result = await api("/api/ai/chat", {
      method: "POST",
      body: JSON.stringify({ subject, topic, message, history: chatHistory.slice(0, -1), use_documents: useDocs }),
    });
    appendChatBubble("assistant", result.reply);
    chatHistory.push({ role: "assistant", content: result.reply });
    speak(result.reply);
  } catch (err) {
    document.getElementById("ai-offline-banner").classList.remove("hidden");
    appendChatBubble("assistant", err.data?.error || "AI Teacher is temporarily offline.");
  }
}

document.getElementById("chat-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const input = document.getElementById("chat-input");
  const message = input.value;
  input.value = "";
  await sendChatMessage(message);
});

// Voice: browser-native Web Speech API — no server/API key involved.
const SpeechRecognitionImpl = window.SpeechRecognition || window.webkitSpeechRecognition;
let recognizer = null;
if (SpeechRecognitionImpl) {
  recognizer = new SpeechRecognitionImpl();
  recognizer.lang = "en-US";
  recognizer.interimResults = false;
  recognizer.maxAlternatives = 1;

  recognizer.onresult = (event) => {
    const transcript = event.results[0][0].transcript;
    document.getElementById("chat-input").value = transcript;
    sendChatMessage(transcript);
  };
  recognizer.onend = () => document.getElementById("mic-btn").classList.remove("recording");
  recognizer.onerror = () => document.getElementById("mic-btn").classList.remove("recording");
}

document.getElementById("mic-btn").addEventListener("click", () => {
  if (!recognizer) {
    alert("Voice input isn't supported in this browser. Try Chrome or Edge.");
    return;
  }
  document.getElementById("mic-btn").classList.add("recording");
  recognizer.start();
});

function speak(text) {
  if (!window.speechSynthesis) return;
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.rate = 1.0;
  window.speechSynthesis.speak(utterance);
}

// ---------- Quiz / AI Examiner ----------

let quizQueue = [];
let quizIndex = 0;
let quizCorrect = 0;
let currentQuizItem = null;

async function loadQuizScreen() {
  document.getElementById("quiz-runner").classList.add("hidden");
  document.getElementById("quiz-complete").classList.add("hidden");
  document.getElementById("gen-quiz-status").textContent = "";
  showScreen("quiz");
}

document.getElementById("gen-quiz-btn").addEventListener("click", async () => {
  const status = document.getElementById("gen-quiz-status");
  const subject = document.getElementById("gen-subject").value;
  const topic = document.getElementById("gen-topic").value;
  if (!subject || !topic) {
    status.textContent = "Enter a subject and topic first.";
    return;
  }
  status.textContent = "Generating...";
  try {
    const result = await api("/api/ai/generate-quiz", {
      method: "POST",
      body: JSON.stringify({ subject, topic, difficulty: 2, count: 5, use_documents: true }),
    });
    status.textContent = `Added ${result.inserted} AI-generated questions.`;
  } catch (err) {
    status.textContent = err.data?.error || "AI Examiner is temporarily offline. Add questions manually below.";
  }
});

document.getElementById("quiz-add-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  await api("/api/quiz-items", {
    method: "POST",
    body: JSON.stringify({
      subject: document.getElementById("qa-subject").value,
      topic: document.getElementById("qa-topic").value,
      question: document.getElementById("qa-question").value,
      answer: document.getElementById("qa-answer").value,
    }),
  });
  e.target.reset();
});

document.getElementById("start-quiz-btn").addEventListener("click", async () => {
  const subject = document.getElementById("quiz-subject-filter").value;
  const url = subject ? `/api/quiz-items/next?subject=${encodeURIComponent(subject)}&count=8` : `/api/quiz-items/next?count=8`;
  quizQueue = await api(url);
  quizIndex = 0;
  quizCorrect = 0;
  document.getElementById("quiz-complete").classList.add("hidden");
  if (quizQueue.length === 0) {
    alert("No quiz questions yet — generate some with AI or add them manually above.");
    return;
  }
  document.getElementById("quiz-runner").classList.remove("hidden");
  showNextQuizItem();
});

// ---------- Formal Examiner ----------
let examQueue = [], examIndex = 0, examAnswers = [];

async function loadExaminerScreen() {
  document.getElementById("examiner-runner").classList.add("hidden");
  document.getElementById("examiner-complete").classList.add("hidden");
  document.getElementById("examiner-status").textContent = "";
  const results = await api("/api/examiner/results");
  const history = document.getElementById("examiner-history");
  history.innerHTML = results.length ? results.map(r =>
    `<div class="topic-row"><span><strong>${escapeHtml(r.subject)}</strong> · ${escapeHtml(r.topic || "")}<br><span class="small muted">${new Date(r.taken_at * 1000).toLocaleDateString()}</span></span><strong>${r.marks}/${r.total_marks} · ${r.percentage}%</strong></div>`
  ).join("") : '<p class="muted small">No formal assessments saved yet.</p>';
  showScreen("examiner");
}

document.getElementById("generate-exam-btn").addEventListener("click", async () => {
  const status = document.getElementById("examiner-status");
  const subject = document.getElementById("examiner-subject").value.trim();
  const topic = document.getElementById("examiner-topic").value.trim();
  if (!subject || !topic) { status.textContent = "Enter a subject and topic first."; return; }
  status.textContent = "Generating a formal assessment...";
  try {
    const result = await api("/api/ai/generate-exam", { method: "POST", body: JSON.stringify({
      subject, topic, difficulty: +document.getElementById("examiner-difficulty").value,
      count: +document.getElementById("examiner-count").value,
      use_documents: document.getElementById("examiner-use-docs").checked
    })});
    examQueue = result.questions; examIndex = 0; examAnswers = [];
    document.getElementById("examiner-setup").classList.add("hidden");
    document.getElementById("examiner-runner").classList.remove("hidden");
    renderExamQuestion();
  } catch (err) { status.textContent = err.data?.error || err.message; }
});

function renderExamQuestion() {
  const q = examQueue[examIndex];
  document.getElementById("examiner-progress").textContent = `Question ${examIndex + 1} of ${examQueue.length}`;
  document.getElementById("examiner-question").textContent = q.question;
  document.getElementById("examiner-options").innerHTML = q.options.map((option, i) =>
    `<button class="option-btn" data-option="${escapeHtml(option)}">${String.fromCharCode(65+i)}. ${escapeHtml(option)}</button>`
  ).join("");
  document.querySelectorAll(".option-btn").forEach(btn => btn.addEventListener("click", () => {
    document.querySelectorAll(".option-btn").forEach(b => b.classList.remove("selected"));
    btn.classList.add("selected");
  }));
  document.getElementById("examiner-next").textContent = examIndex === examQueue.length - 1 ? "Submit assessment" : "Next question";
}

document.getElementById("examiner-next").addEventListener("click", async () => {
  const selected = document.querySelector(".option-btn.selected");
  if (!selected) return;
  examAnswers.push(selected.dataset.option);
  examIndex++;
  if (examIndex < examQueue.length) { renderExamQuestion(); return; }
  const result = await api("/api/examiner/results", { method: "POST", body: JSON.stringify({
    subject: document.getElementById("examiner-subject").value,
    topic: document.getElementById("examiner-topic").value,
    difficulty: +document.getElementById("examiner-difficulty").value,
    questions: examQueue, answers: examAnswers
  })});
  document.getElementById("examiner-runner").classList.add("hidden");
  const complete = document.getElementById("examiner-complete");
  complete.classList.remove("hidden");
  complete.innerHTML = `<div class="label">ASSESSMENT SAVED</div><h2>${result.marks}/${result.total_marks} · ${result.percentage}%</h2><p>${escapeHtml(result.feedback)}</p><p class="muted">Weak areas: ${escapeHtml(result.weak_areas.join(", ") || "None identified")}</p><button class="btn primary" id="examiner-retake">Retake</button>`;
  document.getElementById("examiner-retake").onclick = () => {
    document.getElementById("examiner-complete").classList.add("hidden");
    document.getElementById("examiner-setup").classList.remove("hidden");
  };
});

// ---------- Progress ----------
async function loadProgressScreen() {
  const data = await api("/api/progress");
  document.getElementById("progress-kpis").innerHTML = [
    ["Today", `${data.today.minutes}m`], ["This week", `${Math.floor(data.week.minutes/60)}h ${data.week.minutes%60}m`],
    ["Sessions", data.week.sessions], ["Study streak", `${data.streak} day${data.streak === 1 ? "" : "s"}`]
  ].map(([label, value]) => `<div class="kpi card"><div class="label">${label}</div><strong>${value}</strong></div>`).join("");
  document.getElementById("progress-subjects").innerHTML = data.subjects.length ? data.subjects.map(s =>
    `<div class="progress-row"><span><strong>${escapeHtml(s.subject)}</strong><span class="small muted"> · ${s.confidence} confidence</span></span><span>${s.mastery}%</span><div class="mastery-bar-track"><div class="mastery-bar-fill" style="width:${s.mastery}%"></div></div></div>`
  ).join("") : '<p class="muted">Add subjects and complete practice to build progress.</p>';
  const areas = (id, items) => document.getElementById(id).innerHTML = items.length ? items.map(x => `<div class="topic-row"><span>${escapeHtml(x.subject)} · ${escapeHtml(x.topic)}</span><strong>${x.score}%</strong></div>`).join("") : '<p class="muted small">No evidence yet.</p>';
  areas("progress-weak", data.weak_areas); areas("progress-strong", data.strong_areas);
  document.getElementById("progress-results").innerHTML = data.recent_exams.length ? data.recent_exams.map(r => `<div class="topic-row"><span>${escapeHtml(r.subject)} · ${escapeHtml(r.topic || "")}</span><strong>${r.percentage}%</strong></div>`).join("") : '<p class="muted small">Complete an Examiner assessment to see results.</p>';
  showScreen("progress");
}

function showNextQuizItem() {
  if (quizIndex >= quizQueue.length) {
    document.getElementById("quiz-runner").classList.add("hidden");
    document.getElementById("quiz-complete").classList.remove("hidden");
    document.getElementById("quiz-summary").textContent =
      `${quizCorrect}/${quizQueue.length} correct (${Math.round((100 * quizCorrect) / quizQueue.length)}%).`;
    return;
  }
  currentQuizItem = quizQueue[quizIndex];
  document.getElementById("quiz-progress").textContent = `Question ${quizIndex + 1} of ${quizQueue.length}`;
  document.getElementById("quiz-question").textContent = currentQuizItem.question;
  const answerBox = document.getElementById("quiz-answer");
  answerBox.textContent = currentQuizItem.answer || "(no answer recorded)";
  answerBox.classList.add("hidden");
}

document.getElementById("quiz-reveal").addEventListener("click", () => {
  document.getElementById("quiz-answer").classList.remove("hidden");
});

async function answerQuiz(correct) {
  if (correct) quizCorrect++;
  await api("/api/quiz-attempts", {
    method: "POST",
    body: JSON.stringify({ quiz_item_id: currentQuizItem.id, correct }),
  });
  quizIndex++;
  showNextQuizItem();
}

document.getElementById("quiz-right").addEventListener("click", () => answerQuiz(true));
document.getElementById("quiz-wrong").addEventListener("click", () => answerQuiz(false));

// ---------- Mastery / Forecast ----------

async function loadMasteryScreen() {
  const { forecasts, tally } = await api("/api/forecast");

  const tallyBox = document.getElementById("forecast-tally");
  tallyBox.innerHTML = Object.entries(tally)
    .map(([grade, count]) => `<span class="tally-chip">${escapeHtml(grade)}: ${count}</span>`)
    .join("");

  const list = document.getElementById("mastery-list");
  list.innerHTML = "";
  if (forecasts.length === 0) {
    list.innerHTML = `<p class="muted">Add subjects to see mastery and forecasts.</p>`;
  }
  forecasts.forEach((f) => {
    const card = document.createElement("div");
    card.className = "mastery-card";
    const topics = Object.entries(f.topic_breakdown)
      .map(([topic, pct]) => `<div class="topic-row"><span>${escapeHtml(topic)}</span><span>${pct}%</span></div>`)
      .join("");
    card.innerHTML = `
      <div class="topbar">
        <strong>${escapeHtml(f.subject)}</strong>
        <span>Predicted: <strong>${escapeHtml(f.predicted_grade)}</strong> (${escapeHtml(f.confidence)} confidence)</span>
      </div>
      <div class="small muted">ESTIMATED MASTERY: ${f.estimated_mastery}%</div>
      <div class="mastery-bar-track"><div class="mastery-bar-fill" style="width:${f.estimated_mastery}%"></div></div>
      ${topics}
      ${f.what_would_change_forecast ? `<p class="small">${escapeHtml(f.what_would_change_forecast)}</p>` : ""}
    `;
    list.appendChild(card);
  });

  showScreen("mastery");
}

// ---------- Weekly Report ----------

async function loadReportScreen() {
  const report = await api("/api/weekly-report");
  const box = document.getElementById("report-content");
  const hours = Math.floor(report.total_minutes / 60);
  const mins = report.total_minutes % 60;
  const subjectRows = report.subjects
    .map((s) => `<div class="topic-row"><span>${escapeHtml(s.subject)}</span><span>${s.mastery}%</span></div>`)
    .join("");

  box.innerHTML = `
    <p>${escapeHtml(report.narrative)}</p>
    <div class="label">THIS WEEK</div>
    <div class="topic-row"><span>Focused study</span><span>${hours}h ${mins}m</span></div>
    <div class="topic-row"><span>Quiz accuracy</span><span>${report.quiz_accuracy ?? "—"}%</span></div>
    <div class="topic-row"><span>Study Quality</span><span>${report.study_quality.score}/100</span></div>
    <div class="label" style="margin-top:16px">BY SUBJECT</div>
    ${subjectRows || '<p class="muted small">No subjects yet.</p>'}
  `;
  showScreen("report");
}

// ---------- Weekly Agenda ----------

async function loadAgendaScreen() {
  const goals = await api("/api/weekly-goals");
  const list = document.getElementById("goals-list");
  list.innerHTML = "";
  if (goals.length === 0) {
    list.innerHTML = `<p class="muted">No weekly goals yet.</p>`;
  }
  goals.forEach((g) => {
    const li = document.createElement("li");
    li.innerHTML = `<span><strong>${escapeHtml(g.subject)}</strong> — ${escapeHtml(g.topic)} <span class="small muted">(target ${g.target_mastery}%)</span></span><button>Remove</button>`;
    li.querySelector("button").addEventListener("click", async () => {
      await api(`/api/weekly-goals/${g.id}`, { method: "DELETE" });
      await loadAgendaScreen();
    });
    list.appendChild(li);
  });
  showScreen("agenda");
}

document.getElementById("goal-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  await api("/api/weekly-goals", {
    method: "POST",
    body: JSON.stringify({
      subject: document.getElementById("goal-subject").value,
      topic: document.getElementById("goal-topic").value,
      target_mastery: parseInt(document.getElementById("goal-target").value || "90", 10),
    }),
  });
  e.target.reset();
  await loadAgendaScreen();
});

// ---------- Boot ----------

(async function init() {
  const profile = await api("/api/profile");
  if (profile) {
    await loadDashboard();
  } else {
    showScreen("onboarding");
  }
})();
