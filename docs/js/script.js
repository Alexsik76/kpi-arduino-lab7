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
 * Input State & Game Loop
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
    
    // Prevent mouse stickiness if dragging out of button
    if (!active) {
        // safety clear all if needed, but usually just the one is enough
    }
}

// Main Control Loop (20Hz = 50ms)
setInterval(() => {
    if (!manualMode) return;
    processPlatform();
    processCamera();
}, 50);

/**
 * Platform Logic
 */
let lastLeft = 0;
let lastRight = 0;

function processPlatform() {
    let speed = 100;
    let turnSpeed = 35; // Significantly reduced for finer control
    let turnReduction = 0.5; // Slow down inner wheel for turns while moving

    let left = 0;
    let right = 0;

    // Forward/Backward base
    if (inputState.forward) {
        left = speed;
        right = speed;
    } else if (inputState.backward) {
        left = -speed;
        right = -speed;
    }

    // Turning mixing
    if (inputState.left) {
        if (left === 0 && right === 0) {
            // Spin in place (Left)
            left = -turnSpeed;
            right = turnSpeed;
        } else {
            // Turn while moving
            left *= turnReduction; 
        }
    } else if (inputState.right) {
        if (left === 0 && right === 0) {
            // Spin in place (Right)
            left = turnSpeed;
            right = -turnSpeed;
        } else {
            // Turn while moving
            right *= turnReduction;
        }
    }

    // Only send if changed
    if (Math.round(left) !== lastLeft || Math.round(right) !== lastRight) {
        lastLeft = Math.round(left);
        lastRight = Math.round(right);
        sendMove(lastLeft, lastRight);
    }
}

async function sendMove(left, right) {
    try {
        await fetch(`${CONFIG.host}${CONFIG.endpoints.move}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ left, right })
        });
    } catch (e) {
        console.error("Move failed:", e);
    }
}

/**
 * Camera Logic
 */
let lastPan = -1;
let lastTilt = -1;

function processCamera() {
    const step = 1; // 1 degree per tick (20 deg/sec)
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
        // Rate limit sending commands is handled by backend somewhat, 
        // but we can also optimize here to not flood network if backend is slow.
        // For now, fire and forget.
        sendServoCommand();
        lastPan = currentPan;
        lastTilt = currentTilt;
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
    sendServoCommand();
}

async function sendServoCommand() {
    try {
        await fetch(`${CONFIG.host}${CONFIG.endpoints.servo}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ pan: currentPan, tilt: currentTilt })
        });
    } catch (e) {
        // console.error("Servo failed:", e);
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
 * DOM Elements Cache
 */
const els = {
    dot: document.getElementById('status-dot'),
    text: document.getElementById('status-text'),
    container: document.getElementById('video-container')
};

let isOnline = false;

/**
 * Main Status Checker
 */
async function checkSystem() {
    try {
        // Parallel checks
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
            // Only update if changed to avoid interference? 
            // Actually, server truth should prevail on sync.
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

/**
 * Switch UI to Online State
 */
function goOnline() {
    isOnline = true;
    els.dot.className = 'status-dot on';
    els.text.innerText = 'ONLINE';
    els.text.style.color = '#2ecc71';
    
    // Inject Stream with cache-buster
    els.container.innerHTML = `<img src="${CONFIG.host}${CONFIG.endpoints.feed}?t=${Date.now()}" alt="Live Feed">`;
}

/**
 * Switch UI to Offline State
 */
function goOffline() {
    isOnline = false;
    els.dot.className = 'status-dot off';
    els.text.innerText = 'OFFLINE';
    els.text.style.color = '#e74c3c';
    
    els.container.innerHTML = `<div class="offline-msg">⚠️ SIGNAL LOST</div>`;
}

// Global initialization
document.addEventListener('DOMContentLoaded', () => {
    checkSystem();
    setInterval(checkSystem, CONFIG.interval);
});