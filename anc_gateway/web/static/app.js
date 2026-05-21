const state = {
  requestId: crypto.randomUUID(),
  packet: null,
  manualJob: null,
  manualAudit: null,
  patchPacket: null,
};

const el = (id) => document.getElementById(id);

function renderRequestId() {
  el("requestId").textContent = state.requestId;
}

function showJson(id, value) {
  el(id).textContent = typeof value === "string" ? value : JSON.stringify(value, null, 2);
}

function showError(error) {
  showJson("errorOutput", error);
}

function clearError() {
  el("errorOutput").textContent = "";
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
  await refreshRecent();
}

async function completeManualJob() {
  if (!state.manualJob) {
    showError({ error: { code: "MISSING_MANUAL_JOB", message: "Create a Manual Job first.", request_id: state.requestId } });
    return;
  }
  state.manualJob = await apiFetch(`/manual-jobs/${state.manualJob.manual_job_id}/complete`, {
    method: "POST",
    body: JSON.stringify({
      result_video_uri: el("resultVideoUri").value,
      user_notes: el("userNotes").value || null,
    }),
  });
  showJson("completeManualJobOutput", state.manualJob);
  await refreshRecent();
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
  await refreshRecent();
}

async function buildPatchPacket() {
  if (!state.manualAudit?.failure_record_id) {
    showError({ error: { code: "MISSING_FAILURE_RECORD", message: "Submit Manual Audit first.", request_id: state.requestId } });
    return;
  }
  state.patchPacket = await apiFetch(`/failures/${state.manualAudit.failure_record_id}/recover`, {
    method: "POST",
  });
  showJson("recoverOutput", state.patchPacket);
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

async function copyFromPre(targetId) {
  const text = el(targetId).textContent;
  if (text) {
    await navigator.clipboard.writeText(text);
  }
}

function bindEvents() {
  el("compileBtn").addEventListener("click", compilePrompt);
  el("createManualJobBtn").addEventListener("click", createManualJob);
  el("completeManualJobBtn").addEventListener("click", completeManualJob);
  el("submitManualAuditBtn").addEventListener("click", submitManualAudit);
  el("buildPatchBtn").addEventListener("click", buildPatchPacket);
  el("refreshRecentBtn").addEventListener("click", refreshRecent);
  document.querySelectorAll("[data-copy-target]").forEach((button) => {
    button.addEventListener("click", () => copyFromPre(button.dataset.copyTarget));
  });
}

renderRequestId();
bindEvents();
refreshRecent().catch(showError);
