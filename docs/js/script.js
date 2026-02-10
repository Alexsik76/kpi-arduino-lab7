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
 * Platform Movement Control
 */
async function startMove(direction) {
    if (!manualMode) return;
    
    let left = 0, right = 0;
    const speed = 100;

    switch(direction) {
        case 'forward': left = speed; right = speed; break;
        case 'backward': left = -speed; right = -speed; break;
        case 'left': left = -speed; right = speed; break;
        case 'right': left = speed; right = -speed; break;
    }

    sendMove(left, right);
}

function stopMove() {
    if (!manualMode) return;
    sendMove(0, 0);
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
 * Servo Control
 */
async function moveServo(direction) {
    if (!manualMode) return;

    const step = 10;
    
    switch(direction) {
        case 'up': currentTilt = Math.max(50, currentTilt - step); break;
        case 'down': currentTilt = Math.min(130, currentTilt + step); break;
        case 'left': currentPan = Math.min(180, currentPan + step); break;
        case 'right': currentPan = Math.max(0, currentPan - step); break;
    }

    try {
        await fetch(`${CONFIG.host}${CONFIG.endpoints.servo}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ pan: currentPan, tilt: currentTilt })
        });
    } catch (e) {
        console.error("Servo failed:", e);
    }
}

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
        const response = await fetch(`${CONFIG.host}${CONFIG.endpoints.health}`);
        
        if (response.ok) {
            if (!isOnline) goOnline();
        } else {
            if (isOnline) goOffline();
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