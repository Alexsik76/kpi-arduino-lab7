// js/network.js
import { getUrl, fetchOptions } from './config.js';

let isMovePending = false;
let nextMoveCmd = null;

let isServoPending = false;
let nextServoCmd = null;

// --- Platform Control (Managed) ---
export async function sendMoveManaged(left, right) {
    if (isMovePending) {
        nextMoveCmd = { left, right };
        return;
    }

    isMovePending = true;
    try {
        await fetch(getUrl('/control/move'), {
            ...fetchOptions(),
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ left, right })
        });
    } catch (e) {
        console.warn("Move command failed", e);
    } finally {
        isMovePending = false;
        if (nextMoveCmd) {
            const cmd = nextMoveCmd;
            nextMoveCmd = null;
            sendMoveManaged(cmd.left, cmd.right);
        }
    }
}

// --- Servo Control (Managed) ---
export async function sendServoManaged(pan, tilt) {
    if (isServoPending) {
        nextServoCmd = { pan, tilt };
        return;
    }
    isServoPending = true;
    try {
        await fetch(getUrl('/control/servo'), {
            ...fetchOptions(),
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ pan, tilt })
        });
    } catch (e) {
         // Silently fail for servos to keep smooth
    } finally {
        isServoPending = false;
        if (nextServoCmd) {
            const cmd = nextServoCmd;
            nextServoCmd = null;
            sendServoManaged(cmd.pan, cmd.tilt);
        }
    }
}

// --- Mode Toggle ---
export async function sendMode(enabled) {
    try {
        await fetch(getUrl('/control/mode'), {
            ...fetchOptions(),
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ enabled })
        });
    } catch (e) {
        console.error("Failed to toggle mode:", e);
    }
}