import axios from 'axios';
import fs from 'fs';
import path from 'path';
import cron from 'node-cron';
import 'dotenv/config';

/**
 * Lead AI Engineer - Content OPS Autonomous Loop (auto_loop.js)
 * Mission: Scrape, Scout, Script, and Studio - 24/7 Cycle.
 */

const OLLAMA_BASE_URL = process.env.OLLAMA_BASE_URL || 'http://localhost:11434';
const API_BASE_URL = 'http://localhost:8100'; // FastAPI Backend
const LOOP_INTERVAL = 4 * 60 * 60 * 1000; // 4 Hours

// MCP Server URLs
const XPOZ_URL = process.env.XPOZ_MCP_URL || 'http://localhost:8200';

async function log(message, level = 'INFO') {
    const timestamp = new Date().toISOString();
    console.log(`[${timestamp}] [${level}] ${message}`);
}

/**
 * Utility: Force Ollama to unload model from VRAM
 */
async function unloadOllama(modelName) {
    log(`Explicitly unloading ${modelName} from VRAM...`);
    try {
        await axios.post(`${OLLAMA_BASE_URL}/api/generate`, {
            model: modelName,
            keep_alive: 0
        });
        log('VRAM Cleared successfully.');
    } catch (error) {
        log(`Failed to unload model: ${error.message}`, 'WARNING');
    }
}

/**
 * Discovery Phase: Scrape trends via Xpoz MCP
 */
async function fetchTrendingTopics() {
    log('Pulling trending Web3/Tech topics via Xpoz MCP...');
    try {
        // Mocking the tool call structure requested in Phase 1
        const response = await axios.post(`${XPOZ_URL}/tools/call`, {
            name: 'get_trending_topics',
            arguments: {
                categories: ['web3', 'tech', 'ai', 'crypto'],
                region: 'global'
            }
        });

        if (response.data.error) throw new Error(response.data.error);

        // Return raw topics for Ollama to process
        return response.data.topics || ['Latest AI advancements in 2026', 'Web3 decentralization trends'];
    } catch (error) {
        log(`MCP Fetch failed, using fallback trends: ${error.message}`, 'WARNING');
        return [
            "Decentralized AI Agents on Solana",
            "Multi-modal LLMs for video production",
            "New LTX-2 distillation breakthroughs"
        ];
    }
}

/**
 * Director Phase: Ollama Scriptwriting (Strict JSON)
 */
async function generateAIPack(topic) {
    const model = process.env.OLLAMA_FAST_MODEL || 'qwen2.5:7b-instruct';
    log(`Generating AI Content Pack for topic: "${topic}" using ${model}...`);

    const prompt = `
    You are a Viral Content Director. Build a high-retention video script for a 60-second social media reel.
    Topic: ${topic}

    OUTPUT MUST BE A STRICT JSON SCHEMA:
    {
        "video_script": "The structured script with scene headers",
        "voiceover_text": "The exact words to be read by the AI voice",
        "5_visual_prompts": [
            "Detailed visual cue for Scene 1",
            "Detailed visual cue for Scene 2",
            "Detailed visual cue for Scene 3",
            "Detailed visual cue for Scene 4",
            "Detailed visual cue for Scene 5"
        ],
        "social_caption": "Viral caption with hashtags"
    }
    
    ONLY OUTPUT THE JSON BLOCK. NO INTRO. NO OUTRO.
    `;

    try {
        const response = await axios.post(`${OLLAMA_BASE_URL}/api/generate`, {
            model: model,
            prompt: prompt,
            stream: false,
            format: 'json'
        });

        const result = JSON.parse(response.data.response);

        // CRITICAL: Unload model immediately after generation
        await unloadOllama(model);

        return result;
    } catch (error) {
        log(`Ollama generation failed: ${error.message}`, 'ERROR');
        return null;
    }
}

/**
 * Injection Phase: Send to FastAPI Generation Queue
 */
async function triggerVideoGeneration(contentPack, nicheId = 1) {
    log('Injecting AI pack into the Studio Production pipeline...');
    try {
        const payload = {
            niche_id: nicheId,
            topic: contentPack.social_caption.split('#')[0].trim(),
            custom_script: contentPack.voiceover_text,
            visual_cues: JSON.stringify(contentPack['5_visual_prompts']),
            topic_source: 'autonomous_loop'
        };

        const res = await axios.post(`${API_BASE_URL}/api/generator/video`, payload);
        log(`Job #${res.data.job_id} successfully queued for Rendering.`);
    } catch (error) {
        log(`Failed to queue job: ${error.message}`, 'ERROR');
    }
}


/**
 * THE 24/7 LOOP
 */
async function autonomousCycle() {
    log('Checking Cloud/Local status for Auto-Pilot...');
    try {
        // Fetch current settings from backend
        const settingsRes = await axios.get(`${API_BASE_URL}/api/settings/`);
        const isAutopilot = settingsRes.data.autopilot_enabled;

        if (!isAutopilot) {
            log('Auto-Pilot is currently DISABLED. Skipping cycle.', 'DEBUG');
            return;
        }

        log('=== STARTING AUTONOMOUS SEARCH-AND-SCRIPT CYCLE ===');

        // 1. Scrape Trends
        const trends = await fetchTrendingTopics();
        const topTopic = trends[0] || 'Web3 Revolution';

        // 2. Scripting Pack
        const aiPack = await generateAIPack(topTopic);

        if (aiPack) {
            // 3. Queue Studio Generation
            await triggerVideoGeneration(aiPack);
            log('AI Content Pack successfully sent to Studio pipeline.');
        }

        log('=== CYCLE COMPLETE. SLEEPING ===');
    } catch (error) {
        log(`Cycle error: ${error.message}`, 'ERROR');
    }
}

// Initial Run
autonomousCycle();

// Schedule: Every 4 hours (0 */4 * * *)
log('Autonomous Worker initialized. Cycle scheduled for every 4 hours.');
cron.schedule('0 */4 * * *', () => {
    autonomousCycle();
});
