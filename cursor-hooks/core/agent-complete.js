/**
 * Cursor IDE Agent Complete Hook
 * Automatically consolidates Agent outcomes and stores them as memories
 * 
 * Adapted from Claude Code session-end.js for Cursor IDE Agent/Composer
 */

const fs = require('fs').promises;
const path = require('path');

// Import utilities
const { detectProjectContext } = require('../utilities/project-detector');
const { MemoryClient } = require('../utilities/memory-client');
const { getCursorContext } = require('../utilities/cursor-adapter');

/**
 * Load hook configuration
 */
async function loadConfig() {
    try {
        const configPath = path.join(__dirname, '../config.json');
        const configData = await fs.readFile(configPath, 'utf8');
        return JSON.parse(configData);
    } catch (error) {
        console.warn('[Cursor Memory Hook] Using default configuration:', error.message);
        return {
            memoryService: {
                protocol: 'auto',
                preferredProtocol: 'http',
                fallbackEnabled: true,
                http: {
                    endpoint: 'http://127.0.0.1:8889',
                    apiKey: 'test-key-123'
                },
                defaultTags: ['cursor', 'auto-generated'],
                enableSessionConsolidation: true
            },
            sessionAnalysis: {
                extractTopics: true,
                extractDecisions: true,
                extractInsights: true,
                extractCodeChanges: true,
                extractNextSteps: true,
                minSessionLength: 100
            },
            output: {
                verbose: true
            }
        };
    }
}

/**
 * Detect workspace context for Cursor IDE
 */
async function detectWorkspaceContext() {
    const workspace = process.env.CURSOR_WORKSPACE || 
                     process.env.VSCODE_CWD || 
                     process.cwd();
    
    return {
        workspace,
        platform: process.platform,
        timestamp: Date.now()
    };
}

/**
 * Analyze Agent conversation to extract key information
 * This is a simplified version - in production, you'd parse actual conversation history
 */
function analyzeAgentOutcome() {
    const analysis = {
        topics: [],
        decisions: [],
        insights: [],
        codeChanges: [],
        nextSteps: [],
        sessionDuration: 0,
        confidence: 0.7  // Default confidence for basic extraction
    };
    
    // In Cursor IDE, we don't have direct access to conversation history
    // This would need to be enhanced with actual Agent conversation data
    // For now, we create a minimal outcome based on workspace state
    
    analysis.topics.push('agent-session');
    
    return analysis;
}

/**
 * Generate session summary from analysis
 */
function generateSessionSummary(analysis, projectContext) {
    const parts = [];
    
    // Add project context
    if (projectContext && projectContext.name) {
        parts.push(`Agent session in project: ${projectContext.name}`);
    }
    
    // Add topics
    if (analysis.topics && analysis.topics.length > 0) {
        parts.push(`Topics: ${analysis.topics.join(', ')}`);
    }
    
    // Add decisions
    if (analysis.decisions && analysis.decisions.length > 0) {
        parts.push('\nDecisions made:');
        analysis.decisions.slice(0, 3).forEach(decision => {
            parts.push(`- ${decision}`);
        });
    }
    
    // Add insights
    if (analysis.insights && analysis.insights.length > 0) {
        parts.push('\nKey insights:');
        analysis.insights.slice(0, 3).forEach(insight => {
            parts.push(`- ${insight}`);
        });
    }
    
    // Add code changes
    if (analysis.codeChanges && analysis.codeChanges.length > 0) {
        parts.push('\nCode changes:');
        analysis.codeChanges.slice(0, 3).forEach(change => {
            parts.push(`- ${change}`);
        });
    }
    
    // Add next steps
    if (analysis.nextSteps && analysis.nextSteps.length > 0) {
        parts.push('\nNext steps:');
        analysis.nextSteps.slice(0, 3).forEach(step => {
            parts.push(`- ${step}`);
        });
    }
    
    return parts.join('\n');
}

/**
 * Build tags for the session memory
 */
