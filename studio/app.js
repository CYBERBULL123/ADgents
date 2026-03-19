/* ─── ADgents Studio — Main Application JS ───────────────────────── */
'use strict';

const API = 'http://localhost:8000/api';
let state = {
    agents: {},
    selectedAgent: null,
    selectedChatAgent: null,
    ws: null,
    skills: [],
    templates: {},
    pendingTaskId: null,
    selectedBuilderSkills: new Set(),
    selectedTemplate: null
};

// ─── Navigation ──────────────────────────────────────────────────────────────
function navigate(page) {
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));

    const pageEl = document.getElementById(`page-${page}`);
    if (pageEl) pageEl.classList.add('active');

    const navEl = document.querySelector(`[data-page="${page}"]`);
    if (navEl) navEl.classList.add('active');

    const titles = {
        dashboard: ['Dashboard', 'Overview of your agent fleet'],
        agents: ['Agents', 'Manage your AI agent personas'],
        builder: ['Build Agent', 'Create a new AI persona'],
        chat: ['Chat', 'Converse with your agents'],
        tasks: ['Tasks', 'Run autonomous workflows'],
        history: ['Task History', 'Browse all past autonomous task runs'],
        memory: ['Memory', "View and manage agents' memories"],
        skills: ['Skills', 'Tools available to your agents'],
        mcp: ['MCP Server', 'Model Context Protocol Integration'],
        adk: ['ADK Integration', 'Agent Development Kit Adapter'],
        settings: ['Settings', 'Configure LLM providers and system'],
        docs: ['Documentation', 'Learn how to use ADgents']
    };

    const [title, desc] = titles[page] || [page, ''];
    document.getElementById('page-title').textContent = title;
    document.getElementById('breadcrumb').textContent = desc;

    // Load page-specific data
    if (page === 'agents') renderAgentsGrid();
    if (page === 'chat') renderChatPicker();
    if (page === 'tasks') populateTaskAgentSelect();
    if (page === 'history') loadHistory();
    if (page === 'memory') populateMemorySelects();
    if (page === 'skills') renderSkillsPage();
    if (page === 'mcp') loadMCPPage();
    if (page === 'adk') loadADKPage();
    if (page === 'settings') loadProviderStatus();
    if (page === 'builder') initBuilder();
    if (page === 'dashboard') updateDashboard();
    if (page === 'docs') {
        if (!state.docsLoaded) loadDocs();
    }
}

// ─── API Helpers ─────────────────────────────────────────────────────────────
async function api(path, method = 'GET', body = null) {
    const opts = {
        method,
        headers: { 'Content-Type': 'application/json' }
    };
    if (body) opts.body = JSON.stringify(body);
    const res = await fetch(`${API}${path}`, opts);
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `HTTP ${res.status}`);
    }
    return res.json();
}

// ─── App Init ─────────────────────────────────────────────────────────────────
async function init() {
    await checkApiStatus();
    await loadSkills();
    await loadTemplates();
    await loadAgents();
    updateDashboard();
    initBuilder();
    setInterval(checkApiStatus, 10000);
}

async function checkApiStatus() {
    try {
        const health = await api('/health');
        const dot = document.getElementById('api-status-dot');
        const text = document.getElementById('api-status-text');
        dot.className = 'status-dot online';
        text.textContent = 'API Connected';

        document.getElementById('status-api').textContent = '✅ Online';
        document.getElementById('status-api').className = 'badge badge-green';
        document.getElementById('status-llm').textContent = health.llm_providers?.join(', ') || 'mock';
        document.getElementById('stat-skills').textContent = health.skills || 0;
        document.getElementById('stat-providers').textContent = health.llm_providers?.length || 1;
    } catch {
        const dot = document.getElementById('api-status-dot');
        const text = document.getElementById('api-status-text');
        dot.className = 'status-dot offline';
        text.textContent = 'API Offline';
        document.getElementById('status-api').textContent = '❌ Offline';
        document.getElementById('status-api').className = 'badge badge-red';
    }
}

async function loadAgents() {
    try {
        const data = await api('/agents');
        state.agents = {};
        (data.agents || []).forEach(a => { state.agents[a.persona.id] = a; });
        updateAgentCount();
        updateDashboard();
    } catch (e) { console.error('Load agents:', e); }
}

async function loadSkills() {
    try {
        const data = await api('/skills');
        state.skills = data.skills || [];
    } catch (e) { console.error('Load skills:', e); }
}

async function loadTemplates() {
    try {
        const data = await api('/templates');
        state.templates = data.templates || {};
    } catch (e) { console.error('Load templates:', e); }
}

function updateAgentCount() {
    const n = Object.keys(state.agents).length;
    document.getElementById('agent-count-badge').textContent = n;
    document.getElementById('stat-agents').textContent = n;
}

async function refreshAll() {
    await loadAgents();
    await checkApiStatus();
    toast('Refreshed', 'info');
}

// ─── Dashboard ────────────────────────────────────────────────────────────────
function updateDashboard() {
    const agents = Object.values(state.agents);
    const listEl = document.getElementById('dashboard-agents-list');

    if (agents.length === 0) {
        listEl.innerHTML = '<div class="empty-state-small">No agents yet. Create your first agent!</div>';
        return;
    }

    listEl.innerHTML = agents.slice(0, 5).map(a => `
    <div class="dash-agent-item" onclick="navigate('chat')">
      <div style="font-size:1.4rem">${a.persona.avatar}</div>
      <div>
        <div style="font-weight:600;font-size:0.9rem">${a.persona.name}</div>
        <div style="font-size:0.75rem;color:var(--text-secondary)">${a.persona.role}</div>
      </div>
      <span class="badge badge-green" style="margin-left:auto">${a.status}</span>
    </div>
  `).join('');

    updateAgentCount();
}

// ─── Agents Grid ──────────────────────────────────────────────────────────────
function renderAgentsGrid(filter = '') {
    const grid = document.getElementById('agents-grid');
    const agents = Object.values(state.agents).filter(a => {
        const q = filter.toLowerCase();
        return !q || a.persona.name.toLowerCase().includes(q) || a.persona.role.toLowerCase().includes(q);
    });

    if (agents.length === 0) {
        grid.innerHTML = `<div class="empty-state" style="grid-column:1/-1">
      <div class="empty-icon">🤖</div>
      <div class="empty-title">No Agents Found</div>
      <div class="empty-desc">${filter ? 'Try a different search' : 'Create your first AI agent to get started'}</div>
      ${!filter ? '<button class="btn btn-primary" onclick="navigate(\'builder\')">Create First Agent</button>' : ''}
    </div>`;
        return;
    }

    grid.innerHTML = agents.map(a => {
        const traits = (a.persona.personality_traits || []).slice(0, 3);
        const skills = (a.available_skills || []).length;
        const mem = a.memory_stats?.episodic_memories || 0;
        return `
      <div class="agent-card" onclick="openAgentChat('${a.persona.id}')">
        <div class="agent-card-header">
          <div class="agent-avatar">${a.persona.avatar}</div>
          <div class="agent-info">
            <div class="agent-name">${a.persona.name}</div>
            <div class="agent-role">${a.persona.role}</div>
          </div>
          <span class="badge badge-${a.status === 'idle' ? 'green' : 'blue'}">${a.status}</span>
        </div>
        <div class="agent-traits">
          ${traits.map(t => `<span class="trait-chip">${t}</span>`).join('')}
        </div>
        <div class="agent-stats-row">
          <div class="agent-stat">
            <div class="agent-stat-val">${skills}</div>
            <div class="agent-stat-lab">Skills</div>
          </div>
          <div class="agent-stat">
            <div class="agent-stat-val">${mem}</div>
            <div class="agent-stat-lab">Memories</div>
          </div>
          <div class="agent-stat">
            <div class="agent-stat-val">${a.persona.autonomy_level}/5</div>
            <div class="agent-stat-lab">Autonomy</div>
          </div>
        </div>
        <div class="agent-actions" onclick="event.stopPropagation()">
          <button class="btn btn-ghost btn-xs" onclick="openAgentChat('${a.persona.id}')">💬 Chat</button>
          <button class="btn btn-ghost btn-xs" onclick="navigate('tasks')">⚡ Task</button>
          <button class="btn btn-ghost btn-xs" onclick="editAgent('${a.persona.id}')">✏️ Edit</button>
          <button class="btn btn-danger btn-xs" onclick="deleteAgent('${a.persona.id}')">🗑️</button>
        </div>
      </div>
    `;
    }).join('');
}

