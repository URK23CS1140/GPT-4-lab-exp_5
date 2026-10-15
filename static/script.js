/**
 * Automated Legal Document Analyzer
 * Frontend Logic & Interactivity
 * Experiment 5 - Building Applications using GPT-4 / Ollama
 */

document.addEventListener("DOMContentLoaded", () => {
  // Elements
  const tabBtns = document.querySelectorAll(".tab-btn");
  const tabContents = document.querySelectorAll(".tab-content");
  const fileInput = document.getElementById("fileInput");
  const dropZone = document.getElementById("dropZone");
  const selectedFileInfo = document.getElementById("selectedFileInfo");
  const fileNameBadge = document.getElementById("fileNameBadge");
  const btnRemoveFile = document.getElementById("btnRemoveFile");
  const manualText = document.getElementById("manualText");
  const documentTypeSelect = document.getElementById("documentType");
  const partiesHintInput = document.getElementById("partiesHint");
  const analysisTypeSelect = document.getElementById("analysisType");
  const analysisForm = document.getElementById("analysisForm");
  const btnAnalyze = document.getElementById("btnAnalyze");
  const btnClearForm = document.getElementById("btnClearForm");
  const btnLoadSample = document.getElementById("btnLoadSample");
  const loadingOverlay = document.getElementById("loadingOverlay");
  const loadingTitle = document.getElementById("loadingTitle");
  const loadingSubtitle = document.getElementById("loadingSubtitle");
  const resultsSection = document.getElementById("resultsSection");
  const inputSection = document.getElementById("inputSection");

  // Results & Dashboard Elements
  const engineBadge = document.getElementById("engineBadge");
  const metricDocType = document.getElementById("metricDocType");
  const metricWordCount = document.getElementById("metricWordCount");
  const metricCharCount = document.getElementById("metricCharCount");
  const metricPartiesCount = document.getElementById("metricPartiesCount");
  const metricObligationsCount = document.getElementById("metricObligationsCount");
  const metricClausesCount = document.getElementById("metricClausesCount");
  const metricDatesCount = document.getElementById("metricDatesCount");
  const outputSummary = document.getElementById("outputSummary");

  const cardDocType = document.getElementById("cardDocType");
  const cardParties = document.getElementById("cardParties");
  const cardPurpose = document.getElementById("cardPurpose");
  const cardObligations = document.getElementById("cardObligations");
  const cardRights = document.getElementById("cardRights");
  const cardPayment = document.getElementById("cardPayment");
  const cardDuration = document.getElementById("cardDuration");
  const cardTermination = document.getElementById("cardTermination");
  const cardConfidentiality = document.getElementById("cardConfidentiality");
  const cardDates = document.getElementById("cardDates");
  const cardGoverningLaw = document.getElementById("cardGoverningLaw");
  const cardClauses = document.getElementById("cardClauses");
  const distributionGrid = document.getElementById("distributionGrid");

  // Modal & Download Buttons
  const btnViewRawJson = document.getElementById("btnViewRawJson");
  const btnCopyJson = document.getElementById("btnCopyJson");
  const btnDownloadTxt = document.getElementById("btnDownloadTxt");
  const btnDownloadHtml = document.getElementById("btnDownloadHtml");
  const btnPrintReport = document.getElementById("btnPrintReport");
  const btnAnalyzeAgain = document.getElementById("btnAnalyzeAgain");
  const jsonModal = document.getElementById("jsonModal");
  const btnCloseJsonModal = document.getElementById("btnCloseJsonModal");
  const btnModalClose = document.getElementById("btnModalClose");
  const btnModalCopy = document.getElementById("btnModalCopy");
  const rawJsonCode = document.getElementById("rawJsonCode");

  // State
  let currentAnalysisData = null;
  let activeTab = "uploadTab";

  // Check Ollama Health
  async function checkHealth() {
    try {
      const res = await fetch("/health");
      if (res.ok) {
        const data = await res.json();
        const pill = document.getElementById("ollamaStatusPill");
        const text = document.getElementById("ollamaStatusText");
        const notice = document.getElementById("ollamaNotice");

        if (data.ollama_active) {
          pill.className = "status-pill status-online";
          text.textContent = `Ollama: ${data.target_model}`;
          if (notice) notice.style.display = "none";
        } else {
          pill.className = "status-pill status-offline";
          text.textContent = "Ollama Offline (Deterministic Fallback)";
          if (notice) notice.style.display = "flex";
        }
      }
    } catch (e) {
      console.warn("Health check skipped:", e);
    }
  }
  checkHealth();

  // Tab switching
  tabBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      tabBtns.forEach(b => b.classList.remove("active"));
      tabContents.forEach(c => c.classList.remove("active"));
      btn.classList.add("active");
      const targetId = btn.getAttribute("data-tab");
      document.getElementById(targetId).classList.add("active");
      activeTab = targetId;
    });
  });

  // File Upload Handlers
  dropZone.addEventListener("click", (e) => {
    if (e.target !== btnRemoveFile) {
      fileInput.click();
    }
  });

  fileInput.addEventListener("change", (e) => {
    if (fileInput.files.length > 0) {
      const file = fileInput.files[0];
      fileNameBadge.textContent = `${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
      selectedFileInfo.style.display = "inline-flex";
    }
  });

  btnRemoveFile.addEventListener("click", (e) => {
    e.stopPropagation();
    fileInput.value = "";
    selectedFileInfo.style.display = "none";
  });

  ["dragenter", "dragover"].forEach(eventName => {
    dropZone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropZone.classList.add("dragover");
    });
  });

  ["dragleave", "drop"].forEach(eventName => {
    dropZone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropZone.classList.remove("dragover");
    });
  });

  dropZone.addEventListener("drop", (e) => {
    const dt = e.dataTransfer;
    const files = dt.files;
    if (files.length > 0) {
      fileInput.files = files;
      fileNameBadge.textContent = `${files[0].name} (${(files[0].size / 1024).toFixed(1)} KB)`;
      selectedFileInfo.style.display = "inline-flex";
    }
  });

  // Load Sample Contract Button
  btnLoadSample.addEventListener("click", async () => {
    try {
      btnLoadSample.textContent = "Loading sample...";
      const res = await fetch("/sample");
      if (res.ok) {
        const data = await res.json();
        // Switch to text tab
        tabBtns.forEach(b => b.classList.remove("active"));
        tabContents.forEach(c => c.classList.remove("active"));
        const textTabBtn = document.querySelector('[data-tab="textTab"]');
        textTabBtn.classList.add("active");
        document.getElementById("textTab").classList.add("active");
        activeTab = "textTab";

        manualText.value = data.content;
        documentTypeSelect.value = data.document_type;
        partiesHintInput.value = data.parties;
        btnLoadSample.textContent = "✓ Sample Contract Loaded";
        setTimeout(() => {
          btnLoadSample.textContent = "⚡ Load Sample Employment Contract";
        }, 2500);
      } else {
        alert("Could not load sample contract.");
        btnLoadSample.textContent = "⚡ Load Sample Employment Contract";
      }
    } catch (err) {
      alert("Error loading sample: " + err.message);
      btnLoadSample.textContent = "⚡ Load Sample Employment Contract";
    }
  });

  // Clear Form
  btnClearForm.addEventListener("click", () => {
    fileInput.value = "";
    selectedFileInfo.style.display = "none";
    manualText.value = "";
    partiesHintInput.value = "";
    documentTypeSelect.value = "Employment Agreement";
    analysisTypeSelect.value = "Complete Analysis";
  });

  // Form Submit
  analysisForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    const hasFile = fileInput.files && fileInput.files.length > 0;
    const hasText = manualText.value.trim().length > 0;

    if (!hasFile && !hasText) {
      alert("Please upload a legal document file or paste legal text before analyzing.");
      return;
    }

    const formData = new FormData(analysisForm);

    // If on text tab and file exists, prefer text or clear file
    if (activeTab === "textTab" && hasText && !hasFile) {
      formData.delete("file");
    }

    // Show Loading
    loadingOverlay.style.display = "flex";
    loadingTitle.textContent = "Processing Document...";
    loadingSubtitle.textContent = "Extracting text, cleaning formatting, and identifying legal sections";

    const loadingStages = [
      { delay: 1200, title: "Structuring Legal Prompts...", sub: "Synthesizing zero-hallucination extraction schema" },
      { delay: 2800, title: "Executing Llama 3.2 Inference...", sub: "Running local LLM inference on localhost:11434" },
      { delay: 6500, title: "Consolidating Structured Results...", sub: "Normalizing clauses, obligations, dates, and summary" }
    ];

    const stageTimers = loadingStages.map(stage => {
      return setTimeout(() => {
        loadingTitle.textContent = stage.title;
        loadingSubtitle.textContent = stage.sub;
      }, stage.delay);
    });

    try {
      const response = await fetch("/analyze", {
        method: "POST",
        body: formData
      });

      stageTimers.forEach(t => clearTimeout(t));

      const result = await response.json();
      loadingOverlay.style.display = "none";

      if (result.success) {
        currentAnalysisData = result;
        renderDashboard(result);
        resultsSection.style.display = "block";
        resultsSection.scrollIntoView({ behavior: "smooth" });
      } else {
        alert("Analysis Error: " + (result.error || "An unknown error occurred."));
      }
    } catch (err) {
      stageTimers.forEach(t => clearTimeout(t));
      loadingOverlay.style.display = "none";
      alert("Failed to communicate with server: " + err.message);
    }
  });

  // Render Dashboard
  function renderDashboard(data) {
    const analysis = data.analysis;
    const stats = data.document_stats;
    const metrics = data.dashboard_metrics;

    // Engine badge
    engineBadge.textContent = analysis.inference_engine || "Local Llama 3.2";

    // Metrics Strip
    metricDocType.textContent = analysis.document_type || "Legal Document";
    metricWordCount.textContent = (stats.word_count || 0).toLocaleString();
    metricCharCount.textContent = (stats.character_count || 0).toLocaleString();
    metricPartiesCount.textContent = metrics.parties_count || 0;
    metricObligationsCount.textContent = metrics.obligations_count || 0;
    metricClausesCount.textContent = metrics.key_clauses_count || 0;
    metricDatesCount.textContent = metrics.important_dates_count || 0;

    // Executive Summary
    outputSummary.textContent = analysis.summary || "Not specified in the document.";

    // Card 1: Document Type
    cardDocType.textContent = analysis.document_type || "Not specified in the document.";

    // Card 2: Parties
    renderList(cardParties, analysis.parties);

    // Card 3: Purpose
    cardPurpose.textContent = analysis.purpose || "Not specified in the document.";

    // Card 4: Obligations
    renderList(cardObligations, analysis.obligations);

    // Card 5: Rights
    renderList(cardRights, analysis.rights);

    // Card 6: Payment Terms
    cardPayment.textContent = analysis.payment_terms || "Not specified in the document.";

    // Card 7: Duration / Term
    cardDuration.textContent = analysis.duration || "Not specified in the document.";

    // Card 8: Termination
    cardTermination.textContent = analysis.termination || "Not specified in the document.";

    // Card 9: Confidentiality
    cardConfidentiality.textContent = analysis.confidentiality || "Not specified in the document.";

    // Card 10: Dates
    renderList(cardDates, analysis.important_dates);

    // Card 11: Governing Law
    cardGoverningLaw.textContent = analysis.governing_law || "Not specified in the document.";

    // Card 12: Potentially Important Clauses
    cardClauses.innerHTML = "";
    const clauses = analysis.key_clauses;
    if (Array.isArray(clauses) && clauses.length > 0 && clauses[0] !== "Not specified in the document.") {
      clauses.forEach(clause => {
        const badge = document.createElement("span");
        badge.className = "clause-badge-item";
        badge.textContent = clause;
        cardClauses.appendChild(badge);
      });
    } else {
      cardClauses.innerHTML = '<span class="text-muted">No specific clauses identified.</span>';
    }

    // Clause Distribution & Compliance Grid
    renderClauseDistribution(analysis.key_clauses || []);
  }

  function renderList(container, items) {
    container.innerHTML = "";
    if (Array.isArray(items) && items.length > 0) {
      items.forEach(item => {
        const li = document.createElement("li");
        li.textContent = item;
        container.appendChild(li);
      });
    } else if (typeof items === "string" && items.trim()) {
      const li = document.createElement("li");
      li.textContent = items;
      container.appendChild(li);
    } else {
      container.innerHTML = "<li>Not specified in the document.</li>";
    }
  }

  function renderClauseDistribution(detectedClauses) {
    const standardClauses = [
      "Confidentiality",
      "Termination",
      "Intellectual Property",
      "Payment Terms",
      "Liability",
      "Dispute Resolution",
      "Governing Law",
      "Non-compete",
      "Non-solicitation",
      "Data Protection / Privacy"
    ];

    distributionGrid.innerHTML = "";
    const detectedLower = detectedClauses.map(c => c.toLowerCase());

    standardClauses.forEach(name => {
      const isPresent = detectedLower.some(d => d.includes(name.toLowerCase()) || name.toLowerCase().includes(d));
      const div = document.createElement("div");
      div.className = "dist-item";
      div.innerHTML = `
        <span class="dist-name">${name}</span>
        <span class="${isPresent ? 'dist-status-present' : 'dist-status-absent'}">
          ${isPresent ? '✓ Identified' : '— Not Found'}
        </span>
      `;
      distributionGrid.appendChild(div);
    });
  }

  // Raw JSON Modal
  btnViewRawJson.addEventListener("click", () => {
    if (!currentAnalysisData) return;
    rawJsonCode.textContent = JSON.stringify(currentAnalysisData.analysis, null, 2);
    jsonModal.style.display = "flex";
  });

  const closeModal = () => { jsonModal.style.display = "none"; };
  btnCloseJsonModal.addEventListener("click", closeModal);
  btnModalClose.addEventListener("click", closeModal);

  // Copy JSON
  btnCopyJson.addEventListener("click", copyJsonToClipboard);
  btnModalCopy.addEventListener("click", copyJsonToClipboard);

  function copyJsonToClipboard() {
    if (!currentAnalysisData) return;
    const jsonStr = JSON.stringify(currentAnalysisData.analysis, null, 2);
    navigator.clipboard.writeText(jsonStr).then(() => {
      const originalText = btnCopyJson.textContent;
      btnCopyJson.textContent = "✓ Copied!";
      btnModalCopy.textContent = "✓ Copied!";
      setTimeout(() => {
        btnCopyJson.textContent = originalText;
        btnModalCopy.textContent = "Copy JSON";
      }, 2000);
    }).catch(err => {
      alert("Failed to copy JSON: " + err);
    });
  }

  // Downloads
  btnDownloadTxt.addEventListener("click", async () => {
    if (!currentAnalysisData) return;
    try {
      const res = await fetch("/download/txt", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(currentAnalysisData)
      });
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${currentAnalysisData.document_stats.filename || "legal"}_analysis.txt`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (e) {
      alert("Error downloading TXT report: " + e.message);
    }
  });

  btnDownloadHtml.addEventListener("click", async () => {
    if (!currentAnalysisData) return;
    try {
      const res = await fetch("/download/html", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(currentAnalysisData)
      });
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${currentAnalysisData.document_stats.filename || "legal"}_analysis.html`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (e) {
      alert("Error downloading HTML report: " + e.message);
    }
  });

  // Print
  btnPrintReport.addEventListener("click", () => {
    window.print();
  });

  // Analyze Again
  btnAnalyzeAgain.addEventListener("click", () => {
    inputSection.scrollIntoView({ behavior: "smooth" });
  });
});
