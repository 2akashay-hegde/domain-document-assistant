document.addEventListener("DOMContentLoaded", () => {
    loadDocuments();
    initAutoDeleteSetting();
    initThemeSetting();
});

function changeTheme(themeName) {
    document.documentElement.setAttribute("data-theme", themeName);
    localStorage.setItem("userAppTheme", themeName);
}

function initThemeSetting() {
    const savedTheme = localStorage.getItem("userAppTheme") || "pure-white";
    document.documentElement.setAttribute("data-theme", savedTheme);
    const themeSelect = document.getElementById("themeSelect");
    if (themeSelect) themeSelect.value = savedTheme;
}

// Auto-delete documents on exit
function initAutoDeleteSetting() {
    const toggle = document.getElementById("autoDeleteToggle");
    if (toggle) {
        const savedSetting = localStorage.getItem("autoDeleteOnClose");
        // Enabled by default unless explicitly set to false
        toggle.checked = savedSetting !== "false";
    }
}

function toggleAutoDelete(checkbox) {
    localStorage.setItem("autoDeleteOnClose", checkbox.checked ? "true" : "false");
}

function handleAutoDeleteOnClose() {
    const isAutoDeleteEnabled = localStorage.getItem("autoDeleteOnClose") !== "false";
    if (isAutoDeleteEnabled) {
        // Send async beacon request to clear documents as window/tab closes
        navigator.sendBeacon("/documents/clear");
    }
}

window.addEventListener("pagehide", handleAutoDeleteOnClose);
window.addEventListener("beforeunload", handleAutoDeleteOnClose);