function filterAgents(q) { renderAgentsGrid(q); }

function deleteAgent(id) {
    confirmAction('Delete this agent? Their memories will be preserved.', async () => {
        try {
            await api(`/agents/${id}`, 'DELETE');
            await loadAgents();
            renderAgentsGrid();
            toast('Agent deleted', 'info');
        } catch (e) { toast(e.message, 'error'); }
    });
}

function openAgentChat(id) {
    state.selectedChatAgent = id;
    navigate('chat');
    renderChatPicker();
    selectChatAgent(id);
}

// ─── Builder ──────────────────────────────────────────────────────────────────
function initBuilder() {
    // Templates list
    const tList = document.getElementById('template-list');
    if (!tList) return;

    tList.innerHTML = Object.entries(state.templates).map(([key, t]) => `
    <div class="template-item" id="tpl-${key}" onclick="loadTemplate('${key}')">
      <span class="template-emoji">${t.avatar}</span>
      <div class="template-info">
        <div class="template-tname">${t.name}</div>
        <div class="template-trole">${t.role}</div>
      </div>
    </div>
  `).join('') + `
    <div class="template-item" id="tpl-custom" onclick="clearTemplate()">
      <span class="template-emoji">✍️</span>
      <div class="template-info">
        <div class="template-tname">Custom</div>
        <div class="template-trole">Start from scratch</div>
      </div>
    </div>
  `;

    // Skills checkboxes
    const sGrid = document.getElementById('build-skills-grid');
    if (sGrid && state.skills.length) {
        const catIcons = { information: '🔍', development: '💻', filesystem: '📁', integration: '🔗', utility: '🔧', data: '📊', text: '📝', general: '⚙️' };
        sGrid.innerHTML = state.skills.map(s => `
      <div class="skill-check-item ${state.selectedBuilderSkills.has(s.name) ? 'selected' : ''}" 
        id="skill-check-${s.name}" onclick="toggleSkill('${s.name}')">
        ${catIcons[s.category] || '🔧'} ${s.name}
      </div>
    `).join('');
    }
}

function loadTemplate(key) {
    const t = state.templates[key];
    if (!t) return;

    // Set template as selected
    document.querySelectorAll('.template-item').forEach(el => el.classList.remove('selected'));
    document.getElementById(`tpl-${key}`)?.classList.add('selected');
    state.selectedTemplate = key;

    // Fill form
    document.getElementById('build-name').value = t.name;
    document.getElementById('build-avatar').value = t.avatar;
    document.getElementById('build-role').value = t.role;
    document.getElementById('build-backstory').value = t.backstory || '';
    document.getElementById('build-expertise').value = (t.expertise_domains || []).join(', ');
    document.getElementById('build-traits').value = (t.personality_traits || []).join(', ');
    document.getElementById('build-tone').value = t.tone || 'professional';
    document.getElementById('build-autonomy').value = t.autonomy_level || 3;
    document.getElementById('autonomy-val').textContent = t.autonomy_level || 3;
    document.getElementById('build-creativity').value = Math.round((t.creativity || 0.7) * 100);
    document.getElementById('creativity-val').textContent = Math.round((t.creativity || 0.7) * 100);

    // Set skills
    state.selectedBuilderSkills = new Set(t.skills || []);
    document.querySelectorAll('.skill-check-item').forEach(el => el.classList.remove('selected'));
    state.selectedBuilderSkills.forEach(s => {
        document.getElementById(`skill-check-${s}`)?.classList.add('selected');
    });

    updatePreview();
}

function clearTemplate() {
    document.querySelectorAll('.template-item').forEach(el => el.classList.remove('selected'));
    document.getElementById('tpl-custom')?.classList.add('selected');
    state.selectedTemplate = null;
    state.editingAgentId = null;
    resetBuilder();
    
    const btn = document.querySelector('[onclick="createAgent()"]');
    if (btn) btn.innerHTML = '✨ Create Agent';
}

function editAgent(id) {
    const a = state.agents[id];
    if (!a) return;
    
    navigate('builder');
    
    // Clear template selection
    document.querySelectorAll('.template-item').forEach(el => el.classList.remove('selected'));
    state.selectedTemplate = null;
    state.editingAgentId = id;

    // Fill form
    document.getElementById('build-name').value = a.persona.name;
    document.getElementById('build-avatar').value = a.persona.avatar;
    document.getElementById('build-role').value = a.persona.role;
    document.getElementById('build-backstory').value = a.persona.backstory || '';
    document.getElementById('build-expertise').value = (a.persona.expertise_domains || []).join(', ');
    document.getElementById('build-traits').value = (a.persona.personality_traits || []).join(', ');
    document.getElementById('build-tone').value = a.persona.tone || 'professional';
    document.getElementById('build-autonomy').value = a.persona.autonomy_level || 3;
    document.getElementById('autonomy-val').textContent = a.persona.autonomy_level || 3;
    document.getElementById('build-creativity').value = Math.round((a.persona.creativity || 0.7) * 100);
    document.getElementById('creativity-val').textContent = Math.round((a.persona.creativity || 0.7) * 100);

    // Set skills
    state.selectedBuilderSkills = new Set(a.persona.skills || []);
    document.querySelectorAll('.skill-check-item').forEach(el => el.classList.remove('selected'));
    state.selectedBuilderSkills.forEach(s => {
        document.getElementById(`skill-check-${s}`)?.classList.add('selected');
    });

    updatePreview();
    
    // Switch button to updating mode
    const btn = document.querySelector('[onclick="createAgent()"]');
    if (btn) btn.innerHTML = '💾 Save Changes';
}

function toggleSkill(name) {
    const el = document.getElementById(`skill-check-${name}`);
    if (state.selectedBuilderSkills.has(name)) {
        state.selectedBuilderSkills.delete(name);
        el?.classList.remove('selected');
    } else {
        state.selectedBuilderSkills.add(name);
        el?.classList.add('selected');
    }
}

function updatePreview() {
    const name = document.getElementById('build-name')?.value || 'Your Agent';
    const avatar = document.getElementById('build-avatar')?.value || '🤖';
    const role = document.getElementById('build-role')?.value || 'Define the role below';
    document.getElementById('preview-name').textContent = name;
    document.getElementById('preview-avatar').textContent = avatar;
    document.getElementById('preview-role').textContent = role;
}

function resetBuilder() {
    ['build-name', 'build-role', 'build-backstory', 'build-expertise', 'build-traits'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.value = '';
    });
    document.getElementById('build-avatar').value = '🤖';
    document.getElementById('build-autonomy').value = 3;
    document.getElementById('autonomy-val').textContent = 3;
    document.getElementById('build-creativity').value = 70;
    document.getElementById('creativity-val').textContent = 70;
    state.selectedBuilderSkills = new Set();
    document.querySelectorAll('.skill-check-item').forEach(el => el.classList.remove('selected'));
    updatePreview();
}

async function createAgent() {
    const name = document.getElementById('build-name')?.value?.trim();
    const role = document.getElementById('build-role')?.value?.trim();

    if (!name) { toast('Please enter an agent name', 'error'); return; }
    if (!role) { toast('Please enter a role/title', 'error'); return; }

    const persona = {
        name,
        avatar: document.getElementById('build-avatar')?.value?.trim() || '🤖',
        role,
        backstory: document.getElementById('build-backstory')?.value?.trim() || '',
        expertise_domains: (document.getElementById('build-expertise')?.value || '').split(',').map(s => s.trim()).filter(Boolean),
        personality_traits: (document.getElementById('build-traits')?.value || '').split(',').map(s => s.trim()).filter(Boolean),
        tone: document.getElementById('build-tone')?.value || 'professional',
        autonomy_level: parseInt(document.getElementById('build-autonomy')?.value || 3),
        creativity: parseInt(document.getElementById('build-creativity')?.value || 70) / 100,
        skills: [...state.selectedBuilderSkills],
        communication_style: `${document.getElementById('build-tone')?.value} and clear`
    };

    try {
        const btn = document.querySelector('[onclick="createAgent()"]');
        if (btn) { btn.disabled = true; btn.textContent = state.editingAgentId ? 'Saving...' : 'Creating...'; }

        if (state.editingAgentId) {
            const result = await api(`/agents/${state.editingAgentId}/persona`, 'PUT', { agent_id: state.editingAgentId, updates: persona });
            // Update local state completely, because avatar/name might have changed
            if(state.agents[state.editingAgentId]) {
                state.agents[state.editingAgentId].persona = result.persona;
            }
            toast(`✨ ${name} updated successfully!`, 'success');
        } else {
            const result = await api('/agents', 'POST', { persona });
            state.agents[result.agent.persona.id] = result.agent;
            toast(`✨ ${name} is ready!`, 'success');
        }
        
        updateAgentCount();
        updateDashboard();
        resetBuilder();
        clearTemplate(); // resets editing mode

        // Auto-navigate to agents view
        setTimeout(() => { navigate('agents'); renderAgentsGrid(); }, 500);
    } catch (e) {
        toast(e.message, 'error');
    } finally {
        const btn = document.querySelector('[onclick="createAgent()"]');
        if (btn) { btn.disabled = false; btn.innerHTML = state.editingAgentId ? '💾 Save Changes' : '✨ Create Agent'; }
    }
}

