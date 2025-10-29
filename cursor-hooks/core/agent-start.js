/**
 * Cursor IDE Agent Start Hook
 * Automatically injects relevant memories when Agent/Composer starts
 * 
 * Adapted from Claude Code session-start.js for Cursor IDE workspace context
 */

const fs = require('fs').promises;
const path = require('path');

// Import utilities (reused from Claude hooks)
const { detectProjectContext } = require('../utilities/project-detector');
const { scoreMemoryRelevance, analyzeMemoryAgeDistribution, calculateAdaptiveGitWeight } = require('../utilities/memory-scorer');
const { formatMemoriesForContext } = require('../utilities/context-formatter');
const { analyzeGitContext, buildGitContextQuery } = require('../utilities/git-analyzer');
const { MemoryClient } = require('../utilities/memory-client');

// Cursor-specific helpers
const { formatMemoriesForCursor, getCursorContext } = require('../utilities/cursor-adapter');

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
                    apiKey: 'test-key-123',
                    healthCheckTimeout: 3000,
                    useDetailedHealthCheck: false
                },
                mcp: {
                    serverCommand: ['uv', 'run', 'memory', 'server'],
                    serverWorkingDir: null,
                    connectionTimeout: 5000,
                    toolCallTimeout: 10000
                },
                defaultTags: ['cursor', 'auto-generated'],
                maxMemoriesPerSession: 8
            },
            projectDetection: {
                gitRepository: true,
                packageFiles: ['package.json', 'pyproject.toml', 'Cargo.toml'],
                frameworkDetection: true,
                languageDetection: true
            },
            output: {
                verbose: true,
                showMemoryDetails: true,
                showProjectDetails: true,
                cleanMode: false
            }
        };
    }
}

/**
 * Detect workspace context for Cursor IDE
 * Uses environment variables and process.cwd()
 */
async function detectWorkspaceContext() {
    // Cursor IDE provides workspace context
    const workspace = process.env.CURSOR_WORKSPACE || 
                     process.env.VSCODE_CWD || 
                     process.cwd();
    
    return {
        workspace,
        platform: process.platform,
        nodeVersion: process.version,
        timestamp: Date.now()
    };
}

/**
 * Main hook execution
 */