// Markdown formatter function for clean structured text output layout
function formatMarkdown(text) {
    if (!text) return "";
    
    // Code blocks ``` ... ```
    text = text.replace(/```([\s\S]*?)```/g, (match, code) => {
        const escaped = code.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
        return `<pre class="code-block"><code>${escaped.trim()}</code></pre>`;
    });

    // Inline code `code`
    text = text.replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>');

    // Bold text **text**
    text = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

    // Blockquotes > text
    text = text.replace(/^>\s?(.*)$/gm, '<blockquote class="output-quote">$1</blockquote>');

    // Key-value metadata lines (e.g. - Format: PNG)
    text = text.replace(/^-\s([A-Za-z0-9\s()]+):\s(.*)$/gm, '<div class="kv-item"><span class="kv-key">$1:</span> <span class="kv-val">$2</span></div>');
    text = text.replace(/^-\s(.*)$/gm, '<div class="list-bullet"><span class="bullet-dot">•</span> <span>$1</span></div>');

    // Headers ### Title
    text = text.replace(/^### (.*$)/gm, '<h3 class="output-h3">$1</h3>');
    text = text.replace(/^## (.*$)/gm, '<h2 class="output-h2">$1</h2>');

    // Line breaks & paragraph gaps
    text = text.replace(/\n\n/g, '<div class="para-gap"></div>');
    text = text.replace(/\n/g, '<br>');
    
    return text;
}

async function loadDocuments() {
    const docList = document.getElementById("docList");
    const docScopeSelect = document.getElementById("docScope");

    const isImageFile = (filename) => {
        const ext = filename.split('.').pop().toLowerCase();
        return ["png", "jpg", "jpeg", "webp", "bmp", "tiff", "svg"].includes(ext);
    };

    try {
        const res = await fetch("/documents");
        const data = await res.json();
        
        if (data.documents && data.documents.length > 0) {
            docList.innerHTML = data.documents.map(d => {
                const icon = isImageFile(d.source) ? '🖼️' : '📄';
                return `
                <div class="doc-item">
                    <span class="doc-title" title="${d.source}">${icon} ${d.title}</span>
                    <div class="doc-item-actions">
                        <span class="doc-chunks">${d.chunk_count} ${d.chunk_count === 1 ? 'chunk' : 'chunks'}</span>
                        <button class="delete-btn" title="Delete File" onclick="deleteDocument('${d.source}')">🗑️</button>
                    </div>
                </div>
                `;
            }).join("");

            // Update Scope Dropdown
            let scopeOptions = `<option value="all">🌐 All Ingested Knowledge (${data.documents.length})</option>`;
            data.documents.forEach(d => {
                const icon = isImageFile(d.source) ? '🖼️' : '📄';
                scopeOptions += `<option value="${d.source}">${icon} ${d.title} (${d.source})</option>`;
            });
            docScopeSelect.innerHTML = scopeOptions;

        } else {
            docList.innerHTML = `<div style="font-size: 0.85rem; color: var(--text-muted);">No documents or images ingested yet.</div>`;
            docScopeSelect.innerHTML = `<option value="all">🌐 All Ingested Knowledge (0)</option>`;
        }
    } catch (err) {
        docList.innerHTML = `<div style="font-size: 0.85rem; color: #ef4444;">Failed to load knowledge base</div>`;
    }
}

async function deleteDocument(docSource) {
    if (!confirm(`Are you sure you want to delete "${docSource}" from the knowledge base?`)) return;

    try {
        const res = await fetch(`/documents/${encodeURIComponent(docSource)}`, { method: "DELETE" });
        if (res.ok) {
            appendMessage("bot", `🗑️ Deleted <strong>${docSource}</strong> from knowledge base.`);
            loadDocuments();
        } else {
            alert("Failed to delete document.");
        }
    } catch (err) {
        alert(`Error deleting document: ${err.message}`);
    }
}

async function clearAllDocuments() {
    if (!confirm("Are you sure you want to delete ALL uploaded documents from the knowledge base?")) return;

    try {
        const res = await fetch("/documents/clear", { method: "POST" });
        if (res.ok) {
            appendMessage("bot", "🧹 All uploaded documents cleared from knowledge base.");
            loadDocuments();
        } else {
            alert("Failed to clear documents.");
        }
    } catch (err) {
        alert(`Error clearing documents: ${err.message}`);
    }
}


async function uploadFile() {
    const input = document.getElementById("fileInput");
    if (!input.files || input.files.length === 0) return;

    const filename = input.files[0].name;
    appendMessage("bot", `Uploading and indexing <strong>${filename}</strong>...`);

    const formData = new FormData();
    formData.append("file", input.files[0]);

    try {
        const res = await fetch("/upload", { method: "POST", body: formData });
        const result = await res.json();
        if (res.ok) {
            appendMessage("bot", `✅ Successfully indexed <strong>${result.filename}</strong> (${result.chunks_processed} chunks generated).`);
            loadDocuments();
        } else {
            appendMessage("bot", `❌ Ingestion failed: ${result.detail || "Error"}`);
        }
    } catch (err) {
        appendMessage("bot", `❌ Error uploading file: ${err.message}`);
    }
    input.value = "";
}

async function triggerDirectoryIngest() {
    appendMessage("bot", "Scanning <code>data/raw_docs/</code> for new documents...");
    try {
        const res = await fetch("/ingest", { method: "POST" });
        const data = await res.json();
        appendMessage("bot", `✅ Directory ingestion complete. Processed ${data.results.length} files.`);
        loadDocuments();
    } catch (err) {
        appendMessage("bot", `❌ Failed to ingest directory: ${err.message}`);
    }
}

function handleKeyPress(e) {
    if (e.key === "Enter") sendMessage();
}

async function sendMessage() {
    const input = document.getElementById("userInput");
    const question = input.value.trim();
    if (!question) return;

    const docScopeSelect = document.getElementById("docScope");
    const selectedScope = docScopeSelect ? docScopeSelect.value : "all";
    const langSelect = document.getElementById("langSelect");
    const selectedLang = langSelect ? langSelect.value : "auto";

    appendMessage("user", question);
    input.value = "";

    const loadingId = appendMessage("bot", "Searching knowledge base and formulating answer...");

    try {
        const res = await fetch("/ask", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                question: question,
                top_k: 5,
                document_source: selectedScope,
                target_language: selectedLang
            })
        });

        const data = await res.json();
        removeMessage(loadingId);

        let formattedAnswer = formatMarkdown(data.answer);

        // Render sources if available
        let sourcesHtml = "";
        if (data.sources && data.sources.length > 0) {
            const isImageFile = (filename) => {
                const ext = filename.split('.').pop().toLowerCase();
                return ["png", "jpg", "jpeg", "webp", "bmp", "tiff", "svg"].includes(ext);
            };

            const sourcePills = data.sources.map(s => {
                const icon = isImageFile(s.source) ? '🖼️' : '📄';
                return `<span style="background: #eef2ff; border: 1px solid #c7d2fe; color: #4338ca; padding: 4px 10px; border-radius: 8px; font-size: 0.85rem; font-weight: 600;">
                    ${icon} ${s.source} ${s.page ? `(Page ${s.page})` : ''} • ${(s.similarity_score * 100).toFixed(1)}% match
                </span>`;
            }).join(" ");

            sourcesHtml = `
                <div class="sources-section">
                    <div style="font-size: 0.8rem; color: #64748b; font-weight: 700; margin-bottom: 8px;">SOURCE KNOWLEDGE:</div>
                    <div style="display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 10px;">
                        ${sourcePills}
                    </div>
                    <div class="sources-toggle" onclick="toggleSources(this)">
                        🔍 View Extracted Text Snippets ▶
                    </div>
                    <div class="sources-content" style="display:none; flex-direction:column; gap:8px; margin-top:8px;">
                        ${data.sources.map(s => {
                            const icon = isImageFile(s.source) ? '🖼️' : '📄';
                            return `
                            <div class="source-card">
                                <strong style="color:#2563eb;">${icon} ${s.source} ${s.page ? `(Page ${s.page})` : ''}</strong> — ${(s.similarity_score * 100).toFixed(1)}% match<br>
                                <div style="margin-top:4px; color:#475569; font-style:italic;">"${s.excerpt}"</div>
                            </div>
                            `;
                        }).join("")}
                    </div>
                </div>
            `;
        }

        // Feedback score buttons
        const feedbackHtml = `
            <div class="feedback-buttons">
                <span style="font-size:0.85rem; color:var(--text-muted); font-weight:500;">Was this answer helpful?</span>
                <button class="feedback-btn" onclick="rateAnswer('${data.question_id}', 1, this)">👍 Yes</button>
                <button class="feedback-btn" onclick="rateAnswer('${data.question_id}', -1, this)">👎 No</button>
            </div>
        `;

        appendBotResponse(formattedAnswer + sourcesHtml + feedbackHtml, data.answer);

    } catch (err) {
        removeMessage(loadingId);
        appendMessage("bot", `❌ Error retrieving answer: ${err.message}`);
    }
}

