/**
 * Cursor CLI Adapter
 * Handles Cursor-specific session management and state persistence
 */

const fs = require('fs').promises;
const path = require('path');
const os = require('os');

// Configuration paths
const CURSOR_CONFIG_DIR = path.join(os.homedir(), '.cursor');
const SESSION_STATE_FILE = path.join(CURSOR_CONFIG_DIR, 'session-state.json');
const LAST_EDIT_TRIGGER_FILE = path.join(CURSOR_CONFIG_DIR, 'last-edit-trigger.json');

/**
 * Session state structure
 * @typedef {Object} SessionState
 * @property {number|null} lastActivity - Timestamp of last activity
 * @property {string|null} sessionId - Current session identifier
 * @property {boolean} sessionStarted - Whether session has been initialized
 * @property {string|null} workingDirectory - Current working directory
 * @property {number|null} sessionStartTime - When session started
 */

class CursorSessionTracker {
    constructor(config = {}) {
        this.sessionTimeout = config.cursorSpecific?.sessionTimeout || 1800000; // 30 minutes default
        this.editThrottleMs = config.cursorSpecific?.editThrottleMs || 5000; // 5 seconds default
    }

    /**
     * Load current session state from persistent storage
     * @returns {Promise<SessionState>}
     */
    async loadSessionState() {
        try {
            const data = await fs.readFile(SESSION_STATE_FILE, 'utf8');
            return JSON.parse(data);
        } catch (error) {
            // Return default state if file doesn't exist or is invalid
            return {
                lastActivity: null,
                sessionId: null,
                sessionStarted: false,
                workingDirectory: null,
                sessionStartTime: null
            };
        }
    }

    /**
     * Save session state to persistent storage
     * @param {SessionState} state
     */
    async saveSessionState(state) {
        try {
            // Ensure directory exists
            await fs.mkdir(CURSOR_CONFIG_DIR, { recursive: true });
            
            await fs.writeFile(
                SESSION_STATE_FILE,
                JSON.stringify(state, null, 2),
                'utf8'
            );
        } catch (error) {
            console.warn('[Cursor Adapter] Failed to save session state:', error.message);
        }
    }

    /**
     * Determine if a new session should be started
     * @returns {Promise<boolean>}
     */
    async shouldStartNewSession() {
        const state = await this.loadSessionState();
        
        // Always start if no previous session
        if (!state.lastActivity || !state.sessionStarted) {
            return true;
        }
        
        // Check if session has timed out
        const timeSinceLastActivity = Date.now() - state.lastActivity;
        return timeSinceLastActivity > this.sessionTimeout;
    }

    /**
     * Initialize a new session
     * @param {string} workingDirectory
     * @returns {Promise<string>} Session ID
     */
    async startNewSession(workingDirectory = process.cwd()) {
        const sessionId = `cursor-${Date.now()}-${Math.random().toString(36).substring(7)}`;
        const now = Date.now();
        
        const state = {
            lastActivity: now,
            sessionId: sessionId,
            sessionStarted: true,
            workingDirectory: workingDirectory,
            sessionStartTime: now
        };
        
        await this.saveSessionState(state);
        return sessionId;
    }

    /**
     * Update session activity timestamp
     */
    async updateActivity() {
        const state = await this.loadSessionState();
        state.lastActivity = Date.now();
        await this.saveSessionState(state);
    }

    /**
     * Reset/clear session state
     */
    async resetSession() {
        const state = {
            lastActivity: null,
            sessionId: null,
            sessionStarted: false,
            workingDirectory: null,
            sessionStartTime: null
        };
        await this.saveSessionState(state);
    }

    /**
     * Get current session information
     * @returns {Promise<SessionState>}
     */
    async getSessionInfo() {
        return await this.loadSessionState();
    }

    /**
     * Check if enough time has passed since last edit trigger
     * Used to throttle afterFileEdit hooks
     * @returns {Promise<boolean>}
     */
    async shouldTriggerMidConversation() {
        try {
            const data = await fs.readFile(LAST_EDIT_TRIGGER_FILE, 'utf8');
            const { lastTrigger } = JSON.parse(data);
            
            const timeSinceLastTrigger = Date.now() - lastTrigger;
            if (timeSinceLastTrigger < this.editThrottleMs) {
                return false; // Too soon
            }
        } catch {
            // File doesn't exist, first trigger is allowed
        }
        
        // Update last trigger time
        await this._updateLastEditTrigger();
        return true;
    }

    /**
     * Update the last edit trigger timestamp
     * @private
     */
    async _updateLastEditTrigger() {
        try {
            await fs.mkdir(CURSOR_CONFIG_DIR, { recursive: true });
            await fs.writeFile(
                LAST_EDIT_TRIGGER_FILE,
                JSON.stringify({ lastTrigger: Date.now() }, null, 2),
                'utf8'
            );
        } catch (error) {
            console.warn('[Cursor Adapter] Failed to update edit trigger:', error.message);
        }
    }