async function quickCreateAgent(template) {
    try {
        const result = await api('/agents', 'POST', { template });
        state.agents[result.agent.persona.id] = result.agent;
        updateAgentCount();
        updateDashboard();
        toast(`✨ ${result.agent.persona.name} is ready!`, 'success');
    } catch (e) { toast(e.message, 'error'); }
}

// ─── Chat ─────────────────────────────────────────────────────────────────────
function renderChatPicker() {
    const picker = document.getElementById('chat-agent-picker');
    const agents = Object.values(state.agents);

    if (agents.length === 0) {
        picker.innerHTML = '<div class="empty-state-small">Create an agent first</div>';
        return;
    }

    picker.innerHTML = agents.map(a => `
    <div class="agent-pick-item ${a.persona.id === state.selectedChatAgent ? 'selected' : ''}" 
      onclick="selectChatAgent('${a.persona.id}')">
      <div class="pick-avatar">${a.persona.avatar}</div>
      <div>
        <div class="pick-name">${a.persona.name}</div>
        <div class="pick-role">${a.persona.role}</div>
      </div>
    </div>
  `).join('');
}

function selectChatAgent(id) {
    state.selectedChatAgent = id;
    const agent = state.agents[id];
    if (!agent) return;

    // Update UI
    document.getElementById('chat-avatar').textContent = agent.persona.avatar;
    document.getElementById('chat-agent-name').textContent = agent.persona.name;
    document.getElementById('chat-agent-status').innerHTML = `<span class="dot dot-green"></span> Ready`;

    // Re-render picker to update selection
    document.querySelectorAll('.agent-pick-item').forEach(el => el.classList.remove('selected'));
    document.querySelector(`[onclick="selectChatAgent('${id}')"]`)?.classList.add('selected');

    // Clear messages
    const msgs = document.getElementById('messages-container');
    msgs.innerHTML = `<div style="text-align:center;padding:2rem;color:var(--text-muted);font-size:0.85rem">
    Chatting with <strong style="color:var(--text-secondary)">${agent.persona.name}</strong> — ${agent.persona.role}
  </div>`;

    // Connect WebSocket
    connectWebSocket(id);
}

function connectWebSocket(agentId) {
    if (state.ws) { state.ws.close(); state.ws = null; }

    try {
        const ws = new WebSocket(`ws://localhost:8000/ws/${agentId}`);
        ws.onopen = () => { state.ws = ws; };
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.type === 'chat_response') {
                removeThinkingBubble();
                appendMessage('agent', data.response);
                document.getElementById('chat-agent-status').innerHTML = `<span class="dot dot-green"></span> Ready`;
            }
            if (data.type === 'thought_step') {
                addTaskStep(data.step);
            }
            if (data.type === 'task_complete') {
                handleTaskComplete(data);
            }
            if (data.type === 'task_error') {
                setTaskRunning(false);
                toast('Task error: ' + (data.error || 'Unknown'), 'error');
            }
        };
        ws.onerror = () => { state.ws = null; };
        ws.onclose = () => { state.ws = null; };
    } catch (e) { console.log('WS not available, using REST'); }
}

async function sendMessage() {
    const input = document.getElementById('chat-input');
    const msg = input.value.trim();
    if (!msg || !state.selectedChatAgent) {
        if (!state.selectedChatAgent) toast('Select an agent first', 'error');
        return;
    }

    input.value = '';
    input.style.height = 'auto';
    appendMessage('user', msg);

    const agent = state.agents[state.selectedChatAgent];
    document.getElementById('chat-agent-status').innerHTML = `<span class="dot dot-yellow"></span> Thinking...`;

    // Show thinking indicator
    appendThinkingBubble(agent?.persona?.avatar || '🤖');

    // Try WebSocket first, fallback to REST
    if (state.ws && state.ws.readyState === WebSocket.OPEN) {
        state.ws.send(JSON.stringify({ type: 'chat', message: msg }));
    } else {
        try {
            const res = await api('/chat', 'POST', { agent_id: state.selectedChatAgent, message: msg });
            removeThinkingBubble();
            appendMessage('agent', res.response);
            document.getElementById('chat-agent-status').innerHTML = `<span class="dot dot-green"></span> Ready`;
        } catch (e) {
            removeThinkingBubble();
            appendMessage('agent', `⚠️ Error: ${e.message}`);
            document.getElementById('chat-agent-status').innerHTML = `<span class="dot dot-green"></span> Ready`;
        }
    }
}

function handleChatKey(e) {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
    // Auto-resize
    const ta = e.target;
    ta.style.height = 'auto';
    ta.style.height = Math.min(ta.scrollHeight, 120) + 'px';
}