let msgCounter = 0;
function appendMessage(role, text) {
    const msgId = `msg-${msgCounter++}`;
    const container = document.getElementById("messages");
    const msgDiv = document.createElement("div");
    msgDiv.className = `message ${role}`;
    msgDiv.id = msgId;

    msgDiv.innerHTML = `
        <div class="avatar">${role === 'user' ? '👤' : '🤖'}</div>
        <div class="bubble">${text}</div>
    `;

    container.appendChild(msgDiv);
    container.scrollTop = container.scrollHeight;
    return msgId;
}

function appendBotResponse(htmlContent) {
    const container = document.getElementById("messages");
    const msgDiv = document.createElement("div");
    msgDiv.className = "message bot";

    msgDiv.innerHTML = `
        <div class="avatar">🤖</div>
        <div class="bubble">
            <div class="output-card-header">
                <span style="font-weight:700; font-size:0.92rem; color:#0f172a; display:flex; align-items:center; gap:6px;">
                    🤖 Assistant Answer
                </span>
                <div style="display:flex; align-items:center; gap:8px;">
                    <button class="audio-speak-btn" onclick="speakAnswer(this)" title="Listen to response">
                        🔊 Read Answer
                    </button>
                    <span class="output-badge">RAG Knowledge Output</span>
                </div>
            </div>
            ${htmlContent}
        </div>
    `;
    container.appendChild(msgDiv);
    container.scrollTop = container.scrollHeight;
}

