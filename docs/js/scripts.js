/**
 * Configuration for the Tracking System
 */
const CONFIG = {
    host: 'https://robot.lab.vn.ua',
    endpoints: {
        health: '/health',
        feed: '/video_feed'
    },
    interval: 5000 
};

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