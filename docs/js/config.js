// js/config.js

export const CONFIG = {
    hosts: {
        GLOBAL: 'https://robot.lab.vn.ua',
        LOCAL: 'http://lb7w.lan:8000'
    },
    endpoints: {
        health: '/health',
        feed: '/video_feed',
        mode: '/control/mode',
        move: '/control/move',
        servo: '/control/servo',
        docs: '/docs'
    },
    interval: 5000
};

// State Object
export const state = {
    manualMode: false,
    currentHost: localStorage.getItem('robot_host') || CONFIG.hosts.GLOBAL, // Load from memory
    
    // Servo State
    pan: 90,
    tilt: 90,

    // Input State
    input: {
        forward: false,
        backward: false,
        left: false,
        right: false,
        camUp: false,
        camDown: false,
        camLeft: false,
        camRight: false
    }
};

// Helper to switch host
export function setHost(isLocal) {
    state.currentHost = isLocal ? CONFIG.hosts.LOCAL : CONFIG.hosts.GLOBAL;
    localStorage.setItem('robot_host', state.currentHost); // Persist
    console.log(`Switched to ${isLocal ? 'LOCAL' : 'GLOBAL'} mode: ${state.currentHost}`);
}

// Helper to get full URL
export function getUrl(endpoint) {
    return `${state.currentHost}${endpoint}`;
}