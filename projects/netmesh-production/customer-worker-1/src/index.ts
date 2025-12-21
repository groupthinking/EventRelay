
import { WorkerEntrypoint } from 'cloudflare:workers';

export interface Env {
    OPENAI_API_KEY: string;
    CLOUDFLARE_ACCOUNT_ID: string;
    CLOUDFLARE_GATEWAY_ID: string;
}

export default {
    async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
        const url = new URL(request.url);

        if (url.pathname === '/session') {
            if (request.method !== 'POST') return new Response('Method not allowed', { status: 405 });

            if (!env.OPENAI_API_KEY) {
                return new Response('Missing OPENAI_API_KEY', { status: 500 });
            }

            // Use Cloudflare AI Gateway URL construction
            const gatewayUrl = `https://gateway.ai.cloudflare.com/v1/${env.CLOUDFLARE_ACCOUNT_ID}/${env.CLOUDFLARE_GATEWAY_ID}/openai/realtime/sessions`;

            const response = await fetch(gatewayUrl, {
                method: "POST",
                headers: {
                    "Authorization": `Bearer ${env.OPENAI_API_KEY}`,
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    model: "gpt-4o-realtime-preview-2024-12-17",
                    voice: "verse",
                }),
            });

            return new Response(response.body, {
                headers: {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*", // Allow all for demo
                },
            });
        }

        // Serve the HTML UI
        return new Response(MAIN_HTML, {
            headers: { "Content-Type": "text/html" },
        });
    },
};

const MAIN_HTML = `
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Netmesh Vision Agent</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body { background-color: #0f0f11; color: white; font-family: 'Inter', sans-serif; }
        .glass { background: rgba(255, 255, 255, 0.05); backdrop-filter: blur(10px); border: 1px solid rgba(255, 255, 255, 0.1); }
				.glow { box-shadow: 0 0 20px rgba(0, 146, 184, 0.3); }
        video { transform: scaleX(-1); } 
    </style>
</head>
<body class="h-screen flex flex-col items-center justify-center relative overflow-hidden">
    
    <!-- Background Gradient -->
    <div class="absolute top-0 left-0 w-full h-full z-0 opacity-20 bg-[radial-gradient(circle_at_center,_var(--tw-gradient-stops))] from-blue-900 via-gray-900 to-black"></div>

    <div class="z-10 w-full max-w-4xl p-6 flex flex-col items-center gap-6">
        
        <!-- Header -->
        <h1 class="text-3xl md:text-5xl font-bold tracking-tighter text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-purple-400 mb-4">
            Vision Agent
        </h1>

        <!-- Video Container -->
        <div class="relative w-full aspect-video max-h-[60vh] rounded-2xl overflow-hidden glass glow shadow-2xl">
            <video id="localVideo" autoplay playsinline muted class="w-full h-full object-cover"></video>
            <audio id="remoteAudio" autoplay></audio>
            
            <!-- Overlay Interface -->
            <div class="absolute bottom-6 left-6 right-6 flex justify-between items-center">
                 <div class="flex items-center gap-3">
                    <div id="statusIndicator" class="w-3 h-3 rounded-full bg-red-500 transition-colors"></div>
                    <span id="statusText" class="text-sm font-medium text-gray-300">Disconnected</span>
                 </div>

                 <div class="flex gap-4">
                     <button id="startButton" class="px-6 py-3 rounded-full bg-white text-black font-semibold hover:bg-gray-200 transition-all flex items-center gap-2">
                        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"></path></svg>
                        Start Session
                     </button>
                     <button id="stopButton" class="hidden px-6 py-3 rounded-full bg-red-500/20 text-red-500 border border-red-500/50 hover:bg-red-500/30 transition-all">
                        End
                     </button>
                 </div>
            </div>
        </div>

        <!-- Debug/Log Area (Hidden mostly) -->
        <div id="logs" class="w-full h-32 glass rounded-xl p-4 overflow-y-auto text-xs font-mono text-gray-400 hidden"></div>
    </div>

    <script>
        const localVideo = document.getElementById('localVideo');
        const remoteAudio = document.getElementById('remoteAudio');
        const startButton = document.getElementById('startButton');
        const stopButton = document.getElementById('stopButton');
        const statusInd = document.getElementById('statusIndicator');
        const statusText = document.getElementById('statusText');

        let peerConnection;
        let localStream;
        let dataChannel;

        async function init() {
            try {
                // Get User Media
                localStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
                localVideo.srcObject = localStream;
                localVideo.play();
                log("Camera ready.");
            } catch (e) {
                log("Error accessing camera: " + e.message);
                statusText.innerText = "Camera Error";
            }
        }

        async function startSession() {
            startButton.classList.add('hidden');
            stopButton.classList.remove('hidden');
            statusInd.className = "w-3 h-3 rounded-full bg-yellow-500 animate-pulse";
            statusText.innerText = "Connecting...";

            try {
                // 1. Get Token
                const tokenResponse = await fetch('/session', { method: 'POST' });
								if (!tokenResponse.ok) throw new Error(\`Token Error: \${tokenResponse.status}\`);
                const data = await tokenResponse.json();
                const EPHEMERAL_KEY = data.client_secret.value;

                // 2. Create PC
                peerConnection = new RTCPeerConnection();

                // 3. Set up Audio/Video to send
                peerConnection.ontrack = e => {
                    log("Got remote track: " + e.track.kind);
                    if (e.track.kind === 'audio') remoteAudio.srcObject = e.streams[0];
                };

                // Add local tracks
                localStream.getTracks().forEach(track => peerConnection.addTrack(track, localStream));

                // 4. Data Channel
                dataChannel = peerConnection.createDataChannel("oai-events");
                dataChannel.onopen = () => {
                    log("Data Channel Open");
                    // Configure session
                    const event = {
                        type: "session.update",
                        session: {
                            modalities: ["text", "audio"],
                            instructions: "You are a helpful Vision Agent. You can see the user. Be concise and friendly."
                        }
                    };
                    dataChannel.send(JSON.stringify(event));
                };
                
                // 5. Offer/Answer
                const offer = await peerConnection.createOffer();
                await peerConnection.setLocalDescription(offer);

                const baseUrl = "https://api.openai.com/v1/realtime";
                const model = "gpt-4o-realtime-preview-2024-12-17";
                const sdpResponse = await fetch(\`\${baseUrl}?model=\${model}\`, {
                    method: "POST",
                    body: offer.sdp,
                    headers: {
                        Authorization: \`Bearer \${EPHEMERAL_KEY}\`,
                        "Content-Type": "application/sdp"
                    },
                });

                const answer = {
                    type: "answer",
                    sdp: await sdpResponse.text(),
                };

                await peerConnection.setRemoteDescription(answer);
                
                statusInd.className = "w-3 h-3 rounded-full bg-green-500";
                statusText.innerText = "Connected (Vision Active)";
                log("Connected to OpenAI Realtime");

            } catch (err) {
                console.error(err);
                log("Connection Failed: " + err.message);
                resetUI();
            }
        }

        function stopSession() {
            if (peerConnection) peerConnection.close();
            resetUI();
        }

        function resetUI() {
            startButton.classList.remove('hidden');
            stopButton.classList.add('hidden');
            statusInd.className = "w-3 h-3 rounded-full bg-red-500";
            statusText.innerText = "Disconnected";
        }

        function log(msg) {
            const logs = document.getElementById('logs');
            logs.innerHTML += \`<div>\${msg}</div>\`;
            console.log(msg);
        }

        startButton.onclick = startSession;
        stopButton.onclick = stopSession;

        // Auto-init camera
        init();

    </script>
</body>
</html>