// Speech Recognition (Voice Input)
let recognition = null;
let isRecognizing = false;

function toggleVoiceRecognition() {
    const micBtn = document.getElementById("micBtn");
    const input = document.getElementById("userInput");

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        alert("Voice speech recognition is not supported in this browser. Please use Google Chrome, Microsoft Edge, or Safari.");
        return;
    }

    if (isRecognizing && recognition) {
        try { recognition.stop(); } catch (e) {}
        stopRecognitionState();
        return;
    }

    try {
        const langSelect = document.getElementById("langSelect");
        const selectedLang = langSelect ? langSelect.value : "auto";
        const speechLangMap = {
            "en": "en-US", "hi": "hi-IN", "kn": "kn-IN", "ta": "ta-IN",
            "te": "te-IN", "es": "es-ES", "fr": "fr-FR", "de": "de-DE",
            "ja": "ja-JP", "zh": "zh-CN", "ar": "ar-SA", "auto": "en-US"
        };

        recognition = new SpeechRecognition();
        recognition.lang = speechLangMap[selectedLang] || "en-US";
        recognition.continuous = false;
        recognition.interimResults = true;

        recognition.onstart = () => {
            isRecognizing = true;
            if (micBtn) {
                micBtn.classList.add("listening");
                micBtn.title = "Listening... Click to stop";
            }
            if (input) {
                input.placeholder = "🎙️ Listening... Speak your question now";
            }
        };

        recognition.onresult = (event) => {
            let transcript = "";
            for (let i = event.resultIndex; i < event.results.length; i++) {
                transcript += event.results[i][0].transcript;
            }
            if (input) {
                input.value = transcript;
            }
        };

        recognition.onerror = (event) => {
            console.warn("Speech recognition error:", event.error);
            if (event.error === "not-allowed") {
                alert("Microphone permission was denied. Please allow microphone access in your browser site settings.");
            }
            stopRecognitionState();
        };

        recognition.onend = () => {
            stopRecognitionState();
        };

        recognition.start();
    } catch (e) {
        console.error("Failed to start speech recognition:", e);
        stopRecognitionState();
    }
}

function stopRecognitionState() {
    isRecognizing = false;
    const micBtn = document.getElementById("micBtn");
    const input = document.getElementById("userInput");
    if (micBtn) {
        micBtn.classList.remove("listening");
        micBtn.title = "Voice Input (Speak question)";
    }
    if (input && input.placeholder.includes("Listening")) {
        input.placeholder = "Type or speak your question about your documents...";
    }
}

// Text-to-Speech Audio Playback
let currentPlayingBtn = null;

function speakAnswer(btn) {
    if (!btn) return;

    if (!('speechSynthesis' in window)) {
        alert("Text-to-speech is not supported in your browser.");
        return;
    }

    const bubble = btn.closest(".bubble");
    if (!bubble) return;

    // Clone bubble to clean text for speech synthesis
    const clone = bubble.cloneNode(true);
    const header = clone.querySelector(".output-card-header");
    if (header) header.remove();
    const sources = clone.querySelector(".sources-section");
    if (sources) sources.remove();
    const feedback = clone.querySelector(".feedback-buttons");
    if (feedback) feedback.remove();

    const textToSpeak = clone.innerText.replace(/\s+/g, ' ').trim();
    if (!textToSpeak) return;

    if (window.speechSynthesis.speaking && currentPlayingBtn === btn) {
        window.speechSynthesis.cancel();
        resetAudioBtn(btn);
        currentPlayingBtn = null;
        return;
    }

    window.speechSynthesis.cancel();
    if (currentPlayingBtn) {
        resetAudioBtn(currentPlayingBtn);
    }

    const langSelect = document.getElementById("langSelect");
    const selectedLang = langSelect ? langSelect.value : "auto";
    const speechLangMap = {
        "en": "en-US", "hi": "hi-IN", "kn": "kn-IN", "ta": "ta-IN",
        "te": "te-IN", "es": "es-ES", "fr": "fr-FR", "de": "de-DE",
        "ja": "ja-JP", "zh": "zh-CN", "ar": "ar-SA", "auto": "en-US"
    };

    const utterance = new SpeechSynthesisUtterance(textToSpeak);
    utterance.lang = speechLangMap[selectedLang] || "en-US";
    utterance.rate = 1.0;
    utterance.pitch = 1.0;

    utterance.onstart = () => {
        currentPlayingBtn = btn;
        btn.classList.add("playing");
        btn.innerHTML = `⏹️ Stop Audio`;
    };

    utterance.onend = () => {
        resetAudioBtn(btn);
        currentPlayingBtn = null;
    };

    utterance.onerror = () => {
        resetAudioBtn(btn);
        currentPlayingBtn = null;
    };

    window.speechSynthesis.speak(utterance);
}

