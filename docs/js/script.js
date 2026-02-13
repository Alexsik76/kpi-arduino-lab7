import { CONFIG, state, setHost, getUrl, fetchOptions } from './config.js';
import { sendMoveManaged, sendServoManaged, sendMode } from './network.js';

// --- DOM Elements ---
const els = {
    manualCheck: document.getElementById('manual-mode-toggle'),
    localCheck: document.getElementById('local-mode-toggle'),
    // Select both side panels
    sidePanels: document.querySelectorAll('.panel'),
    dot: document.getElementById('status-dot'),
    text: document.getElementById('status-text'),
    container: document.getElementById('video-container'),
    // Docs link removed from new HTML, but keeping safe check
    docsLink: document.getElementById('link-docs') 
};

// --- Initialization ---
document.addEventListener('DOMContentLoaded', () => {
    // 1. Restore Local Mode Toggle
    const isLocal = state.currentHost === CONFIG.hosts.LOCAL;
    els.localCheck.checked = isLocal;
    
    // 2. Initialize UI State
    updatePanelState();
    if (els.docsLink) updateDocsLink();

    // 3. Start Loop
    checkSystem();
    setInterval(checkSystem, CONFIG.interval);
    
    // 4. Start Control Loop (20Hz)
    setInterval(controlLoop, 50);
});

// --- Event Listeners ---

// 1. Local Mode Toggle
els.localCheck.addEventListener('change', (e) => {
    setHost(e.target.checked);
    if (els.docsLink) updateDocsLink();
    checkSystem(); // Re-ping immediately
    if (state.isOnline) goOnline(); // Refresh video feed
});

// 2. Manual Mode Toggle
els.manualCheck.addEventListener('change', (e) => {
    state.manualMode = e.target.checked;
    updatePanelState();
    sendMode(state.manualMode);
});

// 3. Button Inputs (Mouse/Touch)
document.querySelectorAll('button[data-action]').forEach(btn => {
    const action = btn.dataset.action;
    
    const start = (e) => { 
        if (!state.manualMode) return;
        e.preventDefault(); 
        setInput(action, true); 
        btn.classList.add('active'); // Visual feedback
    };
    
    const end = (e) => { 
        if (!state.manualMode) return;
        e.preventDefault(); 
        setInput(action, false); 
        btn.classList.remove('active');
    };

    btn.addEventListener('mousedown', start);
    btn.addEventListener('mouseup', end);
    btn.addEventListener('touchstart', start);
    btn.addEventListener('touchend', end);
    btn.addEventListener('mouseleave', end);
});

// 4. Center Camera
const btnCenter = document.getElementById('btn-center-cam');
if (btnCenter) {
    btnCenter.addEventListener('click', () => {
        if (!state.manualMode) return;
        state.pan = 90;
        state.tilt = 90;
        sendServoManaged(90, 90);
    });
}

// 5. Keyboard Inputs
document.addEventListener('keydown', (e) => {
    if (!state.manualMode || e.repeat) return;
    mapKeys(e.key, true);
});

document.addEventListener('keyup', (e) => {
    if (!state.manualMode) return;
    mapKeys(e.key, false);
});

// --- Logic Helpers ---

function updatePanelState() {
    // Toggle visibility of both side panels
    const displayValue = state.manualMode ? 'flex' : 'none';
    els.sidePanels.forEach(panel => {
        panel.style.display = displayValue;
    });
}

function updateDocsLink() {
    if (els.docsLink) els.docsLink.href = getUrl(CONFIG.endpoints.docs);
}

function setInput(action, active) {
    if (!state.manualMode) return;
    state.input[action] = active;
}