function appendMessage(role, content) {
    const container = document.getElementById('messages-container');
    const agent = state.agents[state.selectedChatAgent];
    const isUser = role === 'user';
    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    const div = document.createElement('div');
    div.className = `message ${isUser ? 'user' : 'agent'}`;
    const bubbleContent = isUser ? escapeHtml(content) : renderMarkdown(content);
    div.innerHTML = `
    <div class="msg-avatar ${isUser ? 'user-av' : 'agent-av'}">${isUser ? '👤' : (agent?.persona?.avatar || '🤖')}</div>
    <div style="flex:1;min-width:0">
      <div class="msg-bubble ${isUser ? '' : 'md-bubble'}">${bubbleContent}</div>
      <div class="msg-time">${time}</div>
    </div>
  `;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

function appendThinkingBubble(avatar) {
    const container = document.getElementById('messages-container');
    const div = document.createElement('div');
    div.className = 'message agent';
    div.id = 'thinking-bubble';
    div.innerHTML = `
    <div class="msg-avatar agent-av">${avatar}</div>
    <div class="msg-bubble thinking-bubble">
      <div class="thinking-dot"></div>
      <div class="thinking-dot"></div>
      <div class="thinking-dot"></div>
    </div>
  `;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

function removeThinkingBubble() {
    document.getElementById('thinking-bubble')?.remove();
}

async function resetChatSession() {
    if (!state.selectedChatAgent) return;
    try {
        await api(`/agents/${state.selectedChatAgent}/reset`, 'POST');
        selectChatAgent(state.selectedChatAgent); // Re-init chat
        toast('Session reset', 'info');
    } catch (e) { toast(e.message, 'error'); }
}

// ─── Tasks ────────────────────────────────────────────────────────────────────
function populateTaskAgentSelect() {
    const sel = document.getElementById('task-agent-select');
    if (!sel) return;
    const agents = Object.values(state.agents);
    sel.innerHTML = '<option value="">— Select Agent —</option>' +
        agents.map(a => `<option value="${a.persona.id}">${a.persona.avatar} ${a.persona.name} (${a.persona.role})</option>`).join('');
}

async function startTask() {
    const agentId = document.getElementById('task-agent-select')?.value;
    const taskDesc = document.getElementById('task-description')?.value?.trim();
    const maxIter = parseInt(document.getElementById('task-max-iter')?.value || 10);

    if (!agentId) { toast('Select an agent', 'error'); return; }
    if (!taskDesc) { toast('Enter a task description', 'error'); return; }

    const agentForTask = state.agents[agentId];
    setTaskRunning(true, agentForTask?.persona?.name);

    // Clear steps
    const stepsEl = document.getElementById('task-steps');
    stepsEl.innerHTML = '<div class="task-step thought"><div class="step-header"><span class="step-type">🚀</span><span class="step-type thought">Starting task...</span></div><div class="step-content">' + escapeHtml(taskDesc) + '</div></div>';

    // Connect WebSocket for real-time steps
    if (!state.ws || state.ws.readyState !== WebSocket.OPEN) {
        connectWebSocket(agentId);
        await new Promise(r => setTimeout(r, 300)); // Let WS connect
    }

    try {
        const res = await api('/tasks', 'POST', { agent_id: agentId, task: taskDesc, max_iterations: maxIter });
        state.pendingTaskId = res.task_id;
        toast(`Task started for ${state.agents[agentId]?.persona?.name}`, 'success');
        setTimeout(() => setTaskRunning(false, agentForTask?.persona?.name), 30000);
    } catch (e) { toast(e.message, 'error'); }
}

function addTaskStep(step) {
    const stepsEl = document.getElementById('task-steps');
    // Remove empty state if present
    const emptyState = stepsEl.querySelector('.task-empty-state');
    if (emptyState) emptyState.remove();

    const icons = { thought: '💭', action: '⚡', observation: '👁️', reflection: '🔮' };
    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    const div = document.createElement('div');
    div.className = `task-step ${step.step_type || 'thought'}`;

    let bodyHtml = '';
    if (step.skill_used) {
        bodyHtml += `<span class="step-skill-badge">🔧 ${escapeHtml(step.skill_used)}</span><br>`;
    }
    const stepMd = step.step_type === 'thought' || step.step_type === 'reflection'
        ? renderMarkdown(step.content || '')
        : escapeHtml(step.content || '');
    bodyHtml += `<div class="step-content md-content">${stepMd}</div>`;
    if (step.skill_result) {
        bodyHtml += `<div class="step-result-box">${escapeHtml(step.skill_result.substring(0, 300))}${step.skill_result.length > 300 ? '…' : ''}</div>`;
    }

    div.innerHTML = `
    <div class="step-header">
      <span>${icons[step.step_type] || '•'}</span>
      <span class="step-type">${step.step_type || 'thought'}</span>
      <span style="margin-left:auto;font-size:0.65rem;color:var(--text-muted)">${time}</span>
    </div>
    ${bodyHtml}
  `;

    stepsEl.appendChild(div);
    stepsEl.scrollTop = stepsEl.scrollHeight;
}

async function runAutonomousTask() {
    if (!state.selectedChatAgent) { toast('Select an agent first', 'error'); return; }
    
    const chatInput = document.getElementById('chat-input');
    let task = chatInput.value.trim();
    if (!task) {
        toast('Please enter a task description in the message box first! ⚡', 'info');
        chatInput.focus();
        return;
    }
    
    // Clear the input
    chatInput.value = '';
    chatInput.style.height = 'auto';

    navigate('tasks');
    document.getElementById('task-agent-select').value = state.selectedChatAgent;
    document.getElementById('task-description').value = task;
    await startTask();
}

// ─── Memory ───────────────────────────────────────────────────────────────────
function populateMemorySelects() {
    const agents = Object.values(state.agents);
    const selects = ['memory-agent-select', 'learn-agent-select'];

    selects.forEach(selId => {
        const sel = document.getElementById(selId);
        if (!sel) return;
        sel.innerHTML = '<option value="">— Select Agent —</option>' +
            agents.map(a => `<option value="${a.persona.id}">${a.persona.avatar} ${a.persona.name}</option>`).join('');
    });
}

async function loadMemory(query = '') {
    const agentId = document.getElementById('memory-agent-select')?.value;
    if (!agentId) return;

    try {
        const q = query ? `?query=${encodeURIComponent(query)}&limit=20` : '?limit=20';
        const data = await api(`/agents/${agentId}/memory${q}`);
        renderMemoryGrid(data.memories || []);
    } catch (e) { toast(e.message, 'error'); }
}

function searchMemory(q) {
    if (q.length > 2 || q.length === 0) loadMemory(q);
}

function renderMemoryGrid(memories) {
    const grid = document.getElementById('memory-grid');
    if (memories.length === 0) {
        grid.innerHTML = '<div class="empty-state-small">No memories found</div>';
        return;
    }

    const typeColors = { episodic: 'blue', semantic: 'purple', procedural: 'green' };
    grid.innerHTML = memories.map(m => `
    <div class="memory-card">
      <div class="memory-type-badge">
        <span class="badge badge-${typeColors[m.type] || 'blue'}">${m.type}</span>
      </div>
      <div class="memory-content">${escapeHtml(m.summary || m.content).substring(0, 200)}${m.content.length > 200 ? '...' : ''}</div>
      <div class="memory-tags">
        ${(m.tags || []).map(t => `<span class="memory-tag">${t}</span>`).join('')}
      </div>
      <div class="memory-footer">
        <span class="memory-importance">⭐ ${Math.round(m.importance * 100)}% importance</span>
        <button class="btn btn-danger btn-xs" onclick="deleteMemory('${m.id}')">🗑️</button>
      </div>
    </div>
  `).join('');
}

async function deleteMemory(memId) {
    const agentId = document.getElementById('memory-agent-select')?.value;
    if (!agentId) return;
    try {
        await api(`/agents/${agentId}/memory/${memId}`, 'DELETE');
        loadMemory();
        toast('Memory deleted', 'info');
    } catch (e) { toast(e.message, 'error'); }
}

async function teachAgent() {
    const agentId = document.getElementById('learn-agent-select')?.value;
    const fact = document.getElementById('learn-fact')?.value?.trim();
    const topic = document.getElementById('learn-topic')?.value?.trim() || 'general';

    if (!agentId) { toast('Select an agent', 'error'); return; }
    if (!fact) { toast('Enter something to teach', 'error'); return; }

    try {
        await api(`/agents/${agentId}/learn`, 'POST', { agent_id: agentId, fact, topic });
        document.getElementById('learn-fact').value = '';
        toast('Agent learned the new knowledge! 🧠', 'success');

        if (document.getElementById('memory-agent-select')?.value === agentId) loadMemory();
    } catch (e) { toast(e.message, 'error'); }
}

// ─── Skills ───────────────────────────────────────────────────────────────────
function renderSkillsPage() {
    const grid = document.getElementById('skills-grid-full');
    if (!grid || !state.skills.length) return;

    const catIcons = { information: '🔍', development: '💻', filesystem: '📁', integration: '🔗', utility: '🔧', data: '📊', text: '📝', general: '⚙️' };
    const catColors = { information: 'blue', development: 'purple', filesystem: 'green', integration: 'orange', utility: 'blue', data: 'purple', text: 'green' };

    grid.innerHTML = state.skills.map(s => `
    <div class="skill-card">
      <div class="skill-card-header">
        <div class="skill-cat-icon" style="background:rgba(124,58,237,0.1)">${catIcons[s.category] || '🔧'}</div>
        <div>
          <div class="skill-name">${s.name}</div>
          <div class="skill-cat">
            <span class="badge badge-${catColors[s.category] || 'blue'}">${s.category}</span>
          </div>
        </div>
      </div>
      <div class="skill-desc">${s.description}</div>
    </div>
  `).join('');
}

// ─── Settings ─────────────────────────────────────────────────────────────────
async function loadProviderStatus() {
    try {
        const status = await api('/llm/status');
        const el = document.getElementById('provider-status-list');
        if (!el) return;

        el.innerHTML = Object.entries(status).map(([name, info]) => `
      <div class="status-item">
        <span class="status-name">${name}</span>
        <span class="badge badge-${info.available ? 'green' : 'red'}">
          ${info.available ? '✅ Available' : '❌ Not configured'}
          ${info.default ? ' ★ Default' : ''}
        </span>
      </div>
    `).join('');
    } catch (e) { console.error(e); }
}

async function saveLLMConfig() {
    const provider = document.getElementById('llm-provider')?.value;
    const api_key = document.getElementById('llm-api-key')?.value?.trim();
    const model = document.getElementById('llm-model')?.value?.trim();

    if (!api_key && provider !== 'ollama') {
        toast('Enter an API key', 'error');
        return;
    }

    const statusEl = document.getElementById('llm-config-status');
    statusEl.innerHTML = '<span class="badge badge-blue">Saving...</span>';

    try {
        await api('/llm/configure', 'POST', { provider, api_key, model: model || undefined });
        statusEl.innerHTML = '<span class="badge badge-green">✅ Configured successfully</span>';
        toast(`${provider} configured!`, 'success');
        loadProviderStatus();
    } catch (e) {
        statusEl.innerHTML = `<span class="badge badge-red">❌ ${e.message}</span>`;
        toast(e.message, 'error');
    }
}

// ─── Toast ────────────────────────────────────────────────────────────────────
function toast(message, type = 'info') {
    const icons = { success: '✅', error: '❌', info: 'ℹ️' };
    const container = document.getElementById('toast-container');
    const div = document.createElement('div');
    div.className = `toast ${type}`;
    div.innerHTML = `<span>${icons[type] || 'ℹ️'}</span><span>${escapeHtml(message)}</span>`;
    container.appendChild(div);
    setTimeout(() => {
        div.style.animation = 'toastOut 0.3s ease forwards';
        setTimeout(() => div.remove(), 300);
    }, 3500);
}

// ─── Confirm Action Modal ─────────────────────────────────────────────────────
function confirmAction(message, onConfirm) {
    document.getElementById('confirm-modal-message').innerHTML = escapeHtml(message);
    const modal = document.getElementById('confirm-action-modal');
    modal.style.display = 'flex';
    
    const yesBtn = document.getElementById('confirm-modal-yes');
    const noBtn = document.getElementById('confirm-modal-no');
    
    // Clone to remove previous event listeners easily
    const yesClone = yesBtn.cloneNode(true);
    const noClone = noBtn.cloneNode(true);
    yesBtn.parentNode.replaceChild(yesClone, yesBtn);
    noBtn.parentNode.replaceChild(noClone, noBtn);
    
    yesClone.onclick = () => {
        closeConfirmModal();
        if(onConfirm) onConfirm();
    };
    noClone.onclick = () => closeConfirmModal();
}

function closeConfirmModal() {
    const modal = document.getElementById('confirm-action-modal');
    if (modal) modal.style.display = 'none';
}

// ─── Utilities ────────────────────────────────────────────────────────────────
function escapeHtml(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/\n/g, '<br>');
}

// ─── Start ────────────────────────────────────────────────────────────────────

// ─── Custom Skill Creator ───────────────────────────────────────────────────
function toggleSkillForm() {
    const form = document.getElementById('skill-create-form');
    const btn = document.getElementById('skill-form-toggle-btn');
    const shown = form.style.display !== 'none';
    form.style.display = shown ? 'none' : 'block';
    btn.textContent = shown ? '+ Add Skill' : '✕ Close';
}

async function createCustomSkill() {
    const name = document.getElementById('skill-name')?.value?.trim();
    const description = document.getElementById('skill-description')?.value?.trim();
    const category = document.getElementById('skill-category')?.value || 'custom';
    const paramStr = document.getElementById('skill-parameters')?.value?.trim();
    const handlerCode = document.getElementById('skill-handler-code')?.value?.trim();

    if (!name) { toast('Skill name is required', 'error'); return; }
    if (!description) { toast('Description is required', 'error'); return; }
    if (!handlerCode) { toast('Handler code is required', 'error'); return; }
    if (!/^[a-z_][a-z0-9_]*$/.test(name)) {
        toast('Name must be lowercase letters, numbers, and underscores only', 'error'); return;
    }

    let parameters = {};
    try { if (paramStr) parameters = JSON.parse(paramStr); }
    catch (e) { toast('Parameters JSON is invalid: ' + e.message, 'error'); return; }

    const btn = document.querySelector('[onclick="createCustomSkill()"]');
    if (btn) { btn.disabled = true; btn.textContent = 'Registering...'; }

    try {
        await api('/skills/register', 'POST', { name, description, category, parameters, handler_code: handlerCode });
        toast('🔧 Skill registered: ' + name, 'success');
        await loadSkills();
        renderSkillsPage();
        // Reset form fields
        ['skill-name', 'skill-description', 'skill-handler-code'].forEach(id => {
            const el = document.getElementById(id); if (el) el.value = '';
        });
        document.getElementById('skill-category').value = 'custom';
        document.getElementById('skill-parameters').value = JSON.stringify(
            { type: 'object', properties: { input: { type: 'string', description: 'Input value' } }, required: ['input'] }, null, 2
        );
        toggleSkillForm();
        // Refresh builder skills grid
        const sGrid = document.getElementById('build-skills-grid');
        if (sGrid) initBuilder();
    } catch (e) {
        toast(e.message, 'error');
    } finally {
        if (btn) { btn.disabled = false; btn.textContent = '🔧 Register Skill'; }
    }
}

// ─── AI Skill Generator ───────────────────────────────────────────────────────
async function generateSkillFromAI() {
    const promptEl = document.getElementById('skill-ai-prompt');
    const prompt = promptEl?.value?.trim();
    if (!prompt) { toast('Please describe the skill you want to generate', 'error'); return; }

    const statusEl = document.getElementById('skill-ai-status');
    const btn = document.getElementById('generate-skill-btn');
    
    statusEl.style.display = 'block';
    statusEl.innerHTML = '✨ Generating Python code with AI... ⏳';
    if (btn) btn.disabled = true;

    try {
        const response = await api('/skills/generate', 'POST', { description: prompt });
        if (response.success && response.code) {
            // Fill the manual form with the generated data
            
            // Generate a reasonable name from the prompt (very simple slug)
            const generatedName = prompt.toLowerCase().replace(/[^a-z0-9]+/g, '_').substring(0, 20).replace(/^_|_$/g, '') || 'ai_generated_skill';
            document.getElementById('skill-name').value = generatedName;
            document.getElementById('skill-description').value = prompt;
            document.getElementById('skill-handler-code').value = response.code;
            
            // Setup generic params JSON
            document.getElementById('skill-parameters').value = JSON.stringify({
                type: "object",
                properties: {
                    input: { type: "string", description: "Input data for the skill" }
                }
            }, null, 2);
            
            statusEl.innerHTML = '✅ Code generated! Review and click Register.';
            statusEl.style.color = 'var(--green)';
            
            // Scroll to the code editor
            document.getElementById('skill-handler-code').scrollIntoView({ behavior: 'smooth', block: 'center' });
            
            toast('AI Skill generated successfully! Please review the code.', 'success');
        } else {
            throw new Error(response.message || 'Failed to generate code');
        }
    } catch (e) {
        statusEl.innerHTML = `❌ Error: ${e.message}`;
        statusEl.style.color = 'var(--red)';
        toast(e.message, 'error');
    } finally {
        if (btn) btn.disabled = false;
        setTimeout(() => {
            if(statusEl.style.color === 'var(--green)') {
                statusEl.style.display = 'none';
                statusEl.style.color = 'var(--text-secondary)';
            }
        }, 5000);
    }
}

function deleteCustomSkill(name) {
    confirmAction('Delete custom skill "' + name + '"?', async () => {
        try {
            await api('/skills/' + name, 'DELETE');
            await loadSkills();
            renderSkillsPage();
            toast('Skill "' + name + '" deleted', 'info');
        } catch (e) { toast(e.message, 'error'); }
    });
}

// ─── Skills Page Render (overrides previous version) ─────────────────────────
function renderSkillsPage() {
    const grid = document.getElementById('skills-grid-full');
    if (!grid) return;
    const countEl = document.getElementById('skills-count');
    if (countEl) countEl.textContent = state.skills.length;
    if (!state.skills.length) {
        grid.innerHTML = "<div class='empty-state-small'>No skills loaded</div>"; return;
    }
    const catIcons = { information: '🔍', development: '💻', filesystem: '📁', integration: '🔗', utility: '🔧', data: '📊', text: '📝', general: '⚙️', custom: '✨', business: '💼' };
    const catColors = { information: 'blue', development: 'purple', filesystem: 'green', integration: 'orange', utility: 'blue', data: 'purple', text: 'green', custom: 'orange', business: 'blue' };
    grid.innerHTML = state.skills.map(s => {
        const isCustom = s.category === 'custom' || s.is_custom;
        const safeS = escapeHtml(JSON.stringify(s));  // not used directly in onclick
        return `<div class="skill-card ${isCustom ? 'custom-skill' : ''}" onclick="showSkillModal(${JSON.stringify(s.name)})">
      <div class="skill-card-header">
        <div class="skill-cat-icon" style="background:rgba(124,58,237,0.1)">${catIcons[s.category] || '🔧'}</div>
        <div style="flex:1;min-width:0">
          <div class="skill-name">${escapeHtml(s.name)}</div>
          <div class="skill-cat">
            <span class="badge badge-${catColors[s.category] || 'blue'}">${escapeHtml(s.category)}</span>
            ${isCustom ? '<span class="badge badge-orange" style="margin-left:0.3rem">✨ custom</span>' : ''}
          </div>
        </div>
      </div>
      <div class="skill-desc">${escapeHtml(s.description)}</div>
      ${isCustom ? `<div class="skill-card-footer"><button class="btn btn-danger btn-xs" onclick="event.stopPropagation();deleteCustomSkill('${escapeHtml(s.name)}')">Delete</button></div>` : ''}
    </div>`;
    }).join('');
}

function showSkillModal(skillName) {
    const s = state.skills.find(x => x.name === skillName);
    if (!s) return;
    document.getElementById('modal-skill-name').textContent = s.name;
    const params = s.parameters ? JSON.stringify(s.parameters, null, 2) : 'None';
    const handler = s.handler_code || '';
    document.getElementById('modal-skill-body').innerHTML =
        `<div class="modal-row"><span class="modal-key">Category</span><span class="modal-val"><span class="badge badge-blue">${escapeHtml(s.category)}</span></span></div>
     <div class="modal-row"><span class="modal-key">Description</span><span class="modal-val">${escapeHtml(s.description)}</span></div>
     <div class="modal-row" style="flex-direction:column;gap:0.4rem"><span class="modal-key">Parameters</span><pre>${escapeHtml(params)}</pre></div>
     ${handler ? `<div class="modal-row" style="flex-direction:column;gap:0.4rem"><span class="modal-key">Handler Code</span><pre>${escapeHtml(handler)}</pre></div>` : ''}`;
    document.getElementById('skill-modal').style.display = 'flex';
}

function closeSkillModal(e) {
    if (e.target.id === 'skill-modal') document.getElementById('skill-modal').style.display = 'none';
}

// ─── Task Feed Helpers ────────────────────────────────────────────────────────
function clearTaskFeed() {
    const stepsEl = document.getElementById('task-steps');
    stepsEl.innerHTML = `<div class="task-empty-state">
    <div class="task-empty-icon">⚡</div>
    <div class="task-empty-title">Ready for Tasks</div>
    <div class="task-empty-desc">Select an agent, describe the task, then hit Run.<br>Watch the agent's thoughts appear here in real-time.</div>
  </div>`;
    const badge = document.getElementById('task-status-badge');
    if (badge) badge.style.display = 'none';
    document.getElementById('task-feed-heading').textContent = 'Task Steps';
    // Also hide the result panel
    closeTaskResult();
}

function setTaskRunning(running, agentName) {
    const badge = document.getElementById('task-status-badge');
    const heading = document.getElementById('task-feed-heading');
    if (badge) {
        badge.style.display = running ? 'inline' : 'none';
        badge.textContent = running ? '⏳ Running' : '✅ Done';
        badge.className = running ? 'badge badge-blue' : 'badge badge-green';
    }
    if (heading) heading.textContent = running ? (agentName ? agentName + "'s thoughts" : 'Running...') : 'Task Steps';
}



// ─── Mobile Sidebar ──────────────────────────────────────────────────────────
function openSidebar() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebar-overlay');
    const hamBtn = document.getElementById('hamburger-btn');
    if (!sidebar) return;
    sidebar.classList.add('open');
    if (overlay) overlay.classList.add('active');
    if (hamBtn) hamBtn.setAttribute('aria-expanded', 'true');
    document.body.style.overflow = 'hidden';  // prevent background scroll
}

