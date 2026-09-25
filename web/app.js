"use strict";

const elements = {
  serviceStatus: document.querySelector("#service-status"),
  userId: document.querySelector("#user-id"),
  userRole: document.querySelector("#user-role"),
  assistantForm: document.querySelector("#assistant-form"),
  assistantMessage: document.querySelector("#assistant-message"),
  assistantResult: document.querySelector("#assistant-result"),
  createForm: document.querySelector("#create-form"),
  ticketDescription: document.querySelector("#ticket-description"),
  ticketId: document.querySelector("#ticket-id"),
  queryTicket: document.querySelector("#query-ticket"),
  closeTicket: document.querySelector("#close-ticket"),
  approval: document.querySelector("#approval"),
  ticketResult: document.querySelector("#ticket-result"),
  toast: document.querySelector("#toast"),
};

function showToast(message, isError = false) {
  elements.toast.textContent = message;
  elements.toast.className = `toast show${isError ? " error" : ""}`;
  window.setTimeout(() => { elements.toast.className = "toast"; }, 2800);
}

async function request(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const data = await response.json();
  if (!response.ok) {
    const detail = typeof data.detail === "string" ? data.detail : "请求数据没有通过校验。";
    throw new Error(detail);
  }
  return data;
}

function setLoading(button, loading, originalText) {
  button.disabled = loading;
  button.textContent = loading ? "处理中…" : originalText;
}

function clearResult(container) {
  container.classList.remove("empty-state");
  container.replaceChildren();
}

function addTextElement(container, tag, text, className = "") {
  const element = document.createElement(tag);
  element.textContent = text;
  if (className) element.className = className;
  container.appendChild(element);
  return element;
}

function renderAssistant(data) {
  clearResult(elements.assistantResult);
  addTextElement(elements.assistantResult, "h3", "回答");
  addTextElement(elements.assistantResult, "p", data.message);

  if (data.sources.length) {
    addTextElement(elements.assistantResult, "h3", "来源");
    const list = document.createElement("ul");
    data.sources.forEach((source) => {
      addTextElement(list, "li", `${source.file} · ${source.section} · 相关度 ${source.score.toFixed(3)}`);
    });
    elements.assistantResult.appendChild(list);
  }
}

function renderTicket(ticket, heading) {
  clearResult(elements.ticketResult);
  addTextElement(elements.ticketResult, "h3", heading);
  const summary = document.createElement("div");
  summary.className = "ticket-summary";
  [
    ["编号", ticket.id],
    ["状态", ticket.status],
    ["类别", ticket.category],
    ["优先级", ticket.priority],
  ].forEach(([label, value]) => {
    const cell = document.createElement("div");
    addTextElement(cell, "small", label);
    addTextElement(cell, "strong", String(value));
    summary.appendChild(cell);
  });
  elements.ticketResult.appendChild(summary);
  addTextElement(elements.ticketResult, "p", ticket.description);
}

function identity() {
  const userId = elements.userId.value.trim();
  if (!userId) throw new Error("请先填写用户编号。");
  return { userId, userRole: elements.userRole.value };
}

async function checkHealth() {
  try {
    const data = await request("/health");
    elements.serviceStatus.className = "status-pill status-online";
    elements.serviceStatus.lastChild.textContent = ` 服务正常 · ${data.version}`;
  } catch (error) {
    elements.serviceStatus.className = "status-pill status-offline";
    elements.serviceStatus.lastChild.textContent = " 服务不可用";
  }
}

document.querySelectorAll("[data-question]").forEach((button) => {
  button.addEventListener("click", () => {
    elements.assistantMessage.value = button.dataset.question;
    elements.assistantMessage.focus();
  });
});

elements.assistantForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = event.submitter;
  try {
    const { userId, userRole } = identity();
    setLoading(button, true, "查找有依据的答案");
    const data = await request("/v1/assistant/messages", {
      method: "POST",
      body: JSON.stringify({
        message: elements.assistantMessage.value.trim(),
        user_id: userId,
        user_role: userRole,
      }),
    });
    renderAssistant(data);
  } catch (error) {
    showToast(error.message, true);
  } finally {
    setLoading(button, false, "查找有依据的答案");
  }
});

elements.createForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = event.submitter;
  try {
    const { userId } = identity();
    setLoading(button, true, "创建工单");
    const ticket = await request("/v1/tickets", {
      method: "POST",
      body: JSON.stringify({
        description: elements.ticketDescription.value.trim(),
        user_id: userId,
      }),
    });
    elements.ticketId.value = ticket.id;
    elements.approval.checked = false;
    renderTicket(ticket, "工单创建成功");
    showToast(`已创建工单 ${ticket.id}`);
  } catch (error) {
    showToast(error.message, true);
  } finally {
    setLoading(button, false, "创建工单");
  }
});

elements.queryTicket.addEventListener("click", async () => {
  try {
    const { userId, userRole } = identity();
    const ticketId = elements.ticketId.value;
    if (!ticketId) throw new Error("请先填写或创建工单编号。");
    setLoading(elements.queryTicket, true, "查询状态");
    const query = new URLSearchParams({ user_id: userId, user_role: userRole });
    const ticket = await request(`/v1/tickets/${ticketId}?${query}`);
    renderTicket(ticket, "查询成功");
  } catch (error) {
    showToast(error.message, true);
  } finally {
    setLoading(elements.queryTicket, false, "查询状态");
  }
});

elements.closeTicket.addEventListener("click", async () => {
  try {
    const { userId, userRole } = identity();
    const ticketId = elements.ticketId.value;
    if (!ticketId) throw new Error("请先填写或创建工单编号。");
    setLoading(elements.closeTicket, true, "关闭工单");
    const ticket = await request(`/v1/tickets/${ticketId}/close`, {
      method: "POST",
      body: JSON.stringify({
        user_id: userId,
        user_role: userRole,
        approved: elements.approval.checked,
      }),
    });
    renderTicket(ticket, "工单已关闭并记录审计日志");
    showToast(`工单 ${ticket.id} 已关闭`);
  } catch (error) {
    showToast(error.message, true);
  } finally {
    setLoading(elements.closeTicket, false, "关闭工单");
  }
});

checkHealth();