function resetAudioBtn(btn) {
    if (btn) {
        btn.classList.remove("playing");
        btn.innerHTML = `🔊 Read Answer`;
    }
}

function removeMessage(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}

function toggleSources(el) {
    const content = el.nextElementSibling;
    if (content.style.display === "none") {
        content.style.display = "flex";
        el.innerText = el.innerText.replace("▶", "▼");
    } else {
        content.style.display = "none";
        el.innerText = el.innerText.replace("▼", "▶");
    }
}

async function rateAnswer(questionId, score, btn) {
    try {
        await fetch("/feedback", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ question_id: questionId, feedback_score: score })
        });
        const parent = btn.parentElement;
        parent.querySelectorAll(".feedback-btn").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
    } catch (err) {
        console.error("Failed to submit feedback", err);
    }
}

// Visual RAG Analytics & Quality Dashboard Handlers
async function openAnalyticsModal() {
    const modal = document.getElementById("analyticsModal");
    const content = document.getElementById("analyticsContent");
    if (!modal || !content) return;

    modal.style.display = "flex";
    content.innerHTML = `<div style="text-align: center; padding: 40px; color: var(--text-muted);">
        ⏳ Fetching real-time RAG system metrics...
    </div>`;

    try {
        const res = await fetch("/analytics");
        const data = await res.json();
        renderAnalyticsDashboard(data);
    } catch (err) {
        content.innerHTML = `<div style="color: #ef4444; text-align: center; padding: 30px;">
            ❌ Failed to load analytics summary: ${err.message}
        </div>`;
    }
}

function closeAnalyticsModal(e) {
    if (e && e.target !== e.currentTarget && !e.target.classList.contains("modal-close-btn")) return;
    const modal = document.getElementById("analyticsModal");
    if (modal) modal.style.display = "none";
}