function closeSidebar() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebar-overlay');
    const hamBtn = document.getElementById('hamburger-btn');
    if (!sidebar) return;
    sidebar.classList.remove('open');
    if (overlay) overlay.classList.remove('active');
    if (hamBtn) hamBtn.setAttribute('aria-expanded', 'false');
    document.body.style.overflow = '';
}

// Close sidebar with Escape key
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeSidebar();
});

// Auto-close sidebar when resizing to desktop width
window.addEventListener('resize', () => {
    if (window.innerWidth > 900) closeSidebar();
});


// ─── Markdown Renderer ───────────────────────────────────────────────────────
function renderMarkdown(text) {
    if (!text) return '';
    try {
        if (typeof marked !== 'undefined' && typeof DOMPurify !== 'undefined') {
            const parsed = marked.parse(text, {
                breaks: true,
                gfm: true
            });
            return DOMPurify.sanitize(parsed);
        }
    } catch (e) { console.warn('Markdown render error:', e); }
    // Fallback: basic escaping + newlines
    return '<p>' + escapeHtml(text).replace(/\n\n/g, '</p><p>').replace(/\n/g, '<br>') + '</p>';
}

// ─── Model hint updater ───────────────────────────────────────────────────────
function updateModelHint() {
    const provider = document.getElementById('llm-provider')?.value;
    const input = document.getElementById('llm-model');
    const hint = document.getElementById('llm-model-hint');
    const defaults = {
        openai: 'gpt-4o-mini',
        gemini: 'gemini-1.5-flash',
        claude: 'claude-3-5-sonnet-20241022',
        ollama: 'llama3'
    };
    if (input) input.placeholder = defaults[provider] || 'model-name';
    if (hint) hint.textContent = `(default: ${defaults[provider] || 'varies'})`;
}

