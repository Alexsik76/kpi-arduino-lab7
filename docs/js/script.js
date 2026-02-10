/**
 * Configuration for the Tracking System
 */
const CONFIG = {
    host: 'https://robot.lab.vn.ua',
    endpoints: {
        health: '/health',
        feed: '/video_feed',
        mode: '/control/mode',
        move: '/control/move',
        servo: '/control/servo'
    },
    interval: 5000
};

// State
let manualMode = false;
let currentPan = 90;
let currentTilt = 90;

/**
 * Toggle Manual Mode
 */
async function toggleManualMode() {
    const checkbox = document.getElementById('manual-mode-toggle');
    const controls = document.getElementById('manual-controls');
    manualMode = checkbox.checked;

    controls.style.display = manualMode ? 'block' : 'none';

    try {
        await fetch(`${CONFIG.host}${CONFIG.endpoints.mode}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ enabled: manualMode })
        });
    } catch (e) {
        console.error("Failed to toggle mode:", e);
    }
}

/**
 * Input State
 */
const inputState = {
    forward: false,
    backward: false,
    left: false,
    right: false,
    camUp: false,
    camDown: false,
    camLeft: false,
    camRight: false
};

// Helper to update state from HTML buttons
function setInput(action, active) {
    if (!manualMode) return;
    inputState[action] = active;
}

// Main Control Loop (20Hz = 50ms)
setInterval(() => {
    if (!manualMode) return;
    processPlatform();
    processCamera();
}, 50);

/**
 * Platform Logic & Network Flow Control
 */
let lastLeft = 0;
let lastRight = 0;
let lastSentTime = 0;

// Network Flow Control Variables
let isMoveRequestPending = false;
let nextMoveCommand = null;

function processPlatform() {
    const speed = 100;
    const turnSpeed = 35;
    const turnReduction = 0.5;

    let left = 0;
    let right = 0;

    // Forward/Backward base
    if (inputState.forward) { left = speed; right = speed; } 
    else if (inputState.backward) { left = -speed; right = -speed; }

    // Turning mixing
    if (inputState.left) {
        if (left === 0 && right === 0) { left = -turnSpeed; right = turnSpeed; } 
        else { left *= turnReduction; }
    } else if (inputState.right) {
        if (left === 0 && right === 0) { left = turnSpeed; right = -turnSpeed; } 
        else { right *= turnReduction; }
    }

    const now = Date.now();
    const currentLeft = Math.round(left);
    const currentRight = Math.round(right);
    
    const isChanged = (currentLeft !== lastLeft || currentRight !== lastRight);
    const isMoving = (currentLeft !== 0 || currentRight !== 0);
    const isHeartbeatNeeded = (now - lastSentTime > 200);

    if (isChanged || isHeartbeatNeeded) {
        lastLeft = currentLeft;
        lastRight = currentRight;
        lastSentTime = now;
        
        // Call the managed sender instead of direct fetch
        sendMoveManaged(lastLeft, lastRight);
    }
}

/**
 * Managed Sender
 * Implements a "latest-state" buffer. If a request is currently flying,
 * it queues the NEWEST command and sends it immediately after the current one finishes.
 * This prevents network flooding and ensures the "STOP" command is never lost in a queue.
 */
async function sendMoveManaged(left, right) {
    // If a request is already in progress, overwrite the "next" command with the latest state
    if (isMoveRequestPending) {
        nextMoveCommand = { left, right };
        return;
    }

    isMoveRequestPending = true;

    try {
        await fetchMove(left, right);
    } catch (e) {
        console.error("Move failed:", e);
    } finally {
        isMoveRequestPending = false;
        
        // If a new command arrived while we were busy, send it now
        if (nextMoveCommand) {
            const cmd = nextMoveCommand;
            nextMoveCommand = null; // Clear queue
            // Recursively call managed sender
            sendMoveManaged(cmd.left, cmd.right);
        }
    }
}

async function fetchMove(left, right) {
    await fetch(`${CONFIG.host}${CONFIG.endpoints.move}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ left, right })
    });
}

/**
 * Camera Logic
 */
let lastPan = -1;
let lastTilt = -1;
// Servo Flow Control
let isServoPending = false;
let nextServoCommand = null;