    /**
     * Calculate session duration in milliseconds
     * @returns {Promise<number|null>}
     */
    async getSessionDuration() {
        const state = await this.loadSessionState();
        if (!state.sessionStartTime) {
            return null;
        }
        return Date.now() - state.sessionStartTime;
    }

    /**
     * Check if session is still active (not timed out)
     * @returns {Promise<boolean>}
     */
    async isSessionActive() {
        const state = await this.loadSessionState();
        if (!state.lastActivity || !state.sessionStarted) {
            return false;
        }
        
        const timeSinceLastActivity = Date.now() - state.lastActivity;
        return timeSinceLastActivity < this.sessionTimeout;
    }
}

/**
 * Format memories for Cursor CLI output
 * @param {Array} memories - Array of memory objects
 * @param {Object} projectContext - Project context information
 * @param {Object} options - Formatting options
 * @returns {string} Formatted output
 */
function formatMemoriesForCursor(memories, projectContext, options = {}) {
    const {
        verbose = true,
        showDetails = true,
        includeScores = false
    } = options;
    
    const output = [];
    
    // Header
    output.push('');
    output.push('═══════════════════════════════════════════════════════════');
    output.push('📚 RELEVANT PROJECT MEMORIES (Cursor)');
    output.push('═══════════════════════════════════════════════════════════');
    output.push('');
    
    // Project context
    if (projectContext && verbose) {
        output.push(`📁 Project: ${projectContext.name || 'Unknown'}`);
        if (projectContext.language) {
            output.push(`   Language: ${projectContext.language}`);
        }
        if (projectContext.framework) {
            output.push(`   Framework: ${projectContext.framework}`);
        }
        if (projectContext.gitBranch) {
            output.push(`   Git Branch: ${projectContext.gitBranch}`);
        }
        output.push('');
    }
    
    // Memory count
    if (memories.length === 0) {
        output.push('ℹ️  No relevant memories found for this context');
        output.push('');
    } else {
        output.push(`💡 Found ${memories.length} relevant memor${memories.length === 1 ? 'y' : 'ies'}:`);
        output.push('');
        
        // Individual memories
        memories.forEach((memory, idx) => {
            const memoryNumber = `${idx + 1}.`;
            const summary = memory.summary || memory.content?.substring(0, 120) || 'No summary';
            
            output.push(`${memoryNumber} ${summary}`);
            
            if (showDetails) {
                // Tags
                if (memory.tags && memory.tags.length > 0) {
                    output.push(`   🏷️  Tags: ${memory.tags.join(', ')}`);
                }
                
                // Age
                if (memory.created_at) {
                    const age = formatAge(memory.created_at);
                    output.push(`   📅 Age: ${age}`);
                }
                
                // Relevance score (optional)
                if (includeScores && memory.relevanceScore !== undefined) {
                    output.push(`   📊 Relevance: ${(memory.relevanceScore * 100).toFixed(0)}%`);
                }
            }
            
            output.push('');
        });
    }
    
    // Footer
    output.push('═══════════════════════════════════════════════════════════');
    output.push('');
    
    return output.join('\n');
}

/**
 * Format age from timestamp
 * @param {string|number} timestamp
 * @returns {string}
 */
function formatAge(timestamp) {
    const now = Date.now();
    const then = typeof timestamp === 'string' ? new Date(timestamp).getTime() : timestamp;
    const diffMs = now - then;
    
    const diffMinutes = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);
    
    if (diffMinutes < 60) {
        return `${diffMinutes} minute${diffMinutes === 1 ? '' : 's'} ago`;
    } else if (diffHours < 24) {
        return `${diffHours} hour${diffHours === 1 ? '' : 's'} ago`;
    } else if (diffDays < 30) {
        return `${diffDays} day${diffDays === 1 ? '' : 's'} ago`;
    } else {
        const diffMonths = Math.floor(diffDays / 30);
        return `${diffMonths} month${diffMonths === 1 ? '' : 's'} ago`;
    }
}

/**
 * Get Cursor-specific context information
 * @returns {Promise<Object>}
 */
async function getCursorContext() {
    return {
        platform: process.platform,
        nodeVersion: process.version,
        workingDirectory: process.cwd(),
        timestamp: Date.now(),
        environment: process.env.CURSOR_ENV || 'production'
    };
}

/**
 * Check if running in Cursor CLI environment
 * @returns {boolean}
 */
function isCursorEnvironment() {
    // Check for Cursor-specific environment variables
    return !!(
        process.env.CURSOR_CLI ||
        process.env.CURSOR_SESSION_ID ||
        process.env.CURSOR_ENV
    );
}

module.exports = {
    CursorSessionTracker,
    formatMemoriesForCursor,
    formatAge,
    getCursorContext,
    isCursorEnvironment,
    CURSOR_CONFIG_DIR,
    SESSION_STATE_FILE
};