// ─── WebSocket task complete handler ─────────────────────────────────────────
function handleTaskComplete(data) {
    setTaskRunning(false);
    const task = data.task || {};
    const result = task.result || '';
    const isFailed = task.status === 'failed' || task.error;

    const panel = document.getElementById('task-result-panel');
    const body = document.getElementById('task-result-body');
    const agentNameEl = document.getElementById('task-result-agent-name');
    const headerEl = panel?.querySelector('.task-result-header');
    const iconEl = panel?.querySelector('.task-result-icon');
    const labelEl = panel?.querySelector('.task-result-label');

    // Fill in the agent name
    const agentId = document.getElementById('task-agent-select')?.value;
    const agent = state.agents[agentId];
    if (agentNameEl && agent) {
        agentNameEl.textContent = `${agent.persona.avatar || '🤖'} ${agent.persona.name}`;
    }

    if (isFailed) {
        // Style as error
        if (iconEl) iconEl.textContent = '❌';
        if (labelEl) { labelEl.textContent = 'Task Failed'; labelEl.style.color = 'var(--red)'; }
        if (headerEl) {
            headerEl.style.background = 'linear-gradient(90deg, rgba(239,68,68,0.1), transparent)';
            headerEl.style.borderBottomColor = 'rgba(239,68,68,0.2)';
        }
        if (panel) {
            panel.style.borderColor = 'rgba(239,68,68,0.35)';
            panel.style.boxShadow = '0 0 40px rgba(239,68,68,0.1), 0 8px 32px rgba(0,0,0,0.4)';
        }
        const errorText = task.error || result || 'An unknown error occurred.';
        body.innerHTML = `<div style="color:var(--red);font-weight:600;margin-bottom:0.5rem">⚠️ Error Details</div>` +
            `<pre style="background:rgba(239,68,68,0.06);border:1px solid rgba(239,68,68,0.2);border-radius:8px;padding:1rem;white-space:pre-wrap;word-break:break-word;font-size:0.82rem;color:#fca5a5">${escapeHtml(errorText)}</pre>` +
            `<div style="margin-top:1rem;font-size:0.85rem;color:var(--text-secondary)">Check the <strong>Task Steps</strong> above for an <strong style="color:#f87171">LLM Error</strong> observation which shows the exact API error.</div>`;
        toast('Task failed ❌', 'error');
    } else {
        // Success style (default green)
        if (iconEl) iconEl.textContent = '✅';
        if (labelEl) { labelEl.textContent = 'Task Complete'; labelEl.style.color = 'var(--green)'; }
        if (headerEl) {
            headerEl.style.background = '';
            headerEl.style.borderBottomColor = '';
        }
        if (panel) { panel.style.borderColor = ''; panel.style.boxShadow = ''; }

        const displayResult = result && result.trim()
            ? result
            : '_No result text was returned. Check the Task Steps above for observations._';
        body.innerHTML = renderMarkdown(displayResult);
        toast('Task completed! ✅', 'success');
    }

    // Show the panel with a smooth slide-in
    panel.style.display = 'block';
    panel.classList.add('result-animate-in');
    panel.scrollIntoView({ behavior: 'smooth', block: 'start' });

    // Store for copy
    panel._resultText = result || task.error || '';

    // Keep History badge updated in background
    loadHistory().catch(() => { });
}

function copyTaskResult() {
    const panel = document.getElementById('task-result-panel');
    const text = panel?._resultText || document.getElementById('task-result-body')?.innerText || '';
    if (!text) { toast('Nothing to copy', 'info'); return; }
    navigator.clipboard.writeText(text).then(
        () => toast('Result copied to clipboard! 📋', 'success'),
        () => toast('Could not copy', 'error')
    );
}

function closeTaskResult() {
    const panel = document.getElementById('task-result-panel');
    if (panel) {
        panel.classList.remove('result-animate-in');
        panel.style.display = 'none';
    }
}