function processCamera() {
    const step = 1; 
    let changed = false;

    if (inputState.camUp) {
        if (currentTilt > 50) { currentTilt -= step; changed = true; }
    }
    if (inputState.camDown) {
        if (currentTilt < 130) { currentTilt += step; changed = true; }
    }
    if (inputState.camLeft) {
        if (currentPan < 180) { currentPan += step; changed = true; }
    }
    if (inputState.camRight) {
        if (currentPan > 0) { currentPan -= step; changed = true; }
    }

    if (changed || (currentPan !== lastPan || currentTilt !== lastTilt)) {
        lastPan = currentPan;
        lastTilt = currentTilt;
        sendServoManaged(lastPan, lastTilt);
    }
}

async function centerCamera() {
    if (!manualMode) return;
    currentPan = 90;
    currentTilt = 90;
    inputState.camUp = false;
    inputState.camDown = false;
    inputState.camLeft = false;
    inputState.camRight = false;
    sendServoManaged(90, 90);
}

// Similar managed sender for servos to prevent jitter
async function sendServoManaged(pan, tilt) {
    if (isServoPending) {
        nextServoCommand = { pan, tilt };
        return;
    }
    isServoPending = true;
    try {
        await fetch(`${CONFIG.host}${CONFIG.endpoints.servo}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ pan, tilt })
        });
    } catch (e) {
        // console.error("Servo failed:", e);
    } finally {
        isServoPending = false;
        if (nextServoCommand) {
            const cmd = nextServoCommand;
            nextServoCommand = null;
            sendServoManaged(cmd.pan, cmd.tilt);
        }
    }
}

/**
 * Keyboard Listeners
 */
document.addEventListener('keydown', (e) => {
    if (!manualMode || e.repeat) return;
    
    switch(e.key) {
        case 'w': case 'W': inputState.forward = true; break;
        case 's': case 'S': inputState.backward = true; break;
        case 'a': case 'A': inputState.left = true; break;
        case 'd': case 'D': inputState.right = true; break;
        
        case 'ArrowUp': inputState.camUp = true; e.preventDefault(); break;
        case 'ArrowDown': inputState.camDown = true; e.preventDefault(); break;
        case 'ArrowLeft': inputState.camLeft = true; e.preventDefault(); break;
        case 'ArrowRight': inputState.camRight = true; e.preventDefault(); break;
    }
});

document.addEventListener('keyup', (e) => {
    if (!manualMode) return;

    switch(e.key) {
        case 'w': case 'W': inputState.forward = false; break;
        case 's': case 'S': inputState.backward = false; break;
        case 'a': case 'A': inputState.left = false; break;
        case 'd': case 'D': inputState.right = false; break;
        
        case 'ArrowUp': inputState.camUp = false; break;
        case 'ArrowDown': inputState.camDown = false; break;
        case 'ArrowLeft': inputState.camLeft = false; break;
        case 'ArrowRight': inputState.camRight = false; break;
    }
});

/**
 * DOM Elements Cache & System Check (Unchanged logic, kept for completeness)
 */
const els = {
    dot: document.getElementById('status-dot'),
    text: document.getElementById('status-text'),
    container: document.getElementById('video-container')
};

let isOnline = false;

async function checkSystem() {
    try {
        const [healthRes, modeRes] = await Promise.all([
            fetch(`${CONFIG.host}${CONFIG.endpoints.health}`),
            fetch(`${CONFIG.host}${CONFIG.endpoints.mode}`)
        ]);
        
        if (healthRes.ok) {
            if (!isOnline) goOnline();
        } else {
            if (isOnline) goOffline();
        }

        if (modeRes.ok) {
            const data = await modeRes.json();
            if (manualMode !== data.manual_mode) {
                manualMode = data.manual_mode;
                document.getElementById('manual-mode-toggle').checked = manualMode;
                document.getElementById('manual-controls').style.display = manualMode ? 'block' : 'none';
            }
        }

    } catch (error) {
        if (isOnline) goOffline();
        console.warn("System unreachable");
    }
}

function goOnline() {
    isOnline = true;
    els.dot.className = 'status-dot on';
    els.text.innerText = 'ONLINE';
    els.text.style.color = '#2ecc71';
    els.container.innerHTML = `<img src="${CONFIG.host}${CONFIG.endpoints.feed}?t=${Date.now()}" alt="Live Feed">`;
}

function goOffline() {
    isOnline = false;
    els.dot.className = 'status-dot off';
    els.text.innerText = 'OFFLINE';
    els.text.style.color = '#e74c3c';
    els.container.innerHTML = `<div class="offline-msg">⚠️ SIGNAL LOST</div>`;
}

document.addEventListener('DOMContentLoaded', () => {
    checkSystem();
    setInterval(checkSystem, CONFIG.interval);
});