function buildSessionTags(projectContext, analysis, config) {
    const tags = [...(config.memoryService.defaultTags || [])];
    
    // Add project tags
    if (projectContext) {
        if (projectContext.name) {
            tags.push(projectContext.name.toLowerCase().replace(/\s+/g, '-'));
        }
        if (projectContext.language) {
            tags.push(projectContext.language.toLowerCase());
        }
        if (projectContext.framework) {
            tags.push(projectContext.framework.toLowerCase());
        }
    }
    
    // Add topic tags
    if (analysis.topics) {
        analysis.topics.forEach(topic => {
            tags.push(topic.toLowerCase().replace(/\s+/g, '-'));
        });
    }
    
    // Add session-specific tags
    tags.push('agent-session');
    tags.push('session-outcome');
    
    // Deduplicate
    return [...new Set(tags)];
}

/**
 * Main hook execution
 */
async function onAgentComplete() {
    try {
        const config = await loadConfig();
        const cursorContext = await getCursorContext();
        const workspaceInfo = await detectWorkspaceContext();
        
        if (!config.memoryService.enableSessionConsolidation) {
            if (config.output.verbose) {
                console.log('[Cursor Memory Hook] Session consolidation disabled');
            }
            return;
        }
        
        if (config.output.verbose) {
            console.log('\n[Cursor Memory Hook] Agent completing...');
            console.log(`[Cursor Memory Hook] Workspace: ${workspaceInfo.workspace}`);
        }
        
        // Detect project context
        const projectContext = await detectProjectContext(workspaceInfo.workspace);
        
        // Analyze Agent outcomes
        const analysis = analyzeAgentOutcome();
        
        // Check if session was meaningful (meets minimum length)
        if (analysis.sessionDuration < config.sessionAnalysis.minSessionLength) {
            if (config.output.verbose) {
                console.log('[Cursor Memory Hook] Session too short for consolidation');
            }
            return;
        }
        
        // Generate session summary
        const summary = generateSessionSummary(analysis, projectContext);
        
        if (!summary || summary.length < 50) {
            if (config.output.verbose) {
                console.log('[Cursor Memory Hook] No meaningful outcomes to store');
            }
            return;
        }
        
        // Build tags
        const tags = buildSessionTags(projectContext, analysis, config);
        
        // Initialize memory client
        const memoryClient = new MemoryClient(config.memoryService);
        
        // Store session outcome
        const memoryData = {
            content: summary,
            memory_type: 'session-outcome',
            tags: tags,
            metadata: {
                project: projectContext?.name || 'unknown',
                language: projectContext?.language || 'unknown',
                framework: projectContext?.framework || null,
                workspace: workspaceInfo.workspace,
                platform: workspaceInfo.platform,
                timestamp: new Date().toISOString(),
                agent_type: 'cursor',
                topics: analysis.topics,
                confidence: analysis.confidence
            }
        };
        
        const result = await memoryClient.storeMemory(memoryData);
        
        if (result.success || result.content_hash) {
            if (config.output.verbose) {
                console.log('[Cursor Memory Hook] Session outcome stored successfully');
                if (result.content_hash) {
                    console.log(`[Cursor Memory Hook] Memory hash: ${result.content_hash.substring(0, 8)}...`);
                }
            }
        } else {
            if (config.output.verbose) {
                console.warn('[Cursor Memory Hook] Failed to store session outcome:', result.error || 'Unknown error');
            }
        }
        
    } catch (error) {
        console.error('[Cursor Memory Hook] Error:', error.message);
        // Fail gracefully - don't block Agent completion
    }
}

/**
 * Hook metadata for Cursor IDE
 */
module.exports = {
    name: 'cursor-memory-awareness-agent-complete',
    version: '1.0.0',
    description: 'Automatically consolidate and store Agent outcomes',
    trigger: 'PostToolUse',
    handler: onAgentComplete,
    config: {
        async: true,
        timeout: 15000, // 15 second timeout
        priority: 'normal'
    }
};

// Direct execution support
if (require.main === module) {
    onAgentComplete()
        .then(() => {
            if (process.env.DEBUG) {
                console.log('[Cursor Memory Hook] Hook execution completed');
            }
        })
        .catch(error => {
            console.error('[Cursor Memory Hook] Hook execution failed:', error.message);
            process.exit(1);
        });
}