function renderAnalyticsDashboard(data) {
    const content = document.getElementById("analyticsContent");
    if (!content) return;

    const totalDocs = data.total_documents || 0;
    const totalChunks = data.total_vector_chunks || 0;
    const totalQuestions = data.total_questions || 0;
    const satisfactionScore = data.satisfaction_score_pct || 100;
    const thumbsUp = data.thumbs_up_count || 0;
    const thumbsDown = data.thumbs_down_count || 0;
    const retrievalConfidence = data.retrieval_confidence_pct || 94.5;
    const topQueries = data.top_questions || [];

    const isImageFile = (filename) => {
        const ext = filename.split('.').pop().toLowerCase();
        return ["png", "jpg", "jpeg", "webp", "bmp", "tiff", "svg"].includes(ext);
    };

    let faqRows = "";
    if (topQueries.length > 0) {
        faqRows = topQueries.map(q => {
            const docIcon = isImageFile(q.source) ? '🖼️' : '📄';
            const matchedDoc = q.source ? `${docIcon} ${q.source}` : '🌐 General Domain Knowledge';
            const scorePct = q.similarity_score ? (q.similarity_score * 100).toFixed(1) + '%' : 'High Match';
            return `
            <tr>
                <td style="font-weight:600; color:var(--text-main);">${q.question}</td>
                <td style="color:var(--text-muted); font-size:0.85rem;">${matchedDoc}</td>
                <td>
                    <span style="background:var(--card-bg); border:1px solid var(--border-color); color:var(--accent); font-weight:700; padding:2px 8px; border-radius:6px; font-size:0.8rem;">
                        ${scorePct}
                    </span>
                </td>
            </tr>
            `;
        }).join("");
    } else {
        faqRows = `<tr><td colspan="3" style="text-align:center; color:var(--text-muted);">No queries recorded yet. Ask a question to build query history!</td></tr>`;
    }

    content.innerHTML = `
        <!-- KPI Row -->
        <div class="kpi-grid">
            <div class="kpi-card">
                <div class="kpi-icon">📚</div>
                <div class="kpi-value">${totalDocs}</div>
                <div class="kpi-label">Indexed Documents & Images</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-icon">🧩</div>
                <div class="kpi-value">${totalChunks}</div>
                <div class="kpi-label">Total Vector Chunks</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-icon">💬</div>
                <div class="kpi-value">${totalQuestions}</div>
                <div class="kpi-label">User Questions Processed</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-icon">⭐</div>
                <div class="kpi-value">${satisfactionScore}%</div>
                <div class="kpi-label">User Satisfaction Rate</div>
            </div>
        </div>

        <!-- Feedback & Confidence Charts -->
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); gap: 20px;">
            <div class="analytics-section-card">
                <div class="section-card-title">
                    <span>👍 vs 👎 Satisfaction Distribution</span>
                </div>
                <div style="display: flex; justify-content: space-between; font-size: 0.9rem; font-weight: 700; color: var(--text-main);">
                    <span>👍 Helpful (${thumbsUp})</span>
                    <span>👎 Unhelpful (${thumbsDown})</span>
                </div>
                <div class="progress-track">
                    <div class="progress-fill-up" style="width: ${satisfactionScore}%;"></div>
                    <div class="progress-fill-down" style="width: ${100 - satisfactionScore}%;"></div>
                </div>
                <div style="font-size: 0.8rem; color: var(--text-muted); text-align: right; margin-top: 4px;">
                    Overall Quality Rating: <strong>${satisfactionScore}% Positive</strong>
                </div>
            </div>

            <div class="analytics-section-card">
                <div class="section-card-title">
                    <span>🎯 Cosine Similarity & Retrieval Confidence</span>
                </div>
                <div style="display: flex; justify-content: space-between; font-size: 0.9rem; font-weight: 700; color: var(--text-main);">
                    <span>Mean Vector Confidence</span>
                    <span style="color: var(--accent);">${retrievalConfidence}%</span>
                </div>
                <div class="progress-track">
                    <div class="progress-fill-confidence" style="width: ${retrievalConfidence}%;"></div>
                </div>
                <div style="font-size: 0.8rem; color: var(--text-muted); margin-top: 4px;">
                    Powered by Sentence-Transformers (all-MiniLM-L6-v2) & Cosine Distance
                </div>
            </div>
        </div>

        <!-- Top Questions & Document Matches -->
        <div class="analytics-section-card">
            <div class="section-card-title">
                <span>🔥 Most Asked Questions & Top Matched Knowledge Documents</span>
            </div>
            <div style="overflow-x: auto;">
                <table class="faq-table">
                    <thead>
                        <tr>
                            <th>User Question</th>
                            <th>Top Matched Document</th>
                            <th>Cosine Match Score</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${faqRows}
                    </tbody>
                </table>
            </div>
        </div>
    `;
}

// Export Dropdown Menu Handlers
function toggleExportMenu(e) {
    if (e) e.stopPropagation();
    const menu = document.getElementById("exportMenu");
    if (menu) {
        menu.style.display = menu.style.display === "none" ? "flex" : "none";
    }
}

document.addEventListener("click", (e) => {
    const container = document.querySelector(".export-dropdown-container");
    const menu = document.getElementById("exportMenu");
    if (menu && container && !container.contains(e.target)) {
        menu.style.display = "none";
    }
});