async function onAgentStart() {
    try {
        const config = await loadConfig();
        const cursorContext = await getCursorContext();
        const workspaceInfo = await detectWorkspaceContext();
        
        if (config.output.verbose) {
            console.log('\n[Cursor Memory Hook] Agent starting...');
            console.log(`[Cursor Memory Hook] Workspace: ${workspaceInfo.workspace}`);
        }
        
        // Detect project context
        const projectContext = await detectProjectContext(workspaceInfo.workspace);
        
        if (config.output.showProjectDetails && projectContext) {
            console.log(`[Cursor Memory Hook] Project: ${projectContext.name || 'Unknown'}`);
            if (projectContext.language) {
                console.log(`[Cursor Memory Hook] Language: ${projectContext.language}`);
            }
            if (projectContext.framework) {
                console.log(`[Cursor Memory Hook] Framework: ${projectContext.framework}`);
            }
        }
        
        // Initialize memory client
        const memoryClient = new MemoryClient(config.memoryService);
        
        // Check memory service health
        const healthResult = await memoryClient.getHealthStatus();
        if (!healthResult.success) {
            if (config.output.verbose) {
                console.warn('[Cursor Memory Hook] Memory service unavailable:', healthResult.error);
                console.log('[Cursor Memory Hook] Continuing without memory context');
            }
            return;
        }
        
        // Build query tags based on project context
        const queryTags = [];
        if (projectContext.name) queryTags.push(projectContext.name);
        if (projectContext.language) queryTags.push(projectContext.language.toLowerCase());
        if (projectContext.framework) queryTags.push(projectContext.framework.toLowerCase());
        
        // Add default tags from config
        if (config.memoryService.defaultTags) {
            queryTags.push(...config.memoryService.defaultTags);
        }
        
        // Analyze git context if enabled
        let gitContext = null;
        if (config.gitAnalysis && config.gitAnalysis.enabled) {
            gitContext = await analyzeGitContext(workspaceInfo.workspace, config.gitAnalysis);
            
            if (gitContext && config.output.verbose) {
                console.log(`[Cursor Memory Hook] Git: ${gitContext.branch || 'unknown branch'}, ${gitContext.recentCommits || 0} recent commits`);
            }
        }
        
        // Query for relevant memories
        const maxMemories = config.memoryService.maxMemoriesPerSession || 8;
        const memories = await queryRelevantMemories(
            memoryClient,
            projectContext,
            gitContext,
            queryTags,
            maxMemories,
            config
        );
        
        if (memories && memories.length > 0) {
            // Score and rank memories
            const scoredMemories = memories.map(memory => ({
                ...memory,
                relevanceScore: scoreMemoryRelevance(memory, projectContext, config.memoryScoring)
            }));
            
            // Sort by relevance
            scoredMemories.sort((a, b) => b.relevanceScore - a.relevanceScore);
            
            // Take top N
            const topMemories = scoredMemories.slice(0, maxMemories);
            
            // Format for Cursor Agent
            const formattedOutput = formatMemoriesForCursor(
                topMemories,
                projectContext,
                {
                    verbose: config.output.verbose,
                    showDetails: config.output.showMemoryDetails,
                    includeScores: config.output.showScoringDetails
                }
            );
            
            // Output to stdout for Agent to consume
            console.log(formattedOutput);
            
            if (config.output.verbose) {
                console.log(`[Cursor Memory Hook] Injected ${topMemories.length} relevant memories`);
            }
        } else {
            if (config.output.verbose) {
                console.log('[Cursor Memory Hook] No relevant memories found for this workspace');
            }
        }
        
    } catch (error) {
        console.error('[Cursor Memory Hook] Error:', error.message);
        // Fail gracefully - don't block Agent execution
    }
}

/**
 * Query memory service for relevant memories
 */
async function queryRelevantMemories(memoryClient, projectContext, gitContext, tags, maxCount, config) {
    try {
        const memories = [];
        
        // Phase 1: Recent memories for this project
        const recentMemories = await memoryClient.searchByTag(tags, 'AND');
        if (recentMemories && recentMemories.length > 0) {
            memories.push(...recentMemories);
        }
        
        // Phase 2: Git-context aware memories (if enabled)
        if (gitContext && config.gitAnalysis && config.gitAnalysis.enabled) {
            const gitQuery = buildGitContextQuery(gitContext);
            if (gitQuery) {
                const gitMemories = await memoryClient.retrieveMemory(gitQuery, maxCount);
                if (gitMemories && gitMemories.length > 0) {
                    // Boost git-related memories
                    gitMemories.forEach(memory => {
                        memory.gitContextBoost = true;
                    });
                    memories.push(...gitMemories);
                }
            }
        }
        
        // Deduplicate by content hash
        const uniqueMemories = [];
        const seen = new Set();
        
        for (const memory of memories) {
            const hash = memory.content_hash || memory.id;
            if (hash && !seen.has(hash)) {
                seen.add(hash);
                uniqueMemories.push(memory);
            }
        }
        
        return uniqueMemories;
        
    } catch (error) {
        console.warn('[Cursor Memory Hook] Failed to query memories:', error.message);
        return [];
    }
}

/**
 * Hook metadata for Cursor IDE
 */
module.exports = {
    name: 'cursor-memory-awareness-agent-start',
    version: '1.0.0',
    description: 'Automatically inject relevant memories when Cursor Agent starts',
    trigger: 'PreToolUse',
    handler: onAgentStart,
    config: {
        async: true,
        timeout: 10000, // 10 second timeout
        priority: 'high'
    }
};

// Direct execution support
if (require.main === module) {
    onAgentStart()
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

