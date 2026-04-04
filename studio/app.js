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
        files: ['Files', 'Browse and download agent-created files'],
        mcp: ['MCP Server', 'Model Context Protocol Integration'],
        adk: ['ADK Workflows', 'Google ADK agent orchestration'],
        crews: ['Crew Collaboration', 'Multi-agent team coordination'],
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
    if (page === 'adk') loadADKPage();
    if (page === 'crews') loadCrewsPage();
    if (page === 'history') loadHistory();
    if (page === 'files') loadFiles();
    if (page === 'memory') populateMemorySelects();
    if (page === 'skills') renderSkillsPage();
    if (page === 'mcp') loadMCPPage();
    if (page === 'settings') {
        updateDBConnectionFields();

        // Load saved preferences
        document.getElementById('org-name').value = localStorage.getItem('org_name') || '';
        document.getElementById('memory-type').value = localStorage.getItem('memory_type') || 'multi_tier';
        document.getElementById('auto-save').checked = localStorage.getItem('auto_save') === 'true';

        // Restore saved provider dropdown (model will be restored after models load)
        const savedProvider = localStorage.getItem('llm_provider');
        if (savedProvider) {
            document.getElementById('llm-provider').value = savedProvider;
        }

        // Load providers info banner + all models (restore selection happens after load)
        loadConfiguredProviders();
    }
    if (page === 'builder') initBuilder();
    if (page === 'dashboard') updateDashboard();
    if (page === 'docs') {
        if (!state.docsLoaded) loadDocs();
    }
}

// ─── API Helpers ─────────────────────────────────────────────────────────────
async function api(path, method = 'GET', body = null, timeout = 10000) {
    const opts = {
        method,
        headers: { 'Content-Type': 'application/json' }
    };
    if (body) opts.body = JSON.stringify(body);
    
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);
    
    try {
        const res = await fetch(`${API}${path}`, { ...opts, signal: controller.signal });
        clearTimeout(timeoutId);
        
        if (!res.ok) {
            let errorMsg = `HTTP ${res.status}`;
            try {
                const err = await res.json();
                // Handle Pydantic validation errors
                if (err.detail) {
                    if (Array.isArray(err.detail)) {
                        errorMsg = err.detail.map(d => `${d.loc?.join('.')}: ${d.msg}`).join('; ');
                    } else {
                        errorMsg = err.detail;
                    }
                } else if (err.error) {
                    errorMsg = err.error;
                }
            } catch (parseErr) {
                // Response wasn't JSON, keep default message
            }
            throw new Error(errorMsg);
        }
        return res.json();
    } catch (e) {
        clearTimeout(timeoutId);
        if (e.name === 'AbortError') {
            throw new Error(`Request timeout for ${path} (${timeout}ms)`);
        }
        throw e;
    }
}

// ─── App Init ─────────────────────────────────────────────────────────────────
async function init() {
    try {
        const updateLoadingStatus = (msg) => {
            const el = document.getElementById('loading-status');
            if (el) el.textContent = msg;
            console.log('[ADgents]', msg);
        };
        
        updateLoadingStatus('Initializing application...');
        
        // Set a timeout for the entire init sequence
        const initPromise = Promise.race([
            (async () => {
                updateLoadingStatus('Checking API status...');
                console.log('[ADgents] Checking API status...');
                await checkApiStatus();
                
                updateLoadingStatus('Loading skills...');
                console.log('[ADgents] Loading skills...');
                await loadSkills();
                
                updateLoadingStatus('Loading templates...');
                console.log('[ADgents] Loading templates...');
                await loadTemplates();
                
                updateLoadingStatus('Loading agents...');
                console.log('[ADgents] Loading agents...');
                await loadAgents();
                
                updateLoadingStatus('Updating dashboard...');
                console.log('[ADgents] Updating dashboard...');
                updateDashboard();
                
                updateLoadingStatus('Initializing builder...');
                console.log('[ADgents] Initializing builder...');
                initBuilder();
                
                console.log('[ADgents] Initialization complete!');
                return true;
            })(),
            new Promise((_, reject) => 
                setTimeout(() => reject(new Error('Initialization timeout after 30 seconds')), 30000)
            )
        ]);
        
        await initPromise;
        
        // Hide loading overlay
        const overlay = document.getElementById('app-loading-overlay');
        if (overlay) {
            overlay.style.opacity = '0';
            overlay.style.transition = 'opacity 0.3s ease';
            setTimeout(() => overlay.style.display = 'none', 300);
        }
        
        // Set up task tab listeners
        initTaskTabListeners();
        
        // Set up periodic API status checks
        setInterval(checkApiStatus, 10000);
        
    } catch (e) {
        console.error('[ADgents] Initialization error:', e);
        
        // Update loading overlay to show error
        const overlay = document.getElementById('app-loading-overlay');
        if (overlay) {
            overlay.innerHTML = `
                <div style="text-align: center; color: #e0e0e0; font-family: 'Inter', sans-serif;">
                    <div style="font-size: 2rem; margin-bottom: 1rem;">⚠️</div>
                    <div style="font-size: 1.2rem; font-weight: 600; margin-bottom: 0.5rem;">Initialization Error</div>
                    <div style="color: #8b8ba8; margin-bottom: 1rem; max-width: 400px;">
                        <div>${e.message || 'An error occurred during initialization'}</div>
                    </div>
                    <div style="font-size: 0.85rem; color: #4f4f6e; margin-bottom: 1.5rem;">
                        Check your console (F12) for details. The dashboard may still load with limited functionality.
                    </div>
                    <button onclick="location.reload()" style="background: #7c3aed; color: white; border: none; padding: 0.5rem 1.5rem; border-radius: 6px; cursor: pointer;">Retry</button>
                </div>
            `;
        }
        
        // Try to at least show the dashboard anyway
        try {
            updateDashboard();
            initBuilder();
            
            // Hide overlay after 3 seconds
            if (overlay) {
                setTimeout(() => {
                    overlay.style.opacity = '0';
                    overlay.style.transition = 'opacity 0.3s ease';
                    setTimeout(() => overlay.style.display = 'none', 300);
                }, 3000);
            }
        } catch (e2) {
            console.error('[ADgents] Failed to update UI:', e2);
        }
    }
}

async function checkApiStatus() {
    try {
        console.log('[ADgents] Checking API health...');
        const health = await api('/health', 'GET', null, 5000);
        
        const dot = document.getElementById('api-status-dot');
        const text = document.getElementById('api-status-text');
        dot.className = 'status-dot online';
        text.textContent = 'API Connected';

        // Update main status
        document.getElementById('status-api').textContent = '✅ Online';
        document.getElementById('status-api').className = 'badge badge-green';
        
        // Update database status
        document.getElementById('status-db').textContent = `✅ ${health.database_status || 'SQLite Ready'}`;
        document.getElementById('status-db').className = 'badge badge-green';
        
        // Update skills engine status
        document.getElementById('status-skills-engine').textContent = '✅ Active';
        document.getElementById('status-skills-engine').className = 'badge badge-green';
        
        // Update LLM providers count
        const availableLLMs = health.llm_providers?.length || 0;
        document.getElementById('status-llm').textContent = `${availableLLMs}/${health.llm_total || 0} Ready`;
        document.getElementById('status-llm').className = availableLLMs > 0 ? 'badge badge-green' : 'badge badge-orange';
        
        // Update stats
        document.getElementById('stat-skills').textContent = health.skills || 0;
        document.getElementById('stat-agents').textContent = health.agents || 0;
        document.getElementById('stat-providers').textContent = availableLLMs || 0;
        
        // Detailed LLM providers
        const llmDetailEl = document.getElementById('llm-status-details');
        if (health.llm_details && Object.keys(health.llm_details).length > 0) {
            llmDetailEl.innerHTML = Object.entries(health.llm_details).map(([name, info]) => {
                const status = info.available ? '✅' : '❌';
                const isDefault = info.is_default ? ' (default)' : '';
                return `<div class="status-item" style="padding:0.5rem 0;"><span>${status} ${name}${isDefault}</span></div>`;
            }).join('');
        } else {
            llmDetailEl.innerHTML = '<div class="status-item">No providers configured</div>';
        }
        
        console.log('[ADgents] API health check passed');
    } catch (e) {
        console.error('[ADgents] API health check failed:', e);
        const dot = document.getElementById('api-status-dot');
        const text = document.getElementById('api-status-text');
        dot.className = 'status-dot offline';
        text.textContent = 'API Offline: ' + (e.message || 'Connection failed');
        document.getElementById('status-api').textContent = '❌ Offline';
        document.getElementById('status-api').className = 'badge badge-red';
        document.getElementById('status-db').textContent = '❓ Unknown';
        document.getElementById('status-db').className = 'badge badge-red';
        document.getElementById('status-skills-engine').textContent = '❓ Unknown';
        document.getElementById('status-skills-engine').className = 'badge badge-red';
    }
}

async function loadAgents() {
    try {
        const data = await api('/agents');
        state.agents = {};
        (data.agents || []).forEach(a => { 
            state.agents[a.persona.id] = a;
        });
        updateAgentCount();
        updateDashboard();
        console.log(`[ADgents] Loaded ${Object.keys(state.agents).length} agents`);
    } catch (e) { 
        console.error('[ADgents] Error loading agents:', e);
        // Continue with empty agents list
        state.agents = {};
        updateAgentCount();
    }
}

async function loadSkills() {
    try {
        const data = await api('/skills');
        state.skills = data.skills || [];
        console.log(`[ADgents] Loaded ${state.skills.length} skills`);
    } catch (e) { 
        console.error('[ADgents] Error loading skills:', e);
        state.skills = [];
    }
}

