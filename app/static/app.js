document.addEventListener("DOMContentLoaded", () => {
    loadDocuments();
});

// Markdown formatter function for clean responses
function formatMarkdown(text) {
    if (!text) return "";
    
    // Format bold **text**
    let formatted = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    
    // Format blockquotes > text
    formatted = formatted.replace(/^>\s?(.*)$/gm, '<blockquote>$1</blockquote>');
    
    // Format bullet points 📌 or -
    formatted = formatted.replace(/📌/g, '<br>📌');
    formatted = formatted.replace(/\n\n/g, '<br><br>');
    formatted = formatted.replace(/\n/g, '<br>');
    
    return formatted;
}

async function loadDocuments() {
    const docList = document.getElementById("docList");
    try {
        const res = await fetch("/documents");
        const data = await res.json();
        if (data.documents && data.documents.length > 0) {
            docList.innerHTML = data.documents.map(d => `
                <div class="doc-item">
                    <span class="doc-title">${d.title}</span>
                    <span class="doc-chunks">${d.chunk_count} chunks</span>
                </div>
            `).join("");
        } else {
            docList.innerHTML = `<div style="font-size: 0.85rem; color: var(--text-muted);">No documents ingested yet.</div>`;
        }
    } catch (err) {
        docList.innerHTML = `<div style="font-size: 0.85rem; color: #ef4444;">Failed to load docs</div>`;
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

    appendMessage("user", question);
    input.value = "";

    const loadingId = appendMessage("bot", "Searching knowledge base and formulating answer...");

    try {
        const res = await fetch("/ask", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ question: question, top_k: 3 })
        });

        const data = await res.json();
        removeMessage(loadingId);

        let formattedAnswer = formatMarkdown(data.answer);

        // Render sources if available
        let sourcesHtml = "";
        if (data.sources && data.sources.length > 0) {
            const sourcePills = data.sources.map(s => 
                `<span style="background: rgba(79,70,229,0.25); border: 1px solid rgba(79,70,229,0.5); color: #a5b4fc; padding: 4px 10px; border-radius: 8px; font-size: 0.85rem; font-weight: 600;">
                    📄 ${s.source} ${s.page ? `(Page ${s.page})` : ''} • ${(s.similarity_score * 100).toFixed(1)}% match
                </span>`
            ).join(" ");

            sourcesHtml = `
                <div class="sources-section">
                    <div style="font-size: 0.8rem; color: #94a3b8; font-weight: 700; margin-bottom: 8px;">SOURCE DOCUMENTS:</div>
                    <div style="display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 10px;">
                        ${sourcePills}
                    </div>
                    <div class="sources-toggle" onclick="toggleSources(this)">
                        🔍 View Extracted Text Snippets ▶
                    </div>
                    <div class="sources-content" style="display:none; flex-direction:column; gap:8px; margin-top:8px;">
                        ${data.sources.map(s => `
                            <div class="source-card">
                                <strong style="color:#38bdf8;">📄 ${s.source} ${s.page ? `(Page ${s.page})` : ''}</strong> — ${(s.similarity_score * 100).toFixed(1)}% match<br>
                                <div style="margin-top:4px; color:#cbd5e1; font-style:italic;">"${s.excerpt}"</div>
                            </div>
                        `).join("")}
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

        appendBotResponse(formattedAnswer + sourcesHtml + feedbackHtml);

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
        <div class="bubble">${htmlContent}</div>
    `;
    container.appendChild(msgDiv);
    container.scrollTop = container.scrollHeight;
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