// ─── Task History ─────────────────────────────────────────────────────────────

let _histSearchTimer = null;
function filterHistoryDebounced(q) {
    clearTimeout(_histSearchTimer);
    _histSearchTimer = setTimeout(() => loadHistory(q), 350);
}

async function loadHistory(searchOverride) {
    const search = searchOverride !== undefined ? searchOverride
        : document.getElementById('history-search')?.value || '';
    const agentId = document.getElementById('history-filter-agent')?.value || '';
    const status = document.getElementById('history-filter-status')?.value || '';

    try {
        // Load stats
        const stats = await api('/tasks/stats');
        document.getElementById('hstat-total').textContent = stats.total || 0;
        document.getElementById('hstat-completed').textContent = stats.completed || 0;
        document.getElementById('hstat-failed').textContent = stats.failed || 0;
        const avg = stats.avg_duration_s || 0;
        document.getElementById('hstat-avg').textContent = avg >= 60
            ? `${(avg / 60).toFixed(1)}m` : `${avg.toFixed(0)}s`;

        // Populate agent filter from loaded agents
        const agentSel = document.getElementById('history-filter-agent');
        if (agentSel && Object.keys(state.agents).length) {
            const cur = agentSel.value;
            agentSel.innerHTML = '<option value="">All Agents</option>' +
                Object.values(state.agents).map(a =>
                    `<option value="${a.persona.id}">${a.persona.avatar} ${a.persona.name}</option>`
                ).join('');
            agentSel.value = cur;
        }

        // Build query params
        let qs = `?limit=100`;
        if (agentId) qs += `&agent_id=${encodeURIComponent(agentId)}`;
        if (status) qs += `&status=${encodeURIComponent(status)}`;
        if (search) qs += `&search=${encodeURIComponent(search)}`;

        const data = await api(`/tasks${qs}`);
        renderHistoryList(data.tasks || []);

        // Update nav badge
        const badge = document.getElementById('history-count-badge');
        if (badge) {
            badge.textContent = stats.total || 0;
            badge.style.display = stats.total ? '' : 'none';
        }
    } catch (e) {
        console.error('History load error:', e);
    }
}

function renderHistoryList(tasks) {
    const listEl = document.getElementById('history-list');
    if (!tasks.length) {
        listEl.innerHTML = `<div class="task-empty-state">
            <div class="task-empty-icon">📜</div>
            <div class="task-empty-title">No Tasks Found</div>
            <div class="task-empty-desc">Run an autonomous task and it will appear here.</div>
        </div>`;
        return;
    }

    const stepIcons = { thought: '💭', action: '⚡', observation: '👁️', reflection: '🔮' };

    listEl.innerHTML = tasks.map(t => {
        const isOk = t.status === 'completed';
        const statusBadge = isOk
            ? `<span class="badge badge-green">✅ completed</span>`
            : `<span class="badge badge-red">❌ ${escapeHtml(t.status)}</span>`;
        const duration = t.duration_s != null
            ? (t.duration_s >= 60 ? `${(t.duration_s / 60).toFixed(1)}m` : `${t.duration_s.toFixed(0)}s`)
            : '—';
        const date = t.started_at ? new Date(t.started_at + 'Z').toLocaleString() : '';
        const preview = (isOk ? t.result : t.error) || '';
        const previewText = preview.length > 200 ? preview.slice(0, 200) + '…' : preview;
        const stepCount = (t.steps || []).length;

        const stepsHtml = (t.steps || []).map(s => `
            <div class="hist-step ${s.step_type || 'thought'}">
                <span class="hist-step-icon">${stepIcons[s.step_type] || '•'}</span>
                <span class="hist-step-type">${s.step_type || ''}</span>
                ${s.skill_used ? `<span class="step-skill-badge">🔧 ${escapeHtml(s.skill_used)}</span>` : ''}
                <span class="hist-step-content">${escapeHtml((s.content || '').slice(0, 150))}${(s.content || '').length > 150 ? '…' : ''}</span>
            </div>`).join('');

        return `<div class="hist-card" id="histcard-${t.id}">
            <div class="hist-card-header" onclick="toggleHistCard('${t.id}')">
                <div class="hist-card-left">
                    <span class="hist-avatar">${escapeHtml(t.agent_avatar || '🤖')}</span>
                    <div class="hist-meta">
                        <div class="hist-task-text">${escapeHtml(t.task_text)}</div>
                        <div class="hist-sub">
                            <span class="hist-agent-name">${escapeHtml(t.agent_name)}</span>
                            <span class="hist-dot">·</span>
                            ${statusBadge}
                            <span class="hist-dot">·</span>
                            <span class="hist-time">${escapeHtml(date)}</span>
                            <span class="hist-dot">·</span>
                            <span class="hist-duration">⏱ ${duration}</span>
                            <span class="hist-dot">·</span>
                            <span style="color:var(--text-muted);font-size:0.72rem">${stepCount} steps</span>
                        </div>
                    </div>
                </div>
                <div class="hist-card-actions" onclick="event.stopPropagation()">
                    <button class="btn btn-ghost btn-xs" onclick="copyHistResult('${t.id}')" title="Copy result">📋</button>
                    <button class="btn btn-danger btn-xs" onclick="deleteHistTask('${t.id}')" title="Delete">🗑️</button>
                    <span class="hist-chevron" id="hist-chev-${t.id}">▼</span>
                </div>
            </div>
            <div class="hist-card-body" id="hist-body-${t.id}" style="display:none">
                ${previewText ? `<div class="hist-result-preview md-content">${renderMarkdown(preview)}</div>` : ''}
                ${stepsHtml ? `<div class="hist-steps-section">
                    <div class="hist-steps-label">Task Steps</div>
                    <div class="hist-steps-list">${stepsHtml}</div>
                </div>` : ''}
            </div>
        </div>`;
    }).join('');

    // Store result text keyed by task id for copy
    window._histResults = {};
    tasks.forEach(t => { window._histResults[t.id] = (t.result || t.error || ''); });
}

function toggleHistCard(id) {
    const body = document.getElementById(`hist-body-${id}`);
    const chev = document.getElementById(`hist-chev-${id}`);
    if (!body) return;
    const open = body.style.display !== 'none';
    body.style.display = open ? 'none' : 'block';
    if (chev) chev.textContent = open ? '▼' : '▲';
}

function deleteHistTask(id) {
    confirmAction('Delete this task from history?', async () => {
        try {
            await api(`/tasks/${id}`, 'DELETE');
            document.getElementById(`histcard-${id}`)?.remove();
            toast('Task deleted from history', 'info');
            loadHistory();
        } catch (e) { toast(e.message, 'error'); }
    });
}

function copyHistResult(id) {
    const text = window._histResults?.[id] || '';
    if (!text) { toast('Nothing to copy', 'info'); return; }
    navigator.clipboard.writeText(text).then(
        () => toast('Result copied! 📋', 'success'),
        () => toast('Could not copy', 'error')
    );
}

// ─── Documentation ─────────────────────────────────────────────────────────────
async function loadDocs() {
    try {
        const data = await api('/docs');
        const docs = data.docs || [];
        state.docsLoaded = true;
        
        // Preferred ordering if these files exist
        const order = ['index', 'quickstart', 'architecture', 'studio', 'sdk', 'skills', 'use_cases', 'crew', 'mcp_adk', 'deployment'];
        docs.sort((a, b) => {
            const idxA = order.indexOf(a);
            const idxB = order.indexOf(b);
            if (idxA !== -1 && idxB !== -1) return idxA - idxB;
            if (idxA !== -1) return -1;
            if (idxB !== -1) return 1;
            return a.localeCompare(b);
        });

        const listEl = document.getElementById('docs-nav-list');
        if (!listEl) return;
        
        listEl.innerHTML = docs.map(d => {
            const label = d === 'index' ? 'Overview' : (d.charAt(0).toUpperCase() + d.slice(1));
            return `<li class="docs-nav-item" id="nav-doc-${d}" onclick="loadDocContent('${d}')">${escapeHtml(label)}</li>`;
        }).join('');
        
        if (docs.length > 0) {
            loadDocContent('index');
        } else {
            document.getElementById('docs-content').innerHTML = '<div class="empty-state-small">No documentation found.</div>';
        }
    } catch (e) {
        toast('Failed to load docs list: ' + e.message, 'error');
    }
}