async function loadTemplates() {
    try {
        const data = await api('/templates');
        state.templates = data.templates || {};
        console.log(`[ADgents] Loaded ${Object.keys(state.templates).length} templates`);
    } catch (e) { 
        console.error('[ADgents] Error loading templates:', e);
        state.templates = {};
    }
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
    
    // Update memory stats
    let totalMemories = 0;
    agents.forEach(a => {
        const episodic = a.memory_stats?.episodic_memories || 0;
        const semantic = a.memory_stats?.semantic_memories || 0;
        totalMemories += episodic + semantic;
    });
    document.getElementById('stat-memories').textContent = totalMemories;

    if (agents.length === 0) {
        listEl.innerHTML = '<div class="empty-state-small">No agents yet. Create your first agent!</div>';
        return;
    }

    listEl.innerHTML = agents.slice(0, 5).map(a => `
    <div class="dash-agent-item" onclick="navigate('chat')" style="padding: 0.75rem; border-radius: var(--radius-sm); background: var(--bg-card); border: 1px solid var(--border); margin-bottom: 0.5rem; display: flex; align-items: center; cursor: pointer; transition: all 0.2s;">
      <div style="font-size:1.4rem; margin-right: 0.75rem;">${a.persona.avatar}</div>
      <div style="flex: 1;">
        <div style="font-weight:600;font-size:0.9rem;color:var(--text-primary)">${a.persona.name}</div>
        <div style="font-size:0.75rem;color:var(--text-secondary)">${a.persona.role}</div>
      </div>
      <span class="badge badge-green" style="margin-left:auto;">${a.status || 'active'}</span>
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
        const isDeepAgent = a.is_deep_agent || false;
        return `
      <div class="agent-card" onclick="openAgentChat('${a.persona.id}')">
        <div class="agent-card-header">
          <div class="agent-avatar">${a.persona.avatar}</div>
          <div class="agent-info">
            <div class="agent-name">${a.persona.name}</div>
            <div class="agent-role">${a.persona.role}</div>
          </div>
          <div style="display: flex; gap: 0.5rem; flex-wrap: wrap; align-items: center;">
            ${isDeepAgent ? '<span class="badge" style="background: rgba(139, 92, 246, 0.2); color: #8b5cf6; font-size: 0.7rem;">🧠 Deep</span>' : ''}
            <span class="badge badge-${a.status === 'idle' ? 'green' : 'blue'}">${a.status}</span>
          </div>
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
          <button class="btn btn-ghost btn-xs" onclick="toggleAgentDeepMode('${a.persona.id}', ${!isDeepAgent})" title="${isDeepAgent ? 'Disable' : 'Enable'} Deep Agent">${isDeepAgent ? '🧠 Deep' : '🔧 Regular'}</button>
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

async function toggleAgentDeepMode(agentId, enable) {
    try {
        const result = await api(`/agents/${agentId}/deep-agent?enable=${enable}`, 'PUT');
        if (result.success) {
            // Update the agent in state
            state.agents[agentId] = result.agent;
            renderAgentsGrid();
            const mode = enable ? 'enabled 🧠' : 'disabled';
            toast(`Deep Agent ${mode}`, 'success');
        } else {
            toast(result.error || 'Failed to toggle deep agent mode', 'error');
        }
    } catch (e) {
        toast('Error: ' + e.message, 'error');
    }
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
    document.getElementById('build-deep-agent').checked = false;
    state.selectedBuilderSkills = new Set();
    document.querySelectorAll('.skill-check-item').forEach(el => el.classList.remove('selected'));
    updatePreview();
}

function toggleDeepAgent() {
    const checkbox = document.getElementById('build-deep-agent');
    checkbox.checked = !checkbox.checked;
}

async function createAgent() {
    const name = document.getElementById('build-name')?.value?.trim();
    const role = document.getElementById('build-role')?.value?.trim();

    if (!name) { toast('Please enter an agent name', 'error'); return; }
    if (!role) { toast('Please enter a role/title', 'error'); return; }

    const isDeepAgent = document.getElementById('build-deep-agent')?.checked || false;

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
            const result = await api('/agents', 'POST', { persona, is_deep_agent: isDeepAgent });
            state.agents[result.agent.id] = result.agent;
            toast(`✨ ${name} is ready!${isDeepAgent ? ' 🧠 (Deep Agent powered by LangChain)' : ''}`, 'success');
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
// ─── Task Execution (Normal & Deep Agent) ─────────────────────────────────

function initTaskTabListeners() {
    console.log('[DEBUG] Initializing task tab listeners...');
    const normalTab = document.getElementById('tab-normal-agent');
    const deepTab = document.getElementById('tab-deep-agent');
    
    if (normalTab) {
        normalTab.addEventListener('click', (e) => {
            console.log('[DEBUG] Normal tab clicked');
            e.preventDefault();
            switchTaskTab('normal');
        });
    } else {
        console.error('[ERROR] Normal tab button not found');
    }
    
    if (deepTab) {
        deepTab.addEventListener('click', (e) => {
            console.log('[DEBUG] Deep tab clicked');
            e.preventDefault();
            switchTaskTab('deep');
        });
    } else {
        console.error('[ERROR] Deep tab button not found');
    }
}

function switchTaskTab(mode) {
    console.log('[DEBUG] switchTaskTab called with mode:', mode);
    
    const normalPanel = document.getElementById('panel-normal-agent');
    const deepPanel = document.getElementById('panel-deep-agent');
    const normalTab = document.getElementById('tab-normal-agent');
    const deepTab = document.getElementById('tab-deep-agent');
    
    if (!normalPanel || !deepPanel || !normalTab || !deepTab) {
        console.error('[ERROR] One or more elements not found');
        console.error('normalPanel:', normalPanel, 'deepPanel:', deepPanel, 'normalTab:', normalTab, 'deepTab:', deepTab);
        return;
    }
    
    if (mode === 'normal') {
        normalPanel.style.display = 'block';
        deepPanel.style.display = 'none';
        normalTab.classList.add('active');
        normalTab.style.borderBottomColor = 'var(--accent)';
        normalTab.style.color = 'var(--text-primary)';
        deepTab.classList.remove('active');
        deepTab.style.borderBottomColor = 'transparent';
        deepTab.style.color = 'var(--text-secondary)';
        console.log('[DEBUG] Switched to Normal Agent tab');
    } else if (mode === 'deep') {
        normalPanel.style.display = 'none';
        deepPanel.style.display = 'block';
        normalTab.classList.remove('active');
        normalTab.style.borderBottomColor = 'transparent';
        normalTab.style.color = 'var(--text-secondary)';
        deepTab.classList.add('active');
        deepTab.style.borderBottomColor = '#8b5cf6';
        deepTab.style.color = 'var(--text-primary)';
        console.log('[DEBUG] Switched to Deep Agent tab');
    }
    clearTaskFeed();
}

function populateTaskAgentSelect() {
    const selNormal = document.getElementById('task-agent-select');
    const selDeep = document.getElementById('task-deep-agent-select');
    
    // For normal agents - show all agents
    if (selNormal) {
        const agents = Object.values(state.agents);
        selNormal.innerHTML = '<option value="">— Select Agent —</option>' +
            agents.map(a => `<option value="${a.persona.id}">${a.persona.avatar} ${a.persona.name} (${a.persona.role})</option>`).join('');
    }
    
    // For deep agents - only show agents with is_deep_agent=true
    if (selDeep) {
        const deepAgents = Object.values(state.agents).filter(a => a.is_deep_agent === true);
        if (deepAgents.length === 0) {
            selDeep.innerHTML = '<option value="">— No Deep Agents Available —</option><option value="">Create one in Builder with "Enable Deep Agent"</option>';
        } else {
            selDeep.innerHTML = '<option value="">— Select Deep Agent —</option>' +
                deepAgents.map(a => `<option value="${a.persona.id}">🧠 ${a.persona.avatar} ${a.persona.name}</option>`).join('');
        }
    }
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
        toast(`⚡ Normal Agent Task started for ${state.agents[agentId]?.persona?.name}`, 'success');
        setTimeout(() => setTaskRunning(false, agentForTask?.persona?.name), 30000);
    } catch (e) { toast(e.message, 'error'); }
}

async function startDeepTask() {
    const agentId = document.getElementById('task-deep-agent-select')?.value;
    const taskDesc = document.getElementById('task-deep-description')?.value?.trim();
    const maxSteps = parseInt(document.getElementById('task-max-deep-steps')?.value || 10);

    if (!agentId) { toast('Select a Deep Agent', 'error'); return; }
    if (!taskDesc) { toast('Enter a task description', 'error'); return; }

    const agentForTask = state.agents[agentId];
    setTaskRunning(true, agentForTask?.persona?.name);

    // Clear steps
    const stepsEl = document.getElementById('task-steps');
    stepsEl.innerHTML = '<div class="task-step thought"><div class="step-header"><span class="step-type">🚀</span><span class="step-type thought">🧠 Starting Deep Agent Task...</span></div><div class="step-content">' + escapeHtml(taskDesc) + '</div></div>';

    // Connect WebSocket for real-time steps
    if (!state.ws || state.ws.readyState !== WebSocket.OPEN) {
        connectWebSocket(agentId);
        await new Promise(r => setTimeout(r, 300)); // Let WS connect
    }

    try {
        // For deep agents, send a special flag to enable deep agent mode
        const res = await api('/tasks', 'POST', { 
            agent_id: agentId, 
            task: taskDesc, 
            max_iterations: maxSteps,
            use_deep_agent: true  // Flag to use deep agent execution
        });
        state.pendingTaskId = res.task_id;
        toast(`🧠 Deep Agent Task started for ${state.agents[agentId]?.persona?.name}`, 'success');
        setTimeout(() => setTaskRunning(false, agentForTask?.persona?.name), 60000);
    } catch (e) { toast(e.message, 'error'); }
}

// Helper function to convert file paths in text to download links
function convertFilePathsToLinks(text) {
    // Match patterns like "to data/files/filename.txt" or "to data\files\filename.txt"
    const filePathPattern = /(to|in)\s+([\w\/\\.-]+\.(txt|md|json|csv|log|py|js|html|css|xml|yaml|yml))/gi;
    return text.replace(filePathPattern, (match, prefix, filePath) => {
        const encodedPath = encodeURIComponent(filePath.replace(/\\/g, '/'));
        return `${prefix} <a href="/api/files/download?path=${encodedPath}" download style="color:#10b981;text-decoration:underline;font-weight:600;cursor:pointer" title="Click to download">${filePath}</a>`;
    });
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
    
    // Render step content
    let stepContent = step.content || '';
    if (step.step_type === 'thought' || step.step_type === 'reflection') {
        bodyHtml += `<div class="step-content md-content">${renderMarkdown(stepContent)}</div>`;
    } else {
        // For observations/actions, convert file paths to download links
        const escapedContent = escapeHtml(stepContent);
        const contentWithLinks = convertFilePathsToLinks(escapedContent);
        bodyHtml += `<div class="step-content md-content">${contentWithLinks}</div>`;
    }
    
    if (step.skill_result) {
        // Convert file paths to download links in skill results
        const resultText = escapeHtml(step.skill_result.substring(0, 300));
        const resultWithLinks = convertFilePathsToLinks(resultText);
        bodyHtml += `<div class="step-result-box">${resultWithLinks}${step.skill_result.length > 300 ? '…' : ''}</div>`;
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

// ─── Files ────────────────────────────────────────────────────────────────────
let allFiles = [];

async function loadFiles() {
    try {
        const data = await api('/files/list');
        allFiles = data.files || [];
        renderFilesGrid(allFiles);
        
        // Update badge
        const badge = document.getElementById('files-count-badge');
        if (badge) {
            if (allFiles.length > 0) {
                badge.textContent = allFiles.length;
                badge.style.display = '';
            } else {
                badge.style.display = 'none';
            }
        }
    } catch (e) {
        console.error('Failed to load files:', e);
        const grid = document.getElementById('files-grid');
        if (grid) grid.innerHTML = '<div class="empty-state-small">Failed to load files</div>';
    }
}

async function refreshFiles() {
    toast('Refreshing files...', 'info');
    await loadFiles();
    toast('Files refreshed! 📁', 'success');
}

function filterFiles(query) {
    if (!query || query.trim() === '') {
        renderFilesGrid(allFiles);
        return;
    }
    
    const q = query.toLowerCase();
    const filtered = allFiles.filter(f => 
        f.name.toLowerCase().includes(q) || 
        f.path.toLowerCase().includes(q)
    );
    renderFilesGrid(filtered);
}

function renderFilesGrid(files) {
    const grid = document.getElementById('files-grid');
    if (!grid) return;
    
    if (files.length === 0) {
        grid.innerHTML = '<div class="empty-state-small">No files found</div>';
        return;
    }
    
    // Format file size
    const formatSize = (bytes) => {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
    };
    
    // Get file icon based on extension
    const getFileIcon = (ext) => {
        const icons = {
            '.txt': '📄', '.md': '📝', '.json': '🔧', '.csv': '📊',
            '.log': '📋', '.py': '🐍', '.js': '💛', '.html': '🌐',
            '.css': '🎨', '.xml': '📰', '.yaml': '⚙️', '.yml': '⚙️',
            '.pdf': '📕', '.doc': '📘', '.docx': '📘'
        };
        return icons[ext] || '📄';
    };
    
    // Format date
    const formatDate = (isoString) => {
        const date = new Date(isoString);
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMs / 3600000);
        const diffDays = Math.floor(diffMs / 86400000);
        
        if (diffMins < 1) return 'Just now';
        if (diffMins < 60) return `${diffMins}m ago`;
        if (diffHours < 24) return `${diffHours}h ago`;
        if (diffDays < 7) return `${diffDays}d ago`;
        return date.toLocaleDateString();
    };
    
    grid.innerHTML = files.map(f => {
        const encodedPath = encodeURIComponent(f.path);
        const icon = getFileIcon(f.extension);
        const canPreview = ['.txt', '.md', '.json', '.log', '.csv', '.html', '.css', '.js', '.py', '.xml', '.yaml', '.yml'].includes(f.extension);
        
        return `
        <div class="file-card">
            <div class="file-icon">${icon}</div>
            <div class="file-info">
                <div class="file-name">${escapeHtml(f.name)}</div>
                <div class="file-meta">
                    <span>${formatSize(f.size)}</span>
                    <span>•</span>
                    <span>${formatDate(f.modified)}</span>
                </div>
                <div class="file-path">${escapeHtml(f.path)}</div>
            </div>
            <div class="file-actions">
                ${canPreview ? `<button class="btn btn-sm btn-secondary" onclick="previewFile('${encodedPath}', '${escapeHtml(f.name).replace(/'/g, "\\'")}', '${f.extension}')">👁️ View</button>` : ''}
                <a href="/api/files/download?path=${encodedPath}" download class="btn btn-sm btn-primary">⬇️ Download</a>
            </div>
        </div>
        `;
    }).join('');
}

async function previewFile(encodedPath, fileName, extension) {
    try {
        const response = await fetch(`/api/files/download?path=${encodedPath}`);
        if (!response.ok) throw new Error('Failed to load file');
        
        const text = await response.text();
        
        // Create modal
        const modal = document.createElement('div');
        modal.className = 'modal-overlay';
        modal.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.8);z-index:9999;display:flex;align-items:center;justify-content:center;backdrop-filter:blur(4px);';
        
        const maxLength = 50000;
        const truncated = text.length > maxLength;
        const displayText = truncated ? text.substring(0, maxLength) + '\n\n... [File truncated, download to see full content]' : text;
        
        modal.innerHTML = `
            <div style="background:var(--bg-card);border:1px solid var(--border);border-radius:var(--radius);max-width:900px;max-height:80vh;width:90%;display:flex;flex-direction:column;box-shadow:var(--shadow);">
                <div style="padding:1.5rem;border-bottom:1px solid var(--border);display:flex;justify-content:space-between;align-items:center;">
                    <div>
                        <h3 style="margin:0;font-size:1.1rem;">📄 ${escapeHtml(fileName)}</h3>
                        <div style="color:var(--text-secondary);font-size:0.8rem;margin-top:0.25rem;">${text.length.toLocaleString()} characters${truncated ? ' (showing first ' + maxLength.toLocaleString() + ')' : ''}</div>
                    </div>
                    <button onclick="this.closest('.modal-overlay').remove()" class="btn btn-secondary" style="flex-shrink:0;margin-left:1rem;">✕ Close</button>
                </div>
                <div style="padding:1.5rem;overflow:auto;flex:1;">
                    <pre style="margin:0;white-space:pre-wrap;word-break:break-word;font-family:var(--font-mono);font-size:0.85rem;line-height:1.6;background:var(--bg-input);padding:1rem;border-radius:var(--radius-sm);border:1px solid var(--border);">${escapeHtml(displayText)}</pre>
                </div>
                <div style="padding:1rem 1.5rem;border-top:1px solid var(--border);display:flex;justify-content:flex-end;gap:0.75rem;">
                    <button onclick="this.closest('.modal-overlay').remove()" class="btn btn-secondary">Close</button>
                    <a href="/api/files/download?path=${encodedPath}" download class="btn btn-primary">⬇️ Download</a>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        // Close on overlay click
        modal.addEventListener('click', (e) => {
            if (e.target === modal) modal.remove();
        });
        
        // Close on Escape key
        const escHandler = (e) => {
            if (e.key === 'Escape') {
                modal.remove();
                document.removeEventListener('keydown', escHandler);
            }
        };
        document.addEventListener('keydown', escHandler);
        
    } catch (e) {
        toast('Failed to preview file: ' + e.message, 'error');
    }
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
async function loadAllAvailableModels() {
    // Load all models from all providers and populate dropdown
    try {
        console.log('🔄 Loading all available models from all providers...');
        const modelHint = document.getElementById('model-hint');
        const modelSelect = document.getElementById('llm-model');
        
        if (modelHint) modelHint.textContent = '⏳ Fetching models from all providers...';
        if (modelSelect) modelSelect.innerHTML = '<option value="">⏳ Loading models...</option>';
        
        console.log('📡 API Call: GET /llm/models');
        const response = await api('/llm/models', 'GET', null, 30000);
        
        console.log('✅ API Response:', response);
        
        if (response && response.success && response.providers) {
            console.log('📦 Providers received:', Object.keys(response.providers));
            
            const providers = response.providers;
            const options = [];
            let modelCount = 0;
            let configuredCount = 0;
            
            // Organize by provider - show ALL providers, not just configured ones
            for (const [providerKey, providerData] of Object.entries(providers)) {
                console.log(`🔍 Checking provider: ${providerKey}`, providerData);
                
                if (providerData.models && providerData.models.length > 0) {
                    const icon = providerData.icon || '⚙️';
                    const providerLabel = providerData.provider || providerKey;
                    const configStatus = providerData.configured ? '✅' : '⚠️';
                    const configText = providerData.configured ? '' : ' (Not Configured)';
                    
                    options.push(`<optgroup label="${configStatus} ${icon} ${providerLabel}${configText}">`);
                    
                    providerData.models.forEach(model => {
                        // Format: "model|provider-key" for auto-selection
                        const displayName = model.length > 50 ? model.substring(0, 47) + '...' : model;
                        options.push(`<option value="${model}|${providerKey}">${displayName}</option>`);
                        modelCount++;
                        if (providerData.configured) configuredCount++;
                    });
                    
                    options.push('</optgroup>');
                }
            }
            
            if (modelCount > 0) {
                modelSelect.innerHTML = `<option value="">-- Select a model --</option>` + options.join('');
                if (configuredCount > 0) {
                    modelHint.textContent = `✅ ${modelCount} models available (${configuredCount} from configured providers)`;
                } else {
                    modelHint.textContent = `⚠️ ${modelCount} models available. Configure API keys in .env to enable providers.`;
                }
                console.log(`✨ SUCCESS: Loaded ${modelCount} models`);

                // Restore saved model selection now that options are populated
                const savedProvider = localStorage.getItem('llm_provider');
                const savedModel = localStorage.getItem('llm_model');
                if (savedProvider && savedModel) {
                    for (let option of modelSelect.options) {
                        if (option.value && option.value.startsWith(savedModel + '|' + savedProvider)) {
                            modelSelect.value = option.value;
                            break;
                        }
                    }
                    // If exact provider match not found, try any provider
                    if (!modelSelect.value || modelSelect.value === '') {
                        for (let option of modelSelect.options) {
                            if (option.value && option.value.startsWith(savedModel + '|')) {
                                modelSelect.value = option.value;
                                break;
                            }
                        }
                    }
                    if (modelSelect.value) {
                        const providerNames = {
                            'openai': '🔴 OpenAI', 'gemini': '🔵 Google Gemini',
                            'claude': '✨ Anthropic Claude', 'ollama': '🦙 Ollama (Local)'
                        };
                        updateCurrentSelectionDisplay(savedProvider, savedModel, providerNames[savedProvider] || savedProvider);
                    }
                }
            } else {
                modelSelect.innerHTML = '<option value="">❌ No models available</option>';
                modelHint.textContent = '❌ No models found. This should not happen!';
                console.warn('⚠️ No models found in response');
            }
        } else {
            console.error('❌ Invalid response format:', response);
            modelSelect.innerHTML = '<option value="">❌ Error loading models</option>';
            modelHint.textContent = `❌ Error: ${response?.error || 'Invalid response'}`;
        }
    } catch (e) {
        console.error('❌ Error loading all models:', e);
        const modelSelect = document.getElementById('llm-model');
        const modelHint = document.getElementById('model-hint');
        if (modelSelect) modelSelect.innerHTML = '<option value="">❌ Error loading models</option>';
        if (modelHint) modelHint.textContent = `❌ Error: ${e.message}`;
    }
}

function onModelSelected() {
    // Handle model selection - auto-set provider based on selected model
    const modelSelect = document.getElementById('llm-model');
    const providerSelect = document.getElementById('llm-provider');
    const selectedValue = modelSelect?.value;
    
    if (!selectedValue || selectedValue === '') {
        return;
    }
    
    // Extract provider info from the option value
    // Format: "model-name|provider-key"
    const parts = selectedValue.split('|');
    if (parts.length === 2) {
        const [modelName, providerKey] = parts;
        console.log(`Model selected: ${modelName} from provider: ${providerKey}`);
        
        // Auto-set the provider
        if (providerSelect) {
            providerSelect.value = providerKey;
            console.log(`Auto-selected provider: ${providerKey}`);
        }
        
        // Update the model input to show just the model name
        modelSelect.value = selectedValue;
        
        // Update current selection display
        updateCurrentSelectionDisplay(providerKey, modelName);
    }
}

function updateCurrentSelectionDisplay(provider, model, providerDisplayName) {
    const banner = document.getElementById('llm-active-banner');
    if (!banner) return;
    const label = providerDisplayName || {'openai':'🔴 OpenAI','gemini':'🔵 Gemini','claude':'✨ Claude','ollama':'🦙 Ollama'}[provider] || provider;
    banner.textContent = `✅ Active: ${label} — ${model}`;
    banner.style.display = 'block';
}

async function loadEnvironmentStatus() {
    /**Load and display which LLM providers are configured in environment variables.*/
    try {
        const statusEl = document.getElementById('llm-env-status');
        if (!statusEl) return;
        
        const response = await api('/llm/env-status');
        
        if (response.success && response.providers) {
            const html = Object.entries(response.providers).map(([key, info]) => {
                const status = info.configured ? '✅ Configured' : '❌ Not Configured';
                const statusColor = info.configured ? 'color: #22c55e;' : 'color: #ef4444;';
                return `
                    <div style="display: flex; justify-content: space-between; align-items: center; padding: 0.5rem; background: rgba(0,0,0,0.2); border-radius: 0.25rem;">
                        <span>${info.icon} <strong>${key.charAt(0).toUpperCase() + key.slice(1)}</strong></span>
                        <span style="${statusColor} font-weight: 500;">${status}</span>
                    </div>
                `;
            }).join('');
            
            statusEl.innerHTML = html;
        } else {
            statusEl.innerHTML = '<div style="color: var(--text-secondary);">Unable to load environment status</div>';
        }
    } catch (e) {
        console.error('Error loading environment status:', e);
        const statusEl = document.getElementById('llm-env-status');
        if (statusEl) {
            statusEl.innerHTML = '<div style="color: var(--text-secondary);">Error loading status</div>';
        }
    }
}

async function loadConfiguredProviders() {
    // Load environment status first
    await loadEnvironmentStatus();
    // Then load all available models
    await loadAllAvailableModels();
}

function updateDBConnectionFields() {
    const dbType = document.getElementById('db-type')?.value || 'sqlite';
    const fieldsEl = document.getElementById('db-connection-fields');
    
    if (dbType === 'sqlite') {
        fieldsEl.innerHTML = '<small style="color: var(--text-secondary);">SQLite uses local file-based storage. No additional configuration needed.</small>';
    } else if (dbType === 'postgresql') {
        fieldsEl.innerHTML = `
            <div class="form-group">
                <label>Hostname</label>
                <input type="text" id="db-host" class="form-input" placeholder="localhost" value="localhost" />
            </div>
            <div class="form-group">
                <label>Port</label>
                <input type="number" id="db-port" class="form-input" placeholder="5432" value="5432" />
            </div>
            <div class="form-group">
                <label>Database Name</label>
                <input type="text" id="db-name" class="form-input" placeholder="adgents" value="adgents" />
            </div>
            <div class="form-group">
                <label>Username</label>
                <input type="text" id="db-user" class="form-input" placeholder="postgres" />
            </div>
            <div class="form-group">
                <label>Password</label>
                <input type="password" id="db-pass" class="form-input" />
            </div>
        `;
    } else if (dbType === 'mongodb') {
        fieldsEl.innerHTML = `
            <div class="form-group">
                <label>Connection String</label>
                <input type="text" id="db-uri" class="form-input" placeholder="mongodb://localhost:27017/adgents" />
            </div>
        `;
    }
}

async function updateProviderSelection() {
    // When user manually changes provider, filter models to that provider
    const provider = document.getElementById('llm-provider')?.value?.trim();
    const modelSelect = document.getElementById('llm-model');
    const modelHint = document.getElementById('model-hint');
    
    console.log('Provider changed to:', provider);
    
    if (!provider || provider === '') {
        // Show all models again
        await loadAllAvailableModels();
        return;
    }
    
    try {
        if (modelHint) modelHint.textContent = `Loading ${provider} models...`;
        if (modelSelect) modelSelect.innerHTML = '<option value="">Loading...</option>';
        
        const response = await api(`/llm/models/${provider}`);
        
        if (response.success && response.models) {
            console.log(`Loaded ${response.models.length} ${provider} models`);
            const options = [`<option value="">-- Select a model from ${provider} --</option>`];
            
            response.models.forEach(model => {
                const displayName = model.length > 50 ? model.substring(0, 47) + '...' : model;
                options.push(`<option value="${model}|${provider}">${displayName}</option>`);
            });
            
            if (modelSelect) modelSelect.innerHTML = options.join('');
            if (modelHint) modelHint.textContent = `${response.models.length} ${response.provider} models available`;
        } else {
            if (modelSelect) modelSelect.innerHTML = '<option value="">Failed to load models</option>';
            if (modelHint) modelHint.textContent = response.error || 'Failed to load models';
        }
    } catch (e) {
        console.error('Error updating models:', e);
        if (modelSelect) modelSelect.innerHTML = '<option value="">Error loading models</option>';
        if (modelHint) modelHint.textContent = `Error: ${e.message}`;
    }
}

async function saveLLMConfig() {
    const provider = document.getElementById('llm-provider')?.value?.trim();
    const api_key = document.getElementById('llm-api-key')?.value?.trim();
    const modelSelect = document.getElementById('llm-model');
    let model = modelSelect?.value?.trim();
    
    // Extract model name if it includes provider info (format: "model|provider")
    if (model && model.includes('|')) {
        model = model.split('|')[0];
    }

    if (!provider || provider === '') {
        toast('Select a provider', 'error');
        return;
    }

    // API key optional — .env is used if blank

    if (!model || model === '') {
        toast('Select a model', 'error');
        return;
    }

    const statusEl = document.getElementById('llm-config-status');
    statusEl.innerHTML = '<span class="badge badge-blue">⏳ Saving...</span>';

    try {
        // Only send API key if provided (non-empty)
        const payload = { provider, model };
        if (api_key) {
            payload.api_key = api_key;
        }
        
        await api('/llm/configure', 'POST', payload);
        
        // Save to localStorage (only the model selection, not the key)
        localStorage.setItem('llm_provider', provider);
        localStorage.setItem('llm_model', model);
        
        // Update current selection display
        const providerNames = {
            'openai': '🔴 OpenAI',
            'gemini': '🔵 Google Gemini',
            'claude': '✨ Anthropic Claude',
            'ollama': '🦙 Ollama (Local)'
        };
        updateCurrentSelectionDisplay(provider, model, providerNames[provider] || provider);
        
        statusEl.innerHTML = '<span class="badge badge-green">✅ Saved</span>';
        toast(`${provider} → ${model} saved!`, 'success');
    } catch (e) {
        statusEl.innerHTML = `<span class="badge badge-red">❌ ${e.message}</span>`;
        toast(e.message, 'error');
    }
}

async function testLLMConnection() {
    const provider = document.getElementById('llm-provider')?.value?.trim();
    if (!provider) {
        toast('Select a provider first', 'error');
        return;
    }

    const statusEl = document.getElementById('llm-config-status');
    statusEl.innerHTML = '<span class="badge badge-blue">🧪 Testing connection...</span>';

    try {
        const result = await api('/llm/test', 'POST', { provider });
        if (result.success) {
            statusEl.innerHTML = `<span class="badge badge-green">✅ Connection successful! Model: ${result.model || result.provider}</span>`;
            toast('Connection test passed!', 'success');
        } else {
            statusEl.innerHTML = `<span class="badge badge-red">❌ ${result.error || 'Test failed'}</span>`;
            toast(result.error || 'Connection test failed', 'error');
        }
    } catch (e) {
        statusEl.innerHTML = `<span class="badge badge-red">❌ ${e.message}</span>`;
        toast(e.message, 'error');
    }
}

async function refreshProviderStatus() {
    const statusEl = document.getElementById('provider-status-list');
    statusEl.innerHTML = '<span style="color: var(--text-secondary);">Refreshing...</span>';
    await loadProviderStatus();
}

async function saveMCPConfig() {
    const mode = document.getElementById('mcp-mode')?.value || 'stdio';
    const port = parseInt(document.getElementById('mcp-port')?.value || '8001');

    const statusEl = document.getElementById('mcp-config-status');
    statusEl.innerHTML = '<span class="badge badge-blue">⏳ Saving...</span>';

    try {
        await api('/mcp/configure', 'POST', { mode, port });
        statusEl.innerHTML = '<span class="badge badge-green">✅ MCP configuration saved</span>';
        toast('MCP settings saved!', 'success');
    } catch (e) {
        statusEl.innerHTML = `<span class="badge badge-red">❌ ${e.message}</span>`;
        toast(e.message, 'error');
    }
}

async function saveDBConfig() {
    const dbType = document.getElementById('db-type')?.value || 'sqlite';
    const statusEl = document.getElementById('db-config-status');
    statusEl.innerHTML = '<span class="badge badge-blue">⏳ Saving...</span>';

    try {
        const config = { type: dbType };
        
        if (dbType !== 'sqlite') {
            config.host = document.getElementById('db-host')?.value || 'localhost';
            config.port = parseInt(document.getElementById('db-port')?.value || '5432');
            config.database = document.getElementById('db-name')?.value || 'adgents';
            config.username = document.getElementById('db-user')?.value || '';
            config.password = document.getElementById('db-pass')?.value || '';
        }

        // In a real implementation, this would call a backend endpoint
        statusEl.innerHTML = '<span class="badge badge-green">✅ Database settings saved (requires restart)</span>';
        toast('Database settings saved!', 'success');
    } catch (e) {
        statusEl.innerHTML = `<span class="badge badge-red">❌ ${e.message}</span>`;
        toast(e.message, 'error');
    }
}

async function savePersonalSettings() {
    const orgName = document.getElementById('org-name')?.value || 'My Organization';
    const memoryType = document.getElementById('memory-type')?.value || 'multi_tier';
    const autoSave = document.getElementById('auto-save')?.checked || false;

    const statusEl = document.getElementById('personal-config-status');
    statusEl.innerHTML = '<span class="badge badge-blue">⏳ Saving...</span>';

    try {
        // Save to localStorage for client-side preferences
        localStorage.setItem('org_name', orgName);
        localStorage.setItem('memory_type', memoryType);
        localStorage.setItem('auto_save', autoSave);

        statusEl.innerHTML = '<span class="badge badge-green">✅ Settings saved</span>';
        toast('Personal settings saved!', 'success');
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
    const hintEl = document.getElementById('model-hint');
    const defaults = {
        openai: 'gpt-4o-mini (or gpt-4o, gpt-4-turbo)',
        gemini: 'gemini-1.5-flash (or gemini-1.5-pro)',
        claude: 'claude-3-5-sonnet-20241022 (or claude-3 variants)',
        ollama: 'llama3 (or mistral, neural-chat, etc.)'
    };
    if (input) input.placeholder = defaults[provider] || 'model-name';
    if (hintEl) hintEl.textContent = `Recommended: ${defaults[provider] || 'varies'}`;
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
        
        // Display files created during task execution
        if (task.metadata && task.metadata.files_created && task.metadata.files_created.length > 0) {
            const filesSection = document.createElement('div');
            filesSection.style.marginTop = '1.5rem';
            filesSection.style.padding = '1rem';
            filesSection.style.background = 'rgba(16,185,129,0.06)';
            filesSection.style.border = '1px solid rgba(16,185,129,0.2)';
            filesSection.style.borderRadius = '8px';
            
            const filesTitle = document.createElement('div');
            filesTitle.style.fontWeight = '600';
            filesTitle.style.marginBottom = '0.5rem';
            filesTitle.style.color = 'var(--green)';
            filesTitle.innerHTML = '📁 Files Created';
            filesSection.appendChild(filesTitle);
            
            const filesList = document.createElement('ul');
            filesList.style.listStyle = 'none';
            filesList.style.padding = '0';
            filesList.style.margin = '0';
            
            task.metadata.files_created.forEach(filePath => {
                const fileItem = document.createElement('li');
                fileItem.style.padding = '0.5rem';
                fileItem.style.marginBottom = '0.25rem';
                fileItem.style.background = 'rgba(16,185,129,0.08)';
                fileItem.style.borderRadius = '4px';
                fileItem.style.fontFamily = 'monospace';
                fileItem.style.fontSize = '0.85rem';
                fileItem.style.color = '#34d399';
                
                // Create download link
                const encodedPath = encodeURIComponent(filePath.replace(/\\/g, '/'));
                fileItem.innerHTML = `📄 <a href="/api/files/download?path=${encodedPath}" download style="color:#34d399;text-decoration:underline;cursor:pointer;font-weight:600" title="Click to download ${escapeHtml(filePath)}">${escapeHtml(filePath)}</a>`;
                filesList.appendChild(fileItem);
            });
            
            filesSection.appendChild(filesList);
            body.appendChild(filesSection);
        }
        
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
        
        // Organize docs by section
        const packagesDocs = docs.filter(d => d.startsWith('packages-')).map(d => d.replace('packages-', ''));
        const projectDocs = docs.filter(d => d.startsWith('project-')).map(d => d.replace('project-', ''));
        
        // Preferred ordering within sections
        const packagesOrder = ['installation', 'integration', 'api_reference', 'crew_management', 'skills', 'advanced'];
        const projectOrder = ['quickstart', 'architecture', 'studio', 'crew', 'use_cases', 'deployment'];
        
        packagesDocs.sort((a, b) => {
            const idxA = packagesOrder.indexOf(a);
            const idxB = packagesOrder.indexOf(b);
            if (idxA !== -1 && idxB !== -1) return idxA - idxB;
            if (idxA !== -1) return -1;
            if (idxB !== -1) return 1;
            return a.localeCompare(b);
        });
        
        projectDocs.sort((a, b) => {
            const idxA = projectOrder.indexOf(a);
            const idxB = projectOrder.indexOf(b);
            if (idxA !== -1 && idxB !== -1) return idxA - idxB;
            if (idxA !== -1) return -1;
            if (idxB !== -1) return 1;
            return a.localeCompare(b);
        });

        const listEl = document.getElementById('docs-nav-list');
        if (!listEl) return;
        
        // Build HTML with sections
        let html = '';
        
        // Index first
        html += '<li class="docs-nav-item" id="nav-doc-index" onclick="loadDocContent(\'index\')">📘 Overview</li>';
        
        // Package integration section
        if (packagesDocs.length > 0) {
            html += '<li class="docs-section-header">📦 Package Integration</li>';
            packagesDocs.forEach(d => {
                const label = d.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
                html += `<li class="docs-nav-item" id="nav-doc-packages-${d}" onclick="loadDocContent('packages-${d}')">${escapeHtml(label)}</li>`;
            });
        }
        
        // Project application section
        if (projectDocs.length > 0) {
            html += '<li class="docs-section-header">🚀 Project Application</li>';
            projectDocs.forEach(d => {
                const label = d.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
                html += `<li class="docs-nav-item" id="nav-doc-project-${d}" onclick="loadDocContent('project-${d}')">${escapeHtml(label)}</li>`;
            });
        }
        
        listEl.innerHTML = html;
        
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
                        // Internal document link - convert path to doc name
                        aEl.onclick = (e) => {
                            e.preventDefault();
                            let docName = href.replace('.md', '');
                            
                            // Handle relative paths: packages/skills.md -> packages-skills
                            if (docName.includes('/')) {
                                docName = docName.split('/').join('-');
                            }
                            // Handle root-relative paths: ../packages/skills.md -> packages-skills
                            if (docName.startsWith('..')) {
                                docName = docName.replace(/\.\.\//g, '').split('/').join('-');
                            }
                            
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
        console.log('[MCP] Loading MCP page...');
        
        // Load MCP status
        const statusData = await api('/mcp/status');
        console.log('[MCP] Status data received:', statusData);
        
        // Check if all elements exist
        const statusDiv = document.getElementById('mcp-status');
        const startBtn = document.getElementById('btn-start-mcp');
        const stopBtn = document.getElementById('btn-stop-mcp');
        const toolsList = document.getElementById('mcp-tools-list');
        const agentsList = document.getElementById('mcp-agents-list');
        
        // Safely check if page exists
        if (!statusDiv || !startBtn || !stopBtn || !toolsList || !agentsList) {
            console.warn('[MCP] Some elements missing from DOM, page may not be loaded yet');
            toast('MCP page not fully loaded yet', 'info');
            return;
        }
        
        if (statusData.success) {
            const isRunning = statusData.running || false;
            const toolCount = statusData.available_tools || 0;
            const agentCount = statusData.available_agents || 0;
            
            // Update status display
            if (statusDiv) {
                statusDiv.innerHTML = `
                    <div style="display: grid; gap: 0.75rem;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span style="color: var(--text-secondary);">Status</span>
                            <span class="badge ${isRunning ? 'badge-green' : 'badge-orange'}">${isRunning ? '🟢 Running' : '🟡 Stopped'}</span>
                        </div>
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span style="color: var(--text-secondary);">Available Tools</span>
                            <strong>${toolCount} skill${toolCount !== 1 ? 's' : ''}</strong>
                        </div>
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span style="color: var(--text-secondary);">Agents Available</span>
                            <strong>${agentCount} agent${agentCount !== 1 ? 's' : ''}</strong>
                        </div>
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span style="color: var(--text-secondary);">Mode</span>
                            <strong>${statusData.config?.mode || 'stdio'}</strong>
                        </div>
                    </div>
                `;
            }
            
            // Update button visibility
            if (startBtn && stopBtn) {
                if (isRunning) {
                    startBtn.style.display = 'none';
                    stopBtn.style.display = 'inline-block';
                } else {
                    startBtn.style.display = 'inline-block';
                    stopBtn.style.display = 'none';
                }
            }
        } else {
            console.warn('[MCP] API returned error:', statusData.error);
            if (statusDiv) {
                statusDiv.innerHTML = `<div style="color: var(--text-secondary);">⚠️ Error: ${statusData.error || 'Unable to load status'}</div>`;
            }
        }
        
        // Load and display tools
        if (toolsList) {
            if (statusData.tool_names && statusData.tool_names.length > 0) {
                toolsList.innerHTML = statusData.tool_names.map(name => `
                    <div style="padding: 0.75rem; background: var(--bg-input); border-radius: var(--radius-sm);">
                        <div style="font-weight: 500; color: var(--text-primary);">🔧 ${escapeHtml(name)}</div>
                    </div>
                `).join('');
            } else {
                toolsList.innerHTML = '<div style="padding: 1rem; text-align: center; color: var(--text-secondary);">No skills available as tools</div>';
            }
        }
        
        // Load and display agents
        if (agentsList) {
            if (statusData.agent_names && statusData.agent_names.length > 0) {
                agentsList.innerHTML = statusData.agent_names.map(name => `
                    <div style="padding: 0.75rem; background: var(--bg-input); border-radius: var(--radius-sm); display: flex; align-items: center;">
                        <div style="font-weight: 500; color: var(--text-primary);">🤖 ${escapeHtml(name)}</div>
                    </div>
                `).join('');
            } else {
                agentsList.innerHTML = '<div style="padding: 1rem; text-align: center; color: var(--text-secondary);">No agents configured</div>';
            }
        }
        
        console.log('[MCP] Page load complete');
    } catch (e) {
        console.error('[MCP] Failed to load MCP data:', e);
        toast('Failed to load MCP data: ' + e.message, 'error');
    }
}

async function saveMCPConfig() {
    const modeEl = document.getElementById('mcp-mode');
    const portEl = document.getElementById('mcp-port');
    
    if (!modeEl || !portEl) {
        toast('Configuration elements missing from page', 'error');
        return;
    }
    
    const mode = modeEl.value;
    const port = portEl.value;
    
    try {
        const result = await api('/mcp/configure', 'POST', { mode, port });
        if (result.success) {
            toast('MCP configuration saved!', 'success');
        } else {
            toast('Failed to save configuration', 'error');
        }
    } catch (e) {
        toast('Error: ' + e.message, 'error');
    }
}

async function startMCPServer() {
    try {
        const result = await api('/mcp/start', 'POST', {});
        if (result.success) {
            toast('MCP Server started!', 'success');
            await loadMCPPage();
        } else {
            toast('Failed to start server: ' + result.error, 'error');
        }
    } catch (e) {
        toast('Error: ' + e.message, 'error');
    }
}

async function stopMCPServer() {
    try {
        const result = await api('/mcp/stop', 'POST', {});
        if (result.success) {
            toast('MCP Server stopped', 'success');
            await loadMCPPage();
        } else {
            toast('Failed to stop server: ' + result.error, 'error');
        }
    } catch (e) {
        toast('Error: ' + e.message, 'error');
    }
}

window.addEventListener('DOMContentLoaded', init);

// ─── ADK Workflows ───────────────────────────────────────────────────────────

async function loadADKPage() {
    try {
        // Load Gemini models for ADK agent creation (prefer Gemini, but show all available)
        const modelSelect = document.getElementById('adk-agent-model');
        if (modelSelect) {
            modelSelect.innerHTML = '<option value="">⏳ Loading models...</option>';
            
            try {
                // Try to get Gemini models specifically
                const modelsResponse = await api('/llm/models/gemini');
                if (modelsResponse.success && modelsResponse.models && modelsResponse.models.length > 0) {
                    console.log('✓ Loaded Gemini models for ADK:', modelsResponse.models);
                    modelSelect.innerHTML = '<option value="">-- Select a Gemini model --</option>';
                    modelsResponse.models.forEach(model => {
                        modelSelect.innerHTML += `<option value="${model}">${model}</option>`;
                    });
                } else {
                    // Fallback if Gemini not available
                    console.warn('Gemini models not available, using fallback');
                    modelSelect.innerHTML = '<option value="gemini-1.5-flash" selected>Gemini 1.5 Flash</option><option value="gemini-1.5-pro">Gemini 1.5 Pro</option>';
                }
            } catch (e) {
                console.error('Failed to load Gemini models:', e);
                modelSelect.innerHTML = '<option value="gemini-1.5-flash" selected>Gemini 1.5 Flash (Default)</option>';
            }
        }
        
        // Load ADK agents
        const agentsData = await api('/adk/agents');
        renderADKAgentsList(agentsData.agents || []);
        
        // Populate test agent select
        const testSelect = document.getElementById('test-agent-select');
        if (testSelect) {
            testSelect.innerHTML = '<option value="">Choose an agent...</option>';
            (agentsData.agents || []).forEach(agent => {
                testSelect.innerHTML += `<option value="${agent.name}">${agent.name}</option>`;
            });
        }
        
        // Update workflow type change handler
        const workflowTypeSelect = document.getElementById('workflow-type');
        if (workflowTypeSelect) {
            workflowTypeSelect.addEventListener('change', function() {
                const type = this.value;
                const loopGroup = document.getElementById('loop-condition-group');
                const maxIterGroup = document.getElementById('max-iterations-group');
                
                if (type === 'loop') {
                    loopGroup.style.display = 'block';
                    maxIterGroup.style.display = 'block';
                } else {
                    loopGroup.style.display = 'none';
                    maxIterGroup.style.display = 'none';
                }
            });
        }
        
    } catch (e) {
        console.error('Failed to load ADK page:', e);
        toast('Failed to load ADK data', 'error');
    }
}

function renderADKAgentsList(agents) {
    const listEl = document.getElementById('adk-agents-list');
    if (!agents.length) {
        listEl.innerHTML = '<div class="empty-state"><div class="empty-icon">🤖</div><div class="empty-title">No ADK Agents</div><div class="empty-description">Create your first Google ADK agent to get started</div></div>';
        return;
    }
    
    listEl.innerHTML = agents.map(agent => `
        <div class="agent-card">
            <div class="agent-card-header">
                <span class="agent-avatar">🤖</span>
                <div class="agent-info">
                    <div class="agent-name">${escapeHtml(agent.name)}</div>
                    <div class="agent-model">${escapeHtml(agent.model)}</div>
                </div>
                <div class="agent-status">
                    <span class="badge ${agent.status === 'initialized' ? 'badge-green' : 'badge-yellow'}">
                        ${agent.status === 'initialized' ? '✅ Ready' : '⏳ ' + agent.status}
                    </span>
                </div>
            </div>
            <div class="agent-description">${escapeHtml(agent.description || 'No description')}</div>
            <div class="agent-stats">
                <span>🛠️ ${agent.tools_count || 0} tools</span>
                <span>🔗 ${agent.adk_available ? 'ADK Available' : 'ADK Unavailable'}</span>
            </div>
        </div>
    `).join('');
}

async function createADKAgent() {
    const name = document.getElementById('adk-agent-name').value.trim();
    const description = document.getElementById('adk-agent-description').value.trim();
    const model = document.getElementById('adk-agent-model').value;
    const instructions = document.getElementById('adk-agent-instructions').value.trim();
    
    if (!name) {
        toast('Agent name is required', 'error');
        return;
    }
    
    if (!model || model === '') {
        toast('Please select a model', 'error');
        return;
    }
    
    try {
        const data = await api('/adk/agents/create', 'POST', {
            name, description, model, instructions, tools: []
        });
        
        if (data.success) {
            toast('ADK Agent created successfully!', 'success');
            // Clear form
            document.getElementById('adk-agent-name').value = '';
            document.getElementById('adk-agent-description').value.trim();
            document.getElementById('adk-agent-instructions').value = '';
            // Reload page
            loadADKPage();
        } else {
            toast(data.error || 'Failed to create agent', 'error');
        }
    } catch (e) {
        toast('Failed to create ADK agent: ' + e.message, 'error');
    }
}

async function createADKWorkflow() {
    const name = document.getElementById('workflow-name').value.trim();
    const type = document.getElementById('workflow-type').value;
    const agents = document.getElementById('workflow-agents').value.trim().split(',').map(a => a.trim()).filter(a => a);
    const condition = document.getElementById('loop-condition').value.trim();
    const maxIterations = parseInt(document.getElementById('max-iterations').value) || 10;
    
    if (!name) {
        toast('Workflow name is required', 'error');
        return;
    }
    
    if (!agents.length) {
        toast('At least one agent is required', 'error');
        return;
    }
    
    try {
        const data = await api('/adk/workflows/create', 'POST', {
            name, workflow_type: type, agents, condition, max_iterations: maxIterations
        });
        
        if (data.success) {
            toast('ADK Workflow created successfully!', 'success');
            // Clear form
            document.getElementById('workflow-name').value = '';
            document.getElementById('workflow-agents').value = '';
            document.getElementById('loop-condition').value = '';
            document.getElementById('max-iterations').value = '10';
        } else {
            toast(data.error || 'Failed to create workflow', 'error');
        }
    } catch (e) {
        toast('Failed to create ADK workflow: ' + e.message, 'error');
    }
}

async function testADKAgent() {
    const agentName = document.getElementById('test-agent-select').value;
    const input = document.getElementById('test-agent-input').value.trim();
    
    if (!agentName) {
        toast('Please select an agent', 'error');
        return;
    }
    
    if (!input) {
        toast('Please enter input text', 'error');
        return;
    }
    
    const resultEl = document.getElementById('adk-test-result');
    resultEl.style.display = 'block';
    resultEl.innerHTML = '<div style="text-align: center; color: var(--text-secondary);">⏳ Running agent...</div>';
    
    try {
        const data = await api(`/adk/agents/${agentName}/run`, 'POST', { input });
        
        if (data.success) {
            resultEl.innerHTML = `
                <div style="margin-bottom: 1rem;">
                    <strong>✅ Success</strong> - Model: ${escapeHtml(data.model)}, Agent: ${escapeHtml(data.agent_name)}
                </div>
                <div style="background: var(--bg-card-hover); padding: 1rem; border-radius: 8px; border: 1px solid var(--border);">
                    ${renderMarkdown(data.output)}
                </div>
            `;
        } else {
            resultEl.innerHTML = `
                <div style="margin-bottom: 1rem;">
                    <strong style="color: var(--red);">❌ Error</strong>
                </div>
                <div style="background: rgba(239,68,68,0.1); padding: 1rem; border-radius: 8px; border: 1px solid rgba(239,68,68,0.3); color: var(--red);">
                    ${escapeHtml(data.error)}
                </div>
            `;
        }
    } catch (e) {
        resultEl.innerHTML = `
            <div style="margin-bottom: 1rem;">
                <strong style="color: var(--red);">❌ Network Error</strong>
            </div>
            <div style="background: rgba(239,68,68,0.1); padding: 1rem; border-radius: 8px; border: 1px solid rgba(239,68,68,0.3); color: var(--red);">
                ${escapeHtml(e.message)}
            </div>
        `;
    }
}

// ─── Crew Collaboration ──────────────────────────────────────────────────────

async function loadCrewsPage() {
    try {
        // Load crews
        const crewsData = await api('/crews');
        renderCrewsList(crewsData.crews || []);
        
        // Load agents for member selection and crew creation
        const agentsData = await api('/agents');
        const agentSelects = ['member-agent-select'];
        agentSelects.forEach(id => {
            const select = document.getElementById(id);
            if (select) {
                select.innerHTML = '<option value="">Choose an agent...</option>';
                (agentsData.agents || []).forEach(agent => {
                    select.innerHTML += `<option value="${agent.id}">${agent.persona.avatar} ${agent.persona.name}</option>`;
                });
            }
        });
        
        // Load agents for crew creation
        const crewAgentsSelect = document.getElementById('crew-agents');
        const crewAgentsWrapper = document.getElementById('crew-agents-wrapper');
        if (crewAgentsSelect && crewAgentsWrapper) {
            crewAgentsSelect.innerHTML = '';
            crewAgentsWrapper.innerHTML = '';
            (agentsData.agents || []).forEach(agent => {
                // Add to hidden select for form submission
                crewAgentsSelect.innerHTML += `<option value="${agent.id}">${agent.persona.avatar} ${agent.persona.name}</option>`;
                
                // Render as checkbox card
                crewAgentsWrapper.innerHTML += `
                    <label style="display: flex; align-items: center; gap: 10px; padding: 12px; background: var(--bg-secondary); border: 2px solid transparent; border-radius: 8px; cursor: pointer; transition: all 0.2s; border-color: var(--border-color);">
                        <input type="checkbox" value="${agent.id}" class="crew-agent-checkbox" style="width: 18px; height: 18px; cursor: pointer;">
                        <div style="display: flex; align-items: center; gap: 8px; flex: 1;">
                            <span style="font-size: 24px;">${agent.persona.avatar || '👤'}</span>
                            <span style="font-weight: 500; color: var(--text-primary);">${escapeHtml(agent.persona.name)}</span>
                        </div>
                    </label>
                `;
            });
            
            // Update select when checkboxes change
            document.querySelectorAll('.crew-agent-checkbox').forEach(checkbox => {
                checkbox.addEventListener('change', function() {
                    const selected = Array.from(document.querySelectorAll('.crew-agent-checkbox:checked')).map(cb => cb.value);
                    crewAgentsSelect.value = selected.join(',');
                });
            });
        }
        
        // Load crews for member addition
        const crewSelect = document.getElementById('member-crew-select');
        if (crewSelect) {
            crewSelect.innerHTML = '<option value="">Choose a crew...</option>';
            (crewsData.crews || []).forEach(crew => {
                crewSelect.innerHTML += `<option value="${crew.id}">${crew.name}</option>`;
            });
        }
        
        // Load crews for communications - send message
        const sendMsgCrewSelect = document.getElementById('send-msg-crew');
        if (sendMsgCrewSelect) {
            sendMsgCrewSelect.innerHTML = '<option value="">Choose crew...</option>';
            (crewsData.crews || []).forEach(crew => {
                sendMsgCrewSelect.innerHTML += `<option value="${crew.id}">${crew.name}</option>`;
            });
            // Add change listener with proper context
            sendMsgCrewSelect.onchange = function() {
                console.log('[Crews] Crew selected, loading agents:', this.value);
                updateCrewAgentSelects();
            };
        }
        
        // Load crews for communications - view history
        const viewCommCrewSelect = document.getElementById('view-comm-crew');
        if (viewCommCrewSelect) {
            viewCommCrewSelect.innerHTML = '<option value="">Choose a crew...</option>';
            (crewsData.crews || []).forEach(crew => {
                viewCommCrewSelect.innerHTML += `<option value="${crew.id}">${crew.name}</option>`;
            });
        }
        
    } catch (e) {
        console.error('Failed to load crews page:', e);
        toast('Failed to load crews data', 'error');
    }
}

function renderCrewsList(crews) {
    const listEl = document.getElementById('crews-list');
    if (!crews.length) {
        listEl.innerHTML = '<div class="empty-state"><div class="empty-icon">👥</div><div class="empty-title">No Crews Yet</div><div class="empty-description">Create your first crew to get started</div></div>';
        return;
    }
    
    listEl.innerHTML = crews.map(crew => {
        const memberCount = crew.members ? crew.members.length : 0;
        const protocolIcons = { 'a2a': '🔗', 'adk': '🌐', 'rest': '📡' };
        const protocolIcon = protocolIcons[crew.communication_protocol] || '🔗';
        
        return `
            <div style="background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 12px; padding: 20px; transition: all 0.3s ease;">
                <div style="display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 16px;">
                    <div style="display: flex; align-items: center; gap: 12px; flex: 1;">
                        <div style="width: 48px; height: 48px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 24px;">
                            👥
                        </div>
                        <div style="flex: 1;">
                            <div style="font-size: 16px; font-weight: 600; color: var(--text-primary); margin-bottom: 4px;">
                                ${escapeHtml(crew.name)}
                            </div>
                            <div style="font-size: 13px; color: var(--text-secondary); display: flex; align-items: center; gap: 8px;">
                                <span>${protocolIcon} ${escapeHtml(crew.communication_protocol).toUpperCase()}</span>
                                <span style="color: var(--text-tertiary);">•</span>
                                <span>🏢 ${escapeHtml(crew.organization || 'default')}</span>
                            </div>
                        </div>
                    </div>
                    <div style="background: #4CAF50; color: white; padding: 6px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; white-space: nowrap;">
                        ✅ Active
                    </div>
                </div>
                
                <div style="background: var(--bg-secondary); border-radius: 8px; padding: 12px; margin-bottom: 16px; min-height: 40px;">
                    <div style="font-size: 13px; color: var(--text-primary); line-height: 1.5;">
                        ${escapeHtml(crew.description || 'No description provided')}
                    </div>
                </div>
                
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 16px;">
                    <div style="background: var(--bg-secondary); border-radius: 8px; padding: 10px; text-align: center;">
                        <div style="font-size: 11px; color: var(--text-secondary); margin-bottom: 4px;">MEMBERS</div>
                        <div style="font-size: 18px; font-weight: 700; color: var(--text-primary);">${memberCount}</div>
                    </div>
                    <div style="background: var(--bg-secondary); border-radius: 8px; padding: 10px; text-align: center;">
                        <div style="font-size: 11px; color: var(--text-secondary); margin-bottom: 4px;">PROTOCOL</div>
                        <div style="font-size: 16px;">${protocolIcon}</div>
                    </div>
                </div>
                
                ${memberCount > 0 ? `
                    <div style="margin-bottom: 16px;">
                        <div style="font-size: 12px; font-weight: 600; color: var(--text-secondary); margin-bottom: 8px;">Team Members:</div>
                        <div style="display: flex; flex-wrap: wrap; gap: 6px;">
                            ${(crew.members || []).map(m => `
                                <span style="background: var(--bg-secondary); padding: 4px 10px; border-radius: 16px; font-size: 12px; color: var(--text-primary);">
                                    👤 ${escapeHtml(m.agent_name || 'Unknown')}
                                </span>
                            `).join('')}
                        </div>
                    </div>
                ` : ''}
                
                <div style="display: flex; gap: 8px; padding-top: 16px; border-top: 1px solid var(--border-color);">
                    <button onclick="deleteCrew('${crew.id}')" style="flex: 1; padding: 10px; background: #ff5252; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 13px; font-weight: 600; transition: all 0.2s;">
                        🗑️ Delete
                    </button>
                    <button style="flex: 1; padding: 10px; background: var(--bg-secondary); color: var(--text-primary); border: 1px solid var(--border-color); border-radius: 6px; cursor: pointer; font-size: 13px; font-weight: 600;">
                        📊 Details
                    </button>
                </div>
            </div>
        `;
    }).join('');
}

async function createCrew() {
    const name = document.getElementById('crew-name').value.trim();
    const description = document.getElementById('crew-description').value.trim();
    const organization = document.getElementById('crew-organization').value.trim();
    const protocol = document.getElementById('crew-protocol').value;
    
    // Get selected agents from checkboxes
    const selectedCheckboxes = document.querySelectorAll('.crew-agent-checkbox:checked');
    const selectedAgentIds = Array.from(selectedCheckboxes).map(cb => cb.value);
    
    if (!name) {
        toast('Crew name is required', 'error');
        return;
    }
    
    if (selectedAgentIds.length === 0) {
        toast('Please select at least one agent', 'error');
        return;
    }
    
    try {
        // Get agent details from the page
        const allCheckboxes = document.querySelectorAll('.crew-agent-checkbox');
        const agentMap = {};
        const crewAgentsSelect = document.getElementById('crew-agents');
        
        Array.from(crewAgentsSelect.options).forEach(option => {
            agentMap[option.value] = option.text.replace(/^\S+\s/, '');
        });
        
        const selectedAgents = selectedAgentIds.map(id => ({
            agent_id: id,
            agent_name: agentMap[id] || 'Unknown',
            role: 'contributor'
        }));
        
        const data = await api('/crews/create', 'POST', {
            name, description, organization, communication_protocol: protocol, members: selectedAgents
        });
        
        if (data.success) {
            toast('Crew created successfully!', 'success');
            // Clear form
            document.getElementById('crew-name').value = '';
            document.getElementById('crew-description').value = '';
            document.getElementById('crew-organization').value = 'default';
            // Clear agent selection
            document.querySelectorAll('.crew-agent-checkbox').forEach(cb => cb.checked = false);
            // Reload page
            loadCrewsPage();
        } else {
            toast(data.error || 'Failed to create crew', 'error');
        }
    } catch (e) {
        toast('Failed to create crew: ' + e.message, 'error');
    }
}

async function addCrewMember() {
    const crewId = document.getElementById('member-crew-select').value;
    const agentId = document.getElementById('member-agent-select').value;
    const role = document.getElementById('member-role').value;
    
    if (!crewId) {
        toast('Please select a crew', 'error');
        return;
    }
    
    if (!agentId) {
        toast('Please select an agent', 'error');
        return;
    }
    
    try {
        const data = await api(`/crews/${crewId}/members`, 'POST', {
            agent_id: agentId, role
        });
        
        if (data.success) {
            toast('Member added to crew successfully!', 'success');
            // Clear selections
            document.getElementById('member-crew-select').value = '';
            document.getElementById('member-agent-select').value = '';
            document.getElementById('member-role').value = 'contributor';
            // Reload page
            loadCrewsPage();
        } else {
            toast(data.error || 'Failed to add member', 'error');
        }
    } catch (e) {
        toast('Failed to add crew member: ' + e.message, 'error');
    }
}

async function deleteCrew(crewId) {
    if (!confirm('Are you sure you want to delete this crew? This action cannot be undone.')) {
        return;
    }
    
    try {
        const data = await api(`/crews/${crewId}`, 'DELETE');
        
        if (data.success) {
            toast('Crew deleted successfully!', 'success');
            // Reload page
            loadCrewsPage();
        } else {
            toast(data.error || 'Failed to delete crew', 'error');
        }
    } catch (e) {
        toast('Failed to delete crew: ' + e.message, 'error');
    }
}

async function loadCrewCommunications() {
    const crewId = document.getElementById('view-comm-crew').value;
    
    if (!crewId) {
        document.getElementById('crew-communications').innerHTML = '<div style="text-align: center; color: var(--text-secondary);">👈 Select a crew to view communications</div>';
        return;
    }
    
    const commsEl = document.getElementById('crew-communications');
    commsEl.innerHTML = '<div style="text-align: center; color: var(--text-secondary);">⏳ Loading communications...</div>';
    
    try {
        const data = await api(`/a2a/communications/${crewId}`);
        console.log('[Communications] API Response:', data);
        
        if (data.success && data.communications && data.communications.length > 0) {
            commsEl.innerHTML = data.communications.map((comm, idx) => {
                // Communications have fields: id, crew_id, from, to, message, protocol, timestamp, status
                const fromAgent = comm.from || comm.sender_id || 'Unknown';
                const toAgent = comm.to || comm.receiver_id || 'Unknown';
                
                // Extract content text - it can be a dict or a string
                let contentText = 'No content';
                if (comm.message) {
                    if (typeof comm.message === 'string') {
                        contentText = comm.message;
                    } else if (typeof comm.message === 'object' && comm.message.text) {
                        contentText = comm.message.text;
                    }
                } else if (comm.content) {
                    if (typeof comm.content === 'string') {
                        contentText = comm.content;
                    } else if (typeof comm.content === 'object' && comm.content.text) {
                        contentText = comm.content.text;
                    }
                }
                
                const msgType = comm.message_type || 'message';
                const timestamp = comm.timestamp ? new Date(comm.timestamp).toLocaleString() : 'Just now';
                
                return `
                    <div style="border-left: 3px solid var(--accent); background: var(--card-bg); border-radius: 6px; padding: 12px; margin-bottom: 10px;">
                        <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 8px;">
                            <div style="display: flex; gap: 8px; align-items: center;">
                                <span style="font-weight: 600; color: var(--text-primary);">${escapeHtml(fromAgent)}</span>
                                <span style="color: var(--text-secondary);">→</span>
                                <span style="font-weight: 600; color: var(--text-primary);">${escapeHtml(toAgent)}</span>
                                <span style="background: var(--bg-secondary); padding: 2px 8px; border-radius: 12px; font-size: 11px; color: var(--text-secondary);">
                                    ${escapeHtml(msgType)}
                                </span>
                            </div>
                            <span style="font-size: 12px; color: var(--text-secondary);">
                                ${timestamp}
                            </span>
                        </div>
                        <div style="color: var(--text-primary); line-height: 1.4; word-wrap: break-word;">
                            ${escapeHtml(contentText)}
                        </div>
                    </div>
                `;
            }).join('');
        } else {
            commsEl.innerHTML = '<div style="text-align: center; color: var(--text-secondary); padding: 20px;">No communications yet. Start collaborating with crew members!</div>';
        }
    } catch (e) {
        commsEl.innerHTML = `<div style="text-align: center; color: var(--red);">❌ Failed to load communications</div>`;
        console.error('Error loading communications:', e);
    }
}

async function updateCrewAgentSelects() {
    const crewId = document.getElementById('send-msg-crew').value;
    const fromSelect = document.getElementById('send-msg-from');
    const toSelect = document.getElementById('send-msg-to');
    
    console.log('[Agents] Updating agent selects for crew:', crewId);
    
    if (!crewId) {
        fromSelect.innerHTML = '<option value="">Select agent...</option>';
        toSelect.innerHTML = '<option value="">Select agent...</option>';
        return;
    }
    
    try {
        console.log('[API] Fetching crew details from /crews/' + crewId);
        const crewData = await api(`/crews/${crewId}`);
        
        console.log('[API] Crew response:', crewData);
        
        if (crewData.success && crewData.crew) {
            const crew = crewData.crew;
            const members = crew.members || [];
            
            console.log('[Agents] Found members:', members.length);
            
            if (members.length === 0) {
                fromSelect.innerHTML = '<option value="">No members in crew</option>';
                toSelect.innerHTML = '<option value="">No members in crew</option>';
                toast('This crew has no members. Add members first.', 'warning');
                return;
            }
            
            const agentHtml = members.map(m => 
                `<option value="${m.agent_id}">${escapeHtml(m.agent_name)}</option>`
            ).join('');
            
            fromSelect.innerHTML = '<option value="">Select agent...</option>' + agentHtml;
            toSelect.innerHTML = '<option value="">Select agent...</option>' + agentHtml;
            
            console.log('[Agents] Populated dropdowns with', members.length, 'members');
        } else {
            console.error('[API] Crew data invalid:', crewData);
            toast('Failed to load crew members', 'error');
            fromSelect.innerHTML = '<option value="">Error loading members</option>';
            toSelect.innerHTML = '<option value="">Error loading members</option>';
        }
    } catch (e) {
        console.error('[Error] Failed to load crew agents:', e);
        toast('Failed to load crew members: ' + e.message, 'error');
        fromSelect.innerHTML = '<option value="">Error loading members</option>';
        toSelect.innerHTML = '<option value="">Error loading members</option>';
    }
}

async function sendCrewMessage() {
    console.log('[Message] Send button clicked');
    
    const crewId = document.getElementById('send-msg-crew').value.trim();
    const fromAgent = document.getElementById('send-msg-from').value.trim();
    const toAgent = document.getElementById('send-msg-to').value.trim();
    const messageType = document.getElementById('msg-type').value.trim();
    const content = document.getElementById('msg-content').value.trim();
    
    console.log('[Message] Raw Data:', { crewId, fromAgent, toAgent, messageType, contentLen: content.length });
    
    // Validation checks
    if (!crewId) {
        toast('❌ Please select a crew', 'error');
        return;
    }
    if (!fromAgent) {
        toast('❌ Please select a FROM agent', 'error');
        document.getElementById('send-msg-from').focus();
        return;
    }
    if (!toAgent) {
        toast('❌ Please select a TO agent', 'error');
        document.getElementById('send-msg-to').focus();
        return;
    }
    if (!content) {
        toast('❌ Please write a message', 'error');
        document.getElementById('msg-content').focus();
        return;
    }
    
    if (fromAgent === toAgent) {
        toast('⚠️ Cannot send message to the same agent', 'error');
        return;
    }
    
    try {
        // Build payload with content as dictionary
        const payload = {
            crew_id: String(crewId),
            from_agent: String(fromAgent),
            to_agent: String(toAgent),
            message_type: String(messageType || 'task'),
            content: {
                text: String(content),
                type: 'text'
            }
        };
        
        console.log('[API] Sending payload:', payload);
        console.log('[API] Payload JSON:', JSON.stringify(payload));
        
        const data = await api('/a2a/send', 'POST', payload);
        
        console.log('[API] Response:', data);
        
        if (data.success) {
            toast('✅ Message sent successfully!', 'success');
            document.getElementById('msg-content').value = '';
            // Reload communications history
            await loadCrewCommunications();
        } else {
            toast('❌ ' + (data.error || 'Failed to send message'), 'error');
        }
    } catch (e) {
        console.error('[Error] Send message error:', e);
        toast('❌ Error: ' + e.message, 'error');
    }
}

async function broadcastCrewMessage() {
    console.log('[Broadcast] Broadcast button clicked');
    
    const crewId = document.getElementById('send-msg-crew').value.trim();
    const fromAgent = document.getElementById('send-msg-from').value.trim();
    const content = document.getElementById('msg-content').value.trim();
    
    console.log('[Broadcast] Raw Data:', { crewId, fromAgent, contentLen: content.length });
    
    if (!crewId) {
        toast('❌ Please select a crew', 'error');
        return;
    }
    if (!fromAgent) {
        toast('❌ Please select a FROM agent', 'error');
        document.getElementById('send-msg-from').focus();
        return;
    }
    if (!content) {
        toast('❌ Please write a message', 'error');
        document.getElementById('msg-content').focus();
        return;
    }
    
    try {
        // Build payload with content as dictionary
        const payload = {
            crew_id: String(crewId),
            from_agent: String(fromAgent),
            message_type: 'broadcast',
            content: {
                text: String(content),
                type: 'text'
            }
        };
        
        console.log('[API] Broadcasting payload:', payload);
        console.log('[API] Payload JSON:', JSON.stringify(payload));
        
        const data = await api('/a2a/broadcast', 'POST', payload);
        
        console.log('[API] Response:', data);
        
        if (data.success) {
            toast('✅ Message broadcast to all crew members!', 'success');
            document.getElementById('msg-content').value = '';
            // Reload communications history
            await loadCrewCommunications();
        } else {
            toast('❌ ' + (data.error || 'Failed to broadcast message'), 'error');
        }
    } catch (e) {
        console.error('[Error] Broadcast error:', e);
        toast('❌ Error: ' + e.message, 'error');
    }
}
