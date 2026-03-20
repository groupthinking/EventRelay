"use strict";
/**
 * Centralized Zustand store for the EventRelay dashboard.
 *
 * Combines video processing, event extraction, and agent dispatch
 * into a single store so every component shares the same state.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.useDashboardStore = void 0;
const zustand_1 = require("zustand");
exports.useDashboardStore = (0, zustand_1.create)((set, get) => ({
    videos: [],
    activities: [],
    selectedVideoId: null,
    loading: true,
    selectedVideo: () => {
        const { videos, selectedVideoId } = get();
        return videos.find((v) => v.id === selectedVideoId);
    },
    addVideo: (video) => set((s) => ({ videos: [video, ...s.videos] })),
    updateVideo: (id, patch) => set((s) => ({
        videos: s.videos.map((v) => (v.id === id ? { ...v, ...patch } : v)),
    })),
    removeVideo: (id) => set((s) => ({
        videos: s.videos.filter((v) => v.id !== id),
        selectedVideoId: s.selectedVideoId === id ? null : s.selectedVideoId,
    })),
    selectVideo: (id) => set({ selectedVideoId: id }),
    addActivity: (event, type) => {
        const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        set((s) => ({
            activities: [{ time, event, type }, ...s.activities].slice(0, 30),
        }));
    },
    setLoading: (loading) => set({ loading }),
    // ── Process a video URL via the Next.js API route ──
    processVideo: async (url) => {
        const { addVideo, updateVideo, addActivity } = get();
        const id = Date.now().toString();
        const video = {
            id,
            title: `Analyzing: ${url.length > 50 ? url.substring(0, 47) + '…' : url}`,
            url,
            status: 'processing',
            progress: 10,
        };
        addVideo(video);
        addActivity(`Processing started: ${url.length > 40 ? url.substring(0, 37) + '…' : url}`, 'info');
        // Simulate incremental progress
        const interval = setInterval(() => {
            const current = get().videos.find((v) => v.id === id);
            if (current && current.status === 'processing') {
                updateVideo(id, { progress: Math.min(current.progress + 5, 95) });
            }
        }, 1000);
        try {
            const res = await fetch('/api/video', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url }),
            });
            clearInterval(interval);
            if (!res.ok)
                throw new Error(`API error: ${res.status}`);
            const result = await res.json();
            const rawTitle = result.result?.insights?.summary;
            const videoTitle = (typeof rawTitle === 'string' ? rawTitle : 'Video').substring(0, 50);
            let transcript = result.result?.raw_response?.transcript?.text ||
                result.result?.raw_response?.transcript ||
                undefined;
            // Flatten transcript array to string if needed
            if (Array.isArray(transcript)) {
                transcript = transcript.map((s) => s.text || '').join(' ').trim();
            }
            // STT fallback: if YouTube API returned no/empty transcript, try OpenAI
            if (!transcript || (typeof transcript === 'string' && transcript.length < 50)) {
                addActivity('YouTube transcript unavailable — trying OpenAI fallback…', 'info');
                try {
                    const sttRes = await fetch('/api/transcribe', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ url }),
                    });
                    const sttResult = await sttRes.json();
                    if (sttResult.success && sttResult.transcript) {
                        transcript = sttResult.transcript;
                        addActivity(`Transcript retrieved via ${sttResult.source} (${sttResult.wordCount} words)`, 'success');
                    }
                }
                catch {
                    addActivity('STT fallback unavailable', 'info');
                }
            }
            updateVideo(id, {
                status: result.status === 'complete' ? 'complete' : 'failed',
                progress: 100,
                title: videoTitle + (videoTitle.length >= 50 ? '…' : ''),
                processedAt: 'Just now',
                duration: `${result.result?.transcript_segments || 0} segments`,
                transcript,
                insights: {
                    summary: typeof result.result?.insights?.summary === 'string'
                        ? result.result.insights.summary
                        : 'Analysis complete',
                    actions: result.result?.insights?.actions || [],
                    sentiment: result.result?.insights?.sentiment || 'Neutral',
                    topics: result.result?.insights?.topics || [],
                },
            });
            addActivity(`Analysis complete: ${videoTitle.substring(0, 30)}`, 'success');
            // Auto-extract events + actions via AI SDK if we have a transcript
            if (transcript && typeof transcript === 'string') {
                addActivity('Extracting events & actions with AI…', 'info');
                try {
                    const extractRes = await fetch('/api/extract-events', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            transcript,
                            videoTitle,
                            videoUrl: url,
                        }),
                    });
                    const extraction = await extractRes.json();
                    if (extraction.success && extraction.data) {
                        const { events: extractedEvents, actions, summary, topics } = extraction.data;
                        updateVideo(id, {
                            events: extractedEvents?.map((e) => ({
                                id: `evt_${Math.random().toString(36).slice(2, 10)}`,
                                type: e.type,
                                title: e.title,
                                description: e.description,
                                timestamp: e.timestamp,
                                confidence: e.priority === 'high' ? 0.95 : e.priority === 'medium' ? 0.75 : 0.5,
                            })),
                            insights: {
                                summary: summary || videoTitle,
                                actions: actions?.map((a) => a.title) || [],
                                sentiment: get().videos.find(v => v.id === id)?.insights?.sentiment || 'Neutral',
                                topics: topics || [],
                            },
                        });
                        addActivity(`Extracted ${extractedEvents?.length || 0} events, ${actions?.length || 0} actions`, 'success');
                    }
                    else if (extraction.error) {
                        addActivity(`Event extraction: ${extraction.error}`, 'info');
                    }
                }
                catch (extractError) {
                    addActivity('Event extraction unavailable — set OPENAI_API_KEY', 'info');
                }
            }
            const actionCount = get().videos.find(v => v.id === id)?.insights?.actions?.length || 0;
            if (actionCount > 0) {
                addActivity(`Generated ${actionCount} action item${actionCount > 1 ? 's' : ''}`, 'success');
            }
        }
        catch (error) {
            clearInterval(interval);
            updateVideo(id, { status: 'failed', progress: 0 });
            addActivity(`Analysis failed: ${error instanceof Error ? error.message : 'Unknown error'}`, 'error');
        }
    },
    // ── Full end-to-end pipeline: YouTube URL → deployed software ──
    deployPipeline: async (url) => {
        const { addVideo, updateVideo, addActivity } = get();
        const id = Date.now().toString();
        const video = {
            id,
            title: `🚀 Deploying: ${url.length > 40 ? url.substring(0, 37) + '…' : url}`,
            url,
            status: 'processing',
            progress: 5,
        };
        addVideo(video);
        addActivity(`Pipeline started: ${url.length > 40 ? url.substring(0, 37) + '…' : url}`, 'info');
        const stages = ['Analyzing video', 'Generating code', 'Creating repo', 'Deploying'];
        let stageIdx = 0;
        const interval = setInterval(() => {
            const current = get().videos.find((v) => v.id === id);
            if (current && current.status === 'processing') {
                const newProgress = Math.min(current.progress + 3, 95);
                const newStage = Math.min(Math.floor(newProgress / 25), stages.length - 1);
                if (newStage > stageIdx) {
                    stageIdx = newStage;
                    addActivity(stages[stageIdx] + '…', 'info');
                }
                updateVideo(id, { progress: newProgress });
            }
        }, 2000);
        try {
            const res = await fetch('/api/pipeline', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url, project_type: 'web', deployment_target: 'vercel' }),
            });
            clearInterval(interval);
            if (!res.ok)
                throw new Error(`Pipeline error: ${res.status}`);
            const result = await res.json();
            const pipelineResult = {
                live_url: result.result?.live_url || null,
                github_repo: result.result?.github_repo || null,
                build_status: result.result?.build_status || 'unknown',
                code_generation: result.result?.code_generation || null,
                deployment: result.result?.deployment || null,
            };
            updateVideo(id, {
                status: result.status === 'success' || result.status === 'complete' ? 'complete' : 'failed',
                progress: 100,
                title: `Deployed: ${url.length > 40 ? url.substring(0, 37) + '…' : url}`,
                processedAt: 'Just now',
                pipelineResult,
                insights: {
                    summary: result.result?.video_analysis?.extracted_info?.title || 'Pipeline complete',
                    actions: result.result?.features_implemented || [],
                    sentiment: 'Positive',
                    topics: result.result?.code_generation?.files_created || [],
                },
            });
            if (pipelineResult.live_url) {
                addActivity(`🎉 Live at: ${pipelineResult.live_url}`, 'success');
            }
            if (pipelineResult.github_repo) {
                addActivity(`📦 Repo: ${pipelineResult.github_repo}`, 'success');
            }
            addActivity(`Pipeline complete (${result.processing_time || 'done'})`, 'success');
        }
        catch (error) {
            clearInterval(interval);
            updateVideo(id, { status: 'failed', progress: 0 });
            addActivity(`Pipeline failed: ${error instanceof Error ? error.message : 'Unknown error'}`, 'error');
        }
    },
    // ── Extract events from a completed video ──
    extractEvents: (videoId) => {
        const { videos, updateVideo, addActivity } = get();
        const video = videos.find((v) => v.id === videoId);
        if (!video)
            return;
        addActivity('Extracting events…', 'info');
        const events = [];
        // Derive events from insights
        (video.insights?.actions || []).forEach((action, i) => {
            events.push({
                id: `evt_${videoId}_${i}`,
                type: 'action',
                title: action,
                confidence: 0.85,
            });
        });
        (video.insights?.topics || []).forEach((topic, i) => {
            events.push({
                id: `evt_${videoId}_t${i}`,
                type: 'topic',
                title: topic,
                confidence: 0.9,
            });
        });
        updateVideo(videoId, { events });
        addActivity(`Extracted ${events.length} events`, 'success');
    },
    // ── Dispatch agents for extracted events ──
    dispatchAgents: (videoId) => {
        const { videos, updateVideo, addActivity } = get();
        const video = videos.find((v) => v.id === videoId);
        if (!video?.events?.length)
            return;
        addActivity('Dispatching agents…', 'info');
        const agentTypes = ['analyzer', 'content_creator'];
        const executions = video.events.slice(0, 5).flatMap((event) => agentTypes.map((agentType) => ({
            agent_id: `agent_${videoId}_${event.id}_${agentType}`,
            agent_type: agentType,
            status: 'running',
            progress: 0,
            event_id: event.id,
        })));
        updateVideo(videoId, { agents: executions });
        // Simulate agent completion
        executions.forEach((exec) => {
            setTimeout(() => {
                const currentVideo = get().videos.find((v) => v.id === videoId);
                if (!currentVideo)
                    return;
                const completed = {
                    ...exec,
                    status: 'complete',
                    progress: 100,
                    result: {
                        summary: `Processed by ${exec.agent_type}`,
                        output: `Analysis complete for event ${exec.event_id}`,
                    },
                };
                updateVideo(videoId, {
                    agents: (currentVideo.agents || []).map((a) => a.agent_id === exec.agent_id ? completed : a),
                });
            }, 1500 + Math.random() * 3000);
        });
        addActivity(`Dispatched ${executions.length} agents`, 'success');
    },
}));
//# sourceMappingURL=dashboard-store.js.map