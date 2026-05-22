const state = {
  requestId: crypto.randomUUID(),
  packet: null,
  manualJob: null,
  manualAudit: null,
  patchPacket: null,
  lastPatchPacket: null,
  case: null,
  currentAttempt: null,
  statusMessage: "",
};

const el = (id) => document.getElementById(id);

function renderRequestId() {
  el("requestId").textContent = state.requestId;
}

function showJson(id, value) {
  el(id).textContent = typeof value === "string" ? value : JSON.stringify(value, null, 2);
}

function createTextElement(tagName, className, text) {
  const node = document.createElement(tagName);
  node.className = className;
  node.textContent = text;
  return node;
}

function normalizeFragments(sourceMap) {
  if (!sourceMap) {
    return null;
  }
  const fragments = sourceMap.fragments ?? sourceMap;
  if (Array.isArray(fragments)) {
    return fragments;
  }
  if (typeof fragments === "object" && fragments !== null) {
    return Object.entries(fragments).map(([fragmentId, fragment]) => ({
      fragment_ref: fragment.fragment_ref || fragment.fragment_id || fragmentId,
      ...fragment,
    }));
  }
  return [];
}

function renderFragmentQuickList(sourceMap) {
  const container = el("fragmentQuickList");
  container.replaceChildren();
  const fragments = normalizeFragments(sourceMap);
  if (fragments === null) {
    container.textContent = "No source map available.";
    return;
  }
  if (fragments.length === 0) {
    container.textContent = "No fragments found.";
    return;
  }
  fragments.forEach((fragment, index) => {
    const fragmentId = fragment.fragment_ref || fragment.fragment_id || fragment.id || `frag_${String(index + 1).padStart(3, "0")}`;
    const originalText = fragment.original_text || fragment.original || "";
    const rewrittenText = fragment.rewritten_text || fragment.compiled_text || fragment.rewrite || "";
    const button = document.createElement("button");
    button.type = "button";
    button.className = "fragment-button";
    button.title = rewrittenText || originalText || fragmentId;
    button.appendChild(createTextElement("span", "fragment-id", fragmentId));
    button.appendChild(createTextElement("span", "fragment-text", originalText || "(empty original_text)"));
    if (rewrittenText) {
      button.appendChild(createTextElement("span", "fragment-rewrite", rewrittenText));
    }
    button.addEventListener("click", () => {
      el("badPromptFragmentRef").value = fragmentId;
    });
    container.appendChild(button);
  });
}

function showError(error) {
  showJson("errorOutput", error);
}

function clearError() {
  el("errorOutput").textContent = "";
}

function showStatus(message) {
  state.statusMessage = message;
  const statusEl = el("statusMessage");
  if (statusEl) {
    statusEl.textContent = message;
    statusEl.classList.add("visible");
    window.setTimeout(() => {
      if (statusEl.textContent === message) {
        statusEl.classList.remove("visible");
        window.setTimeout(() => {
          if (statusEl.textContent === message) {
            statusEl.textContent = "";
          }
        }, 300);
      }
    }, 2000);
  }
}

async function apiFetch(path, options = {}) {
  clearError();
  const response = await fetch(path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      "X-Request-ID": state.requestId,
      ...(options.headers || {}),
    },
  });
  const responseRequestId = response.headers.get("X-Request-ID");
  if (responseRequestId) {
    state.requestId = responseRequestId;
    renderRequestId();
  }
  const payload = await response.json();
  if (!response.ok) {
    showError(payload);
    throw new Error(payload?.error?.message || `HTTP ${response.status}`);
  }
  return payload;
}

async function apiFetchText(path, options = {}) {
  clearError();
  const response = await fetch(path, {
    ...options,
    headers: {
      "X-Request-ID": state.requestId,
      ...(options.headers || {}),
    },
  });
  const responseRequestId = response.headers.get("X-Request-ID");
  if (responseRequestId) {
    state.requestId = responseRequestId;
    renderRequestId();
  }
  const payload = await response.text();
  if (!response.ok) {
    showError(payload);
    throw new Error(`HTTP ${response.status}`);
  }
  return payload;
}

async function compilePrompt() {
  const rawPrompt = el("rawPrompt").value;
  const payload = {
    state: {
      id: "console_state",
      shot_id: "console_shot",
      objects: [],
    },
    render_contract: {
      shot_id: "console_shot",
      ruleset_fingerprint: "console",
    },
    raw_prompt: rawPrompt,
  };
  state.packet = await apiFetch("/compile", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  showJson("compiledPrompt", state.packet.compiled_prompt);
  showJson("compileOutput", state.packet);
  renderFragmentQuickList(state.packet.source_map);
  showStatus("Compiled");
}

async function createManualJob() {
  if (!state.packet) {
    showError({ error: { code: "MISSING_PACKET", message: "Run Compile first.", request_id: state.requestId } });
    return;
  }
  state.manualJob = await apiFetch("/manual-jobs", {
    method: "POST",
    body: JSON.stringify({
      condition_hash: state.packet.condition_hash,
      compiled_prompt: state.packet.compiled_prompt,
      source_map: state.packet.source_map,
      platform: el("platform").value,
    }),
  });
  showJson("copyInstructions", state.manualJob.copy_instructions);
  showJson("manualJobOutput", state.manualJob);
  if (state.currentAttempt) {
    state.currentAttempt = await apiFetch(`/attempts/${state.currentAttempt.attempt_id}/manual-job`, {
      method: "POST",
      body: JSON.stringify({ manual_job_id: state.manualJob.manual_job_id }),
    });
    await showAttemptWorkspace();
  }
  await refreshRecentPanels();
  showStatus("Manual job created");
}

async function completeManualJob() {
  if (!state.manualJob) {
    showError({ error: { code: "MISSING_MANUAL_JOB", message: "Create a Manual Job first.", request_id: state.requestId } });
    return;
  }
  const resultVideoUri = el("resultVideoUri").value.trim();
  if (!resultVideoUri) {
    showError({ error: { code: "VALIDATION_ERROR", message: "result_video_uri is required.", request_id: state.requestId } });
    return;
  }
  state.manualJob = await apiFetch(`/manual-jobs/${state.manualJob.manual_job_id}/complete`, {
    method: "POST",
    body: JSON.stringify({
      result_video_uri: resultVideoUri,
      user_notes: el("userNotes").value || null,
    }),
  });
  showJson("completeManualJobOutput", state.manualJob);
  if (state.currentAttempt) {
    state.currentAttempt = await apiFetch(`/attempts/${state.currentAttempt.attempt_id}/manual-job`, {
      method: "POST",
      body: JSON.stringify({
        manual_job_id: state.manualJob.manual_job_id,
        result_video_uri: state.manualJob.result_video_uri,
      }),
    });
    await showAttemptWorkspace();
  }
  await refreshRecentPanels();
  showStatus("Manual job completed");
}

async function submitManualAudit() {
  if (!state.manualJob) {
    showError({ error: { code: "MISSING_MANUAL_JOB", message: "Create a Manual Job first.", request_id: state.requestId } });
    return;
  }
  state.manualAudit = await apiFetch("/manual-audits", {
    method: "POST",
    body: JSON.stringify({
      manual_job_id: state.manualJob.manual_job_id,
      bad_prompt_fragment_ref: el("badPromptFragmentRef").value || "frag_001",
      failure_type: el("failureType").value,
      notes: el("auditNotes").value || null,
    }),
  });
  showJson("manualAuditOutput", state.manualAudit);
  if (state.currentAttempt) {
    state.currentAttempt = await apiFetch(`/attempts/${state.currentAttempt.attempt_id}/manual-audit`, {
      method: "POST",
      body: JSON.stringify({
        manual_audit_id: state.manualAudit.audit_id,
        failure_record_id: state.manualAudit.failure_record_id,
      }),
    });
    await showAttemptWorkspace();
  }
  await refreshRecentPanels();
  showStatus("Manual audit submitted");
}

async function buildPatchPacket() {
  if (!state.manualAudit?.failure_record_id) {
    showError({ error: { code: "MISSING_FAILURE_RECORD", message: "Submit Manual Audit first.", request_id: state.requestId } });
    return;
  }
  state.patchPacket = await apiFetch(`/failures/${state.manualAudit.failure_record_id}/recover`, {
    method: "POST",
  });
  state.lastPatchPacket = state.patchPacket;
  showJson("recoverOutput", state.patchPacket);
  if (state.currentAttempt) {
    state.currentAttempt = await apiFetch(`/attempts/${state.currentAttempt.attempt_id}/patch`, {
      method: "POST",
      body: JSON.stringify({ patch_packet: state.patchPacket }),
    });
    await showAttemptWorkspace();
  }
  showStatus("Patch packet built");
}

async function createCase() {
  state.case = await apiFetch("/cases", {
    method: "POST",
    body: JSON.stringify({
      title: el("caseTitle").value || null,
      raw_prompt: el("rawPrompt").value,
      platform: el("platform").value,
    }),
  });
  state.currentAttempt = null;
  showJson("caseOutput", state.case);
  showJson("attemptOutput", "");
  await showAttemptList();
  await showTimeline();
  await refreshRecentPanels();
  showStatus("Case created");
}

async function saveCurrentAttempt() {
  if (!state.case) {
    showError({ error: { code: "MISSING_CASE", message: "Create a Case first.", request_id: state.requestId } });
    return;
  }
  if (!state.packet) {
    showError({ error: { code: "MISSING_PACKET", message: "Run Compile first.", request_id: state.requestId } });
    return;
  }
  state.currentAttempt = await apiFetch(`/cases/${state.case.case_id}/attempts`, {
    method: "POST",
    body: JSON.stringify({
      raw_prompt: el("rawPrompt").value,
      compiled_prompt: state.packet.compiled_prompt,
      condition_hash: state.packet.condition_hash,
      source_map: state.packet.source_map,
    }),
  });
  await showAttemptWorkspace();
  await refreshCurrentCase();
  showStatus("Attempt saved");
}

async function createNextAttemptFromPatch() {
  if (!state.case || !state.currentAttempt) {
    showError({ error: { code: "MISSING_ATTEMPT", message: "Save the current Attempt first.", request_id: state.requestId } });
    return;
  }
  if (!state.lastPatchPacket && !state.patchPacket) {
    showError({ error: { code: "MISSING_PATCH_PACKET", message: "Build Patch Packet first.", request_id: state.requestId } });
    return;
  }
  state.currentAttempt = await apiFetch(`/attempts/${state.currentAttempt.attempt_id}/next`, {
    method: "POST",
    body: JSON.stringify({
      patch_packet: state.lastPatchPacket || state.patchPacket,
    }),
  });
  el("rawPrompt").value = state.currentAttempt.raw_prompt;
  state.packet = null;
  showJson("compiledPrompt", "");
  showJson("compileOutput", "");
  renderFragmentQuickList(null);
  await showAttemptWorkspace();
  await refreshCurrentCase();
  showStatus("Next attempt created");
}

async function acceptAttempt() {
  if (!state.currentAttempt) {
    showError({ error: { code: "MISSING_ATTEMPT", message: "Save or select an Attempt first.", request_id: state.requestId } });
    return;
  }
  state.currentAttempt = await apiFetch(`/attempts/${state.currentAttempt.attempt_id}/accept`, {
    method: "POST",
    body: JSON.stringify({ accept_case: true }),
  });
  if (state.case) {
    state.case = await apiFetch(`/cases/${state.case.case_id}`);
    showJson("caseOutput", state.case);
  }
  await showAttemptWorkspace();
  await refreshCurrentCase();
  showStatus("Attempt accepted");
}

async function archiveCase() {
  if (!state.case) {
    showError({ error: { code: "MISSING_CASE", message: "Create a Case first.", request_id: state.requestId } });
    return;
  }
  state.case = await apiFetch(`/cases/${state.case.case_id}/archive`, { method: "POST" });
  showJson("caseOutput", state.case);
  await showAttemptWorkspace();
  await refreshRecentPanels();
  showStatus("Case archived");
}

async function exportMarkdown() {
  if (!state.case) {
    showError({ error: { code: "MISSING_CASE", message: "Create a Case first.", request_id: state.requestId } });
    return;
  }
  const markdown = await apiFetchText(`/cases/${state.case.case_id}/export.md`);
  const blob = new Blob([markdown], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  window.open(url, "_blank", "noopener");
  window.setTimeout(() => URL.revokeObjectURL(url), 60000);
  showStatus("Markdown exported");
}

async function showAttemptWorkspace() {
  showJson("attemptOutput", state.currentAttempt || "");
  await showAttemptList();
  await showTimeline();
}

async function showAttemptList() {
  if (!state.case) {
    showJson("attemptListOutput", "");
    return;
  }
  const attempts = await apiFetch(`/cases/${state.case.case_id}/attempts`);
  showJson("attemptListOutput", attempts);
}

async function showTimeline() {
  if (!state.case) {
    showJson("timelineOutput", "");
    return;
  }
  const timeline = await apiFetch(`/cases/${state.case.case_id}/timeline`);
  showJson("timelineOutput", timeline);
}

async function refreshRecent() {
  const [manualJobs, manualAudits, failures] = await Promise.all([
    apiFetch("/manual-jobs/recent?limit=10"),
    apiFetch("/manual-audits/recent?limit=10"),
    apiFetch("/storage/recent-failures?limit=10"),
  ]);
  showJson("recentManualJobs", manualJobs);
  showJson("recentManualAudits", manualAudits);
  showJson("recentFailures", failures);
}

async function refreshRecentPanels() {
  await refreshRecent();
  showStatus("Recent panels updated");
}

async function refreshCurrentCase() {
  if (!state.case) {
    return;
  }
  try {
    state.case = await apiFetch(`/cases/${state.case.case_id}`);
    showJson("caseOutput", state.case);
  } catch {
    // ignore if case not found
  }
}

async function refreshTimeline() {
  await showTimeline();
  showStatus("Timeline refreshed");
}

async function refreshWorkspaceState() {
  await Promise.all([
    refreshCurrentCase(),
    showAttemptWorkspace(),
    refreshRecent(),
  ]);
}

async function copyFromPre(targetId) {
  const text = el(targetId).textContent;
  if (text) {
    await navigator.clipboard.writeText(text);
  }
}

function getPatchPromptText(patchPacket) {
  if (!patchPacket) {
    return "";
  }
  return patchPacket.patch_prompt || patchPacket.positive_lock || patchPacket.suggested_positive_lock || JSON.stringify(patchPacket, null, 2);
}

async function copyPatchPrompt() {
  const status = el("copyPatchStatus");
  const text = getPatchPromptText(state.lastPatchPacket || state.patchPacket);
  if (!text) {
    status.textContent = "Build a patch packet first.";
    return;
  }
  await navigator.clipboard.writeText(text);
  status.textContent = "Copied";
  window.setTimeout(() => {
    if (status.textContent === "Copied") {
      status.textContent = "";
    }
  }, 1800);
}

async function loadRecentCases() {
  const cases = await apiFetch("/cases/recent?limit=10");
  showJson("recentCases", cases);
}

async function selectCase(caseId) {
  state.case = await apiFetch(`/cases/${caseId}`);
  state.currentAttempt = null;
  showJson("caseOutput", state.case);
  showJson("attemptOutput", "");
  await showAttemptList();
  await showTimeline();
  showStatus("Case selected");
}

function bindEvents() {
  el("compileBtn").addEventListener("click", compilePrompt);
  el("createCaseBtn").addEventListener("click", createCase);
  el("saveAttemptBtn").addEventListener("click", saveCurrentAttempt);
  el("nextAttemptBtn").addEventListener("click", createNextAttemptFromPatch);
  el("acceptAttemptBtn").addEventListener("click", acceptAttempt);
  el("archiveCaseBtn").addEventListener("click", archiveCase);
  el("exportMarkdownBtn").addEventListener("click", exportMarkdown);
  el("createManualJobBtn").addEventListener("click", createManualJob);
  el("completeManualJobBtn").addEventListener("click", completeManualJob);
  el("submitManualAuditBtn").addEventListener("click", submitManualAudit);
  el("buildPatchBtn").addEventListener("click", buildPatchPacket);
  el("copyPatchPromptBtn").addEventListener("click", copyPatchPrompt);
  el("refreshRecentBtn").addEventListener("click", refreshRecent);
  el("refreshCasesBtn").addEventListener("click", loadRecentCases);
  document.querySelectorAll("[data-copy-target]").forEach((button) => {
    button.addEventListener("click", () => copyFromPre(button.dataset.copyTarget));
  });
}

renderRequestId();
renderFragmentQuickList(null);
bindEvents();
refreshRecent().catch(showError);
loadRecentCases().catch(showError);