async function loadDocContent(name) {
    // Top highlight state
    document.querySelectorAll('.docs-nav-item').forEach(el => el.classList.remove('active'));
    const navEl = document.getElementById(`nav-doc-${name}`);
    if (navEl) navEl.classList.add('active');
    
    const contentEl = document.getElementById('docs-content');
    contentEl.innerHTML = 'Loading...';
    
    try {
        const data = await api(`/docs/${name}`);
        if(data.success) {
            contentEl.innerHTML = renderMarkdown(data.content);
            // Intercept links inside the rendered markdown to enable internal routing
            contentEl.querySelectorAll('a').forEach(aEl => {
                const href = aEl.getAttribute('href');
                if (href) {
                    if (href.endsWith('.md')) {
                        // Internal document link
                        aEl.onclick = (e) => {
                            e.preventDefault();
                            const docName = href.replace('.md', '');
                            loadDocContent(docName);
                        };
                    } else if (href.startsWith('http')) {
                        // External links should open in new tab securely
                        aEl.target = '_blank';
                        aEl.rel = 'noopener noreferrer';
                    }
                }
            });
        }
    } catch (e) {
        contentEl.innerHTML = `<div class="empty-state-small">Failed to load ${escapeHtml(name)}.<br>${escapeHtml(e.message)}</div>`;
    }
}

// ─── MCP (Model Context Protocol) ─────────────────────────────────────────────

async function loadMCPPage() {
    try {
        // Load MCP status
        const statusData = await api('/mcp/status');
        const statusDiv = document.getElementById('mcp-status');
        
        if (statusData.success) {
            statusDiv.innerHTML = `
                <div><strong>Server Name:</strong> ${escapeHtml(statusData.server_name)}</div>
                <div><strong>Version:</strong> ${escapeHtml(statusData.version)}</div>
                <div><strong>Status:</strong> <span class="badge ${statusData.running ? 'badge-green' : 'badge-red'}">${statusData.running ? 'Running' : 'Stopped'}</span></div>
                <div><strong>Protocols:</strong> ${statusData.supported_protocols.join(', ')}</div>
                <div><strong>Available Tools:</strong> ${statusData.available_tools}</div>
                <div><strong>Registered Agents:</strong> ${statusData.available_agents}</div>
            `;
        }
        
        // Load MCP tools
        const toolsData = await api('/mcp/tools');
        const toolsList = document.getElementById('mcp-tools-list');
        const toolsCount = document.getElementById('mcp-tools-count');
        
        if (toolsData.success && toolsData.tools.length > 0) {
            toolsCount.textContent = toolsData.tools.length;
            toolsList.innerHTML = toolsData.tools.map(tool => {
                const paramsCount = tool.input_schema.properties ? Object.keys(tool.input_schema.properties).length : 0;
                return `
                <div>
                    <div>🔧 ${escapeHtml(tool.name)}</div>
                    <div>${escapeHtml(tool.description)}</div>
                    <div>
                        <strong>Schema:</strong> ${tool.input_schema.type} • 
                        <strong>Parameters:</strong> ${paramsCount}
                    </div>
                </div>
            `}).join('');
        } else {
            toolsList.innerHTML = '<div class="empty-state-small">No tools available yet</div>';
        }
    } catch (e) {
        toast('Failed to load MCP data: ' + e.message, 'error');
    }
}

function saveMCPConfig() {
    const mode = document.getElementById('mcp-mode').value;
    const port = document.getElementById('mcp-port').value;
    
    api('/mcp/configure', 'POST', { mode, port })
        .then(data => {
            if (data.success) {
                toast('MCP configuration saved successfully', 'success');
            } else {
                toast('Failed to save configuration: ' + data.error, 'error');
            }
        })
        .catch(e => toast('Failed to save MCP config: ' + e.message, 'error'));
}

function toggleMCPServer() {
    const toggle = document.getElementById('mcp-toggle-text');
    const isRunning = toggle.textContent === 'Stop Server';
    const endpoint = isRunning ? '/mcp/stop' : '/mcp/start';
    
    api(endpoint, 'POST', {})
        .then(data => {
            if (data.success) {
                if (data.running) {
                    toggle.textContent = 'Stop Server';
                    toast('MCP Server started successfully', 'success');
                } else {
                    toggle.textContent = 'Start Server';
                    toast('MCP Server stopped', 'success');
                }
                // Refresh status
                loadMCPData();
            } else {
                toast('Error: ' + data.error, 'error');
            }
        })
        .catch(e => {
            toast('Failed to toggle MCP server: ' + e.message, 'error');
        });
}

// ─── ADK (Agent Development Kit) ───────────────────────────────────────────────

async function loadADKPage() {
    try {
        // Load ADK status
        const statusData = await api('/adk/status');
        const statusDiv = document.getElementById('adk-status');
        
        if (statusData.success) {
            statusDiv.innerHTML = `
                <div style="margin-bottom: 1rem;"><strong>Status:</strong> <span class="badge ${statusData.total_agents > 0 ? 'badge-green' : 'badge-orange'}">${statusData.total_agents > 0 ? 'Ready' : 'No Agents'}</span></div>
                <div style="margin-bottom: 1rem;"><strong>Available Agents:</strong> <strong style="color: var(--accent);">${statusData.total_agents}</strong></div>
                <div style="margin-bottom: 1rem;"><strong>Framework:</strong> <span class="badge badge-blue">Google ADK</span></div>
                <div><strong>Support Level:</strong> <span class="badge badge-blue">Full</span></div>
            `;
            
            if (statusData.total_agents === 0) {
                statusDiv.innerHTML += `<div style="margin-top: 1rem; padding: 0.75rem; background: var(--bg-input); border-radius: 6px; color: var(--text-secondary); font-size: 0.85rem;">No agents available. <a href="javascript:navigate('agents')" style="color: var(--accent);">Create an agent first</a></div>`;
            }
        } else {
            statusDiv.innerHTML = `<div class="badge badge-red">Error: ${statusData.error || 'Failed to load'}</div>`;
        }
        
        // Load available agents for selection
        const agentsDiv = document.getElementById('adk-agents-list');
        const selectDiv = document.getElementById('adk-test-agent');
        
        if (statusData.success && statusData.agents && statusData.agents.length > 0) {
            agentsDiv.innerHTML = statusData.agents.map(agent => `
                <div style="background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius-sm); padding: 0.75rem;">
                    <div style="font-weight: 600; color: var(--accent);">${escapeHtml(agent.name)}</div>
                    <div style="font-size: 0.8rem; color: var(--text-muted); margin-top: 0.3rem;">Role: ${escapeHtml(agent.role || 'Agent')}</div>
                </div>
            `).join('');
            
            selectDiv.innerHTML = '<option value="">Choose an agent...</option>' + statusData.agents.map(agent => 
                `<option value="${escapeHtml(agent.id)}">${escapeHtml(agent.name)}</option>`
            ).join('');
        } else {
            agentsDiv.innerHTML = '<div style="padding: 1rem; text-align: center; color: var(--text-secondary);">➕ <a href="javascript:navigate(\'agents\')" style="color: var(--accent);">Create an agent</a> to get started with ADK</div>';
            selectDiv.innerHTML = '<option value="">No agents available</option>';
        }
    } catch (e) {
        const statusDiv = document.getElementById('adk-status');
        statusDiv.innerHTML = `<div class="badge badge-red">Error: ${e.message}</div>`;
        document.getElementById('adk-agents-list').innerHTML = `<div style="color: var(--text-secondary);">Failed to load agents</div>`;
    }
}

async function runADKTest() {
    const agentId = document.getElementById('adk-test-agent').value;
    const prompt = document.getElementById('adk-test-prompt').value;
    
    if (!agentId) {
        toast('Please select an agent', 'warning');
        return;
    }
    
    if (!prompt.trim()) {
        toast('Please enter a prompt', 'warning');
        return;
    }
    
    const resultDiv = document.getElementById('adk-test-result');
    const outputDiv = document.getElementById('adk-test-output');
    
    resultDiv.style.display = 'none';
    outputDiv.textContent = 'Running...';
    
    try {
        const response = await api('/adk/run-agent', 'POST', { agent_id: agentId, prompt });
        
        if (response.success) {
            outputDiv.textContent = response.response.text;
            resultDiv.style.display = 'block';
            toast('ADK test completed successfully');
        } else {
            throw new Error(response.error || 'Unknown error');
        }
    } catch (e) {
        outputDiv.textContent = 'Error: ' + e.message;
        resultDiv.style.display = 'block';
        toast('ADK test failed: ' + e.message, 'error');
    }
}

window.addEventListener('DOMContentLoaded', init);