function mapKeys(key, active) {
    // Highlight UI buttons on keypress
    const highlightBtn = (act) => {
        const btn = document.querySelector(`button[data-action="${act}"]`);
        if (btn) active ? btn.classList.add('active') : btn.classList.remove('active');
    };

    switch(key) {
        case 'w': case 'W': setInput('forward', active); highlightBtn('forward'); break;
        case 's': case 'S': setInput('backward', active); highlightBtn('backward'); break;
        case 'a': case 'A': setInput('left', active); highlightBtn('left'); break;
        case 'd': case 'D': setInput('right', active); highlightBtn('right'); break;
        case 'ArrowUp': setInput('camUp', active); highlightBtn('camUp'); break;
        case 'ArrowDown': setInput('camDown', active); highlightBtn('camDown'); break;
        case 'ArrowLeft': setInput('camLeft', active); highlightBtn('camLeft'); break;
        case 'ArrowRight': setInput('camRight', active); highlightBtn('camRight'); break;
    }
}

// --- Control Loop ---
let lastLeft = 0;
let lastRight = 0;
let lastSentTime = 0;

function controlLoop() {
    if (!state.manualMode) return;
    processPlatform();
    processCamera();
}

function processPlatform() {
    let speed = 100;
    let turn = 35;
    let red = 0.5;
    let l = 0, r = 0;

    if (state.input.forward) { l = speed; r = speed; }
    else if (state.input.backward) { l = -speed; r = -speed; }

    if (state.input.left) {
        if (l === 0 && r === 0) { l = -turn; r = turn; }
        else { l *= red; }
    } else if (state.input.right) {
        if (l === 0 && r === 0) { l = turn; r = -turn; }
        else { r *= red; }
    }

    const curL = Math.round(l);
    const curR = Math.round(r);
    const now = Date.now();
    const isMoving = (curL !== 0 || curR !== 0);
    const changed = (curL !== lastLeft || curR !== lastRight);
    
    // Heartbeat logic to prevent runaway robot if connection drops
    const heartbeat = isMoving && (now - lastSentTime > 200);

    if (changed || heartbeat) {
        lastLeft = curL;
        lastRight = curR;
        lastSentTime = now;
        sendMoveManaged(curL, curR);
    }
}

function processCamera() {
    let changed = false;
    const step = 2; // Increased speed slightly for better feel

    if (state.input.camUp && state.tilt > 50) { state.tilt -= step; changed = true; }
    if (state.input.camDown && state.tilt < 130) { state.tilt += step; changed = true; }
    if (state.input.camLeft && state.pan < 180) { state.pan += step; changed = true; }
    if (state.input.camRight && state.pan > 0) { state.pan -= step; changed = true; }

    if (changed) {
        sendServoManaged(state.pan, state.tilt);
    }
}

// --- System Status ---
state.isOnline = false;

async function checkSystem() {
    try {
        const res = await fetch(getUrl(CONFIG.endpoints.health), fetchOptions());
        if (res.ok) {
            if (!state.isOnline) goOnline();
            
            // Sync mode state from server
            try {
                const modeRes = await fetch(getUrl(CONFIG.endpoints.mode), fetchOptions());
                if (modeRes.ok) {
                    const data = await modeRes.json();
                    const serverMode = data.manual_mode;
                    if (serverMode !== state.manualMode) {
                        state.manualMode = serverMode;
                        els.manualCheck.checked = serverMode;
                        updatePanelState();
                    }
                }
            } catch (e) {
                // Ignore mode sync errors
            }
        } else {
            if (state.isOnline) goOffline();
        }
    } catch (e) {
        if (state.isOnline) goOffline();
    }
}

function goOnline() {
    state.isOnline = true;
    els.dot.className = 'status-dot on';
    els.text.innerText = 'ONLINE';
    els.container.innerHTML = `<img src="${getUrl(CONFIG.endpoints.feed)}?t=${Date.now()}" alt="Live Feed" crossorigin="anonymous">`;
}

function goOffline() {
    state.isOnline = false;
    els.dot.className = 'status-dot off';
    els.text.innerText = 'OFFLINE';
    els.text.style.color = '#ff1744';
    els.container.innerHTML = `<div class="offline-placeholder">⚠️ SIGNAL LOST</div>`;
}