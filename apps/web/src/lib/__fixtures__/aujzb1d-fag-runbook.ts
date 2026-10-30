import type { VideoPackV0Json } from "@/lib/video-pack";

/**
 * Saved Video Pack for the repository test video auJzb1D-fag.
 * Captured from the live /api/video/pack response on 2026-10-28.
 * This source-bound sample is not a synthetic re-labeling of another video.
 */
export const RUNBOOK_VIDEO_ID = "auJzb1D-fag";
export const RUNBOOK_SOURCE_HASH = "2778c5fc08a1b7f19fe0a83bca959e24ecf20040c3cc1a3b6edd244d68c5e4ea";

const SAVED_PACK = {
  "version": "v0",
  "id": "vp:v0:auJzb1D-fag",
  "video_id": "auJzb1D-fag",
  "source_url": "https://www.youtube.com/watch?v=auJzb1D-fag",
  "transcript": {
    "language": "en",
    "full_text": "The way we interact with AI is changing. Text was only the beginning. Welcome to the multimodal era, where AI understands the world through images, videos, and continuous streams of information. In this video, we'll explore the multimodal capabilities of Google AI Studio, like generating rich content from diverse inputs, understanding vast amounts of information, and even reacting in real time. So, let's get started with long context. Google AI Studio and Gemini excels in this area. Long context refers to a model's ability to process and understand a very large amount of information within a single prompt or conversation. An AI model's context window is sort of like its short-term memory. It's measured in tokens, which are roughly words or parts of words. This window determines how much information the model can consider at once when generating a response. Now historically, the amount of tokens a large language model could handle was limited. But new Gemini models come with larger context windows and can handle 1 million or even 2 million tokens. To put that into perspective, 1 million tokens equals approximately 50,000 lines of code, all the text messages you have sent in the last 5 years, 8 average length English novels, or transcripts of over 200 average length podcast episodes. So it goes without saying that these models can handle a lot. Not long ago, long context video capabilities were relatively limited due to the lack of accessibility of the medium itself. Now with new Gemini models, long context text capabilities translate to the ability to reason and answer questions about multimodal inputs with sustained performance. Some emerging and standard use cases for video long context include: question and answer, memory, meaning the ability of a model to retain and recall information, captions, recommendation systems by enriching existing metadata with new multimodal understanding, customization by analyzing content and then removing parts that are not relevant to the viewer, content moderation, and real-time processing. Now if you've used Gemini before, you might know that it has several different talents. This includes both images and videos. Imagen is fantastic for generating photorealistic and artistic images. And Gemini Flash experiments can mix images right into text responses. The usual prompt advice applies: be descriptive. And here's how to level up: Paint the picture. Don't just say dog, say a fluffy golden retriever puppy sitting in a field of daisies, soft morning light, shallow depth of field. Think subject, setting, style, and even camera details. Need text? Imagen can add text to images. Keep it short and sweet like a coffee cup with the text Good Morning! written neatly. Exclude stuff. Use negative prompts to tell it what not to include, negativePrompt: blurry, low quality. Google AI Studio can also generate video clips. And this is where things get really exciting. Veo is Google's powerful video generator. You can type a description and get a short video clip, or even bring a still image to life. Whether you're generating from text or from images, be a director. Describe the scene: who or what is in it, what they're doing, the camera movement, and the vibe, like a cinematic moody lighting. Before jumping into a demo, let's explore one more amazing capability of Google AI Studio: real-time streaming. This is where things go from 'Wow, that's cool' to 'Whoa, is this the future?'. You can even point your camera or even stream your screen directly into Google AI Studio, and the model understands and responds as it happens. It's not just analyzing the past, it's reacting to the present. It's like, instead of showing your friend a recording of you building that next level LEGO castle, you could ask, 'Hey Gemini, what piece should I look for next?' while you're still building, and Gemini comes back with an answer: 'Look for six 2x4 gray bricks. Let me know when you find and place them, and I'll help you with the next step.' This isn't just about feeding the AI information anymore. It's about having a dynamic conversation with it using live video and audio. It turns Google AI Studio from just an analysis tool into a potential real-time collaborator or an instant feedback machine. This streaming capability changes the game for how we interact with AI. Okay, so enough talk about these amazing capabilities. So here we are in Google AI Studio, and we are going to add a relatively long video, and then prompt the model to perform a few specific tasks. So let's click the plus icon in the chat prompt interface, and this is coming from YouTube. So let's click that YouTube video, paste the video URL here, and click Save. Now let's design our prompt and keep it simple for now, and ask the model to provide a detailed summary, including main points, supporting evidence, and any conclusions. And let's run this. Okay, and let's be patient. It does have to watch through a 22-minute video. And now we have some results. Okay wow, just as instructed, the model provided a detailed summary, very detailed, with main points, evidence, and some conclusions. This output is structured very nicely as well. And the model essentially watched the 22-minute video in about a minute. Okay, so let's switch gears and check out another capability. And this will be a nice segue into the next video in this course, where you will learn to prototype your own app. So let's click the Build tab, and this will pull up an interface with demo apps. More on this in the next video, so stay tuned. But for now, we're going to show some of the spatial understanding and object detection capabilities of Google AI Studio. Gemini models have a strong understanding of objects and their visual representations. So this is essentially a prototype of an app that can detect objects in an image. In this simple example, the prompt is asking for the position of the items in the image and for the model to add 2D bounding boxes around them. When we send this to the model, we can see that it's added 2D bounding boxes and labeled what each item is. And if we click the code icon, we can see the behind the scenes code for what's actually making this work. And this is something you can use in your own applications to leverage the power of Gemini models. In the next video, we'll continue this discussion and dive deeper into the world of app prototyping with Google AI Studio. This is where things get really exciting, so we'll see you there.",
    "segments": [
      {
        "idx": 0,
        "start_s": 0,
        "end_s": 7,
        "text": "The way we interact with AI is changing. Text was only the beginning. Welcome to the multimodal era,"
      },
      {
        "idx": 1,
        "start_s": 7,
        "end_s": 14,
        "text": "where AI understands the world through images, videos, and continuous streams of information."
      },
      {
        "idx": 2,
        "start_s": 14,
        "end_s": 27,
        "text": "In this video, we'll explore the multimodal capabilities of Google AI Studio, like generating rich content from diverse inputs, understanding vast amounts of information, and even reacting in real time."
      },
      {
        "idx": 3,
        "start_s": 27,
        "end_s": 34,
        "text": "So, let's get started with long context. Google AI Studio and Gemini excels in this area."
      },
      {
        "idx": 4,
        "start_s": 34,
        "end_s": 45,
        "text": "Long context refers to a model's ability to process and understand a very large amount of information within a single prompt or conversation."
      },
      {
        "idx": 5,
        "start_s": 45,
        "end_s": 54,
        "text": "An AI model's context window is sort of like its short-term memory. It's measured in tokens, which are roughly words or parts of words."
      },
      {
        "idx": 6,
        "start_s": 54,
        "end_s": 62,
        "text": "This window determines how much information the model can consider at once when generating a response."
      },
      {
        "idx": 7,
        "start_s": 62,
        "end_s": 75,
        "text": "Now historically, the amount of tokens a large language model could handle was limited. But new Gemini models come with larger context windows and can handle 1 million or even 2 million tokens."
      },
      {
        "idx": 8,
        "start_s": 75,
        "end_s": 97,
        "text": "To put that into perspective, 1 million tokens equals approximately 50,000 lines of code, all the text messages you have sent in the last 5 years, 8 average length English novels, or transcripts of over 200 average length podcast episodes."
      },
      {
        "idx": 9,
        "start_s": 97,
        "end_s": 102,
        "text": "So it goes without saying that these models can handle a lot."
      },
      {
        "idx": 10,
        "start_s": 102,
        "end_s": 116,
        "text": "Not long ago, long context video capabilities were relatively limited due to the lack of accessibility of the medium itself."
      },
      {
        "idx": 11,
        "start_s": 116,
        "end_s": 128,
        "text": "Now with new Gemini models, long context text capabilities translate to the ability to reason and answer questions about multimodal inputs with sustained performance."
      },
      {
        "idx": 12,
        "start_s": 128,
        "end_s": 148,
        "text": "Some emerging and standard use cases for video long context include: question and answer, memory, meaning the ability of a model to retain and recall information, captions,"
      },
      {
        "idx": 13,
        "start_s": 148,
        "end_s": 167,
        "text": "recommendation systems by enriching existing metadata with new multimodal understanding, customization by analyzing content and then removing parts that are not relevant to the viewer, content moderation, and real-time processing."
      },
      {
        "idx": 14,
        "start_s": 167,
        "end_s": 178,
        "text": "Now if you've used Gemini before, you might know that it has several different talents. This includes both images and videos."
      },
      {
        "idx": 15,
        "start_s": 178,
        "end_s": 187,
        "text": "Imagen is fantastic for generating photorealistic and artistic images. And Gemini Flash experiments can mix images right into text responses."
      },
      {
        "idx": 16,
        "start_s": 187,
        "end_s": 192,
        "text": "The usual prompt advice applies: be descriptive. And here's how to level up:"
      },
      {
        "idx": 17,
        "start_s": 192,
        "end_s": 208,
        "text": "Paint the picture. Don't just say dog, say a fluffy golden retriever puppy sitting in a field of daisies, soft morning light, shallow depth of field. Think subject, setting, style, and even camera details."
      },
      {
        "idx": 18,
        "start_s": 208,
        "end_s": 220,
        "text": "Need text? Imagen can add text to images. Keep it short and sweet like a coffee cup with the text Good Morning! written neatly."
      },
      {
        "idx": 19,
        "start_s": 220,
        "end_s": 228,
        "text": "Exclude stuff. Use negative prompts to tell it what not to include, negativePrompt: blurry, low quality."
      },
      {
        "idx": 20,
        "start_s": 228,
        "end_s": 239,
        "text": "Google AI Studio can also generate video clips. And this is where things get really exciting. Veo is Google's powerful video generator."
      },
      {
        "idx": 21,
        "start_s": 239,
        "end_s": 252,
        "text": "You can type a description and get a short video clip, or even bring a still image to life. Whether you're generating from text or from images, be a director."
      },
      {
        "idx": 22,
        "start_s": 252,
        "end_s": 260,
        "text": "Describe the scene: who or what is in it, what they're doing, the camera movement, and the vibe, like a cinematic moody lighting."
      },
      {
        "idx": 23,
        "start_s": 260,
        "end_s": 272,
        "text": "Before jumping into a demo, let's explore one more amazing capability of Google AI Studio: real-time streaming. This is where things go from 'Wow, that's cool' to 'Whoa, is this the future?'."
      },
      {
        "idx": 24,
        "start_s": 272,
        "end_s": 287,
        "text": "You can even point your camera or even stream your screen directly into Google AI Studio, and the model understands and responds as it happens. It's not just analyzing the past, it's reacting to the present."
      },
      {
        "idx": 25,
        "start_s": 287,
        "end_s": 300,
        "text": "It's like, instead of showing your friend a recording of you building that next level LEGO castle, you could ask, 'Hey Gemini, what piece should I look for next?' while you're still building, and Gemini comes back with an answer:"
      },
      {
        "idx": 26,
        "start_s": 300,
        "end_s": 311,
        "text": "'Look for six 2x4 gray bricks. Let me know when you find and place them, and I'll help you with the next step.'"
      },
      {
        "idx": 27,
        "start_s": 311,
        "end_s": 328,
        "text": "This isn't just about feeding the AI information anymore. It's about having a dynamic conversation with it using live video and audio. It turns Google AI Studio from just an analysis tool into a potential real-time collaborator or an instant feedback machine."
      },
      {
        "idx": 28,
        "start_s": 328,
        "end_s": 332,
        "text": "This streaming capability changes the game for how we interact with AI."
      },
      {
        "idx": 29,
        "start_s": 332,
        "end_s": 344,
        "text": "Okay, so enough talk about these amazing capabilities. So here we are in Google AI Studio, and we are going to add a relatively long video, and then prompt the model to perform a few specific tasks."
      },
      {
        "idx": 30,
        "start_s": 344,
        "end_s": 353,
        "text": "So let's click the plus icon in the chat prompt interface, and this is coming from YouTube. So let's click that YouTube video, paste the video URL here, and click Save."
      },
      {
        "idx": 31,
        "start_s": 353,
        "end_s": 366,
        "text": "Now let's design our prompt and keep it simple for now, and ask the model to provide a detailed summary, including main points, supporting evidence, and any conclusions."
      },
      {
        "idx": 32,
        "start_s": 366,
        "end_s": 379,
        "text": "And let's run this. Okay, and let's be patient. It does have to watch through a 22-minute video. And now we have some results."
      },
      {
        "idx": 33,
        "start_s": 379,
        "end_s": 395,
        "text": "Okay wow, just as instructed, the model provided a detailed summary, very detailed, with main points, evidence, and some conclusions. This output is structured very nicely as well. And the model essentially watched the 22-minute video in about a minute."
      },
      {
        "idx": 34,
        "start_s": 395,
        "end_s": 406,
        "text": "Okay, so let's switch gears and check out another capability. And this will be a nice segue into the next video in this course, where you will learn to prototype your own app."
      },
      {
        "idx": 35,
        "start_s": 406,
        "end_s": 414,
        "text": "So let's click the Build tab, and this will pull up an interface with demo apps. More on this in the next video, so stay tuned."
      },
      {
        "idx": 36,
        "start_s": 414,
        "end_s": 427,
        "text": "But for now, we're going to show some of the spatial understanding and object detection capabilities of Google AI Studio. Gemini models have a strong understanding of objects and their visual representations."
      },
      {
        "idx": 37,
        "start_s": 427,
        "end_s": 438,
        "text": "So this is essentially a prototype of an app that can detect objects in an image. In this simple example, the prompt is asking for the position of the items in the image and for the model to add 2D bounding boxes around them."
      },
      {
        "idx": 38,
        "start_s": 438,
        "end_s": 454,
        "text": "When we send this to the model, we can see that it's added 2D bounding boxes and labeled what each item is. And if we click the code icon, we can see the behind the scenes code for what's actually making this work."
      },
      {
        "idx": 39,
        "start_s": 454,
        "end_s": 460,
        "text": "And this is something you can use in your own applications to leverage the power of Gemini models."
      },
      {
        "idx": 40,
        "start_s": 460,
        "end_s": 477,
        "text": "In the next video, we'll continue this discussion and dive deeper into the world of app prototyping with Google AI Studio. This is where things get really exciting, so we'll see you there."
      }
    ]
  },
  "keyframes": [
    {
      "t_s": 14,
      "image_path": "/api/video/pack/frames/auJzb1D-fag/14",
      "desc": "Title card displaying 'Google Cloud - Google AI Studio: multimodal capabilities' with abstract shapes."
    },
    {
      "t_s": 35,
      "image_path": "/api/video/pack/frames/auJzb1D-fag/35",
      "desc": "Graphic explaining context window as short-term memory measured in tokens."
    },
    {
      "t_s": 85,
      "image_path": "/api/video/pack/frames/auJzb1D-fag/85",
      "desc": "Comparison cards illustrating 1 million tokens equivalent to 50,000 lines of code, 5 years of texts, 8 English novels, or 200 podcast transcripts."
    },
    {
      "t_s": 178,
      "image_path": "/api/video/pack/frames/auJzb1D-fag/178",
      "desc": "Labels for Imagen and Gemini Flash showing image generation and interleaved multimodal responses."
    },
    {
      "t_s": 235,
      "image_path": "/api/video/pack/frames/auJzb1D-fag/235",
      "desc": "Speaker discussing Veo video generation model from text or images."
    },
    {
      "t_s": 272,
      "image_path": "/api/video/pack/frames/auJzb1D-fag/272",
      "desc": "Animated mock screen showing live streaming interaction with Gemini assisting a LEGO building task."
    },
    {
      "t_s": 312,
      "image_path": "/api/video/pack/frames/auJzb1D-fag/312",
      "desc": "Google AI Studio welcome interface showing Chat Prompt, model run settings (Gemini 2.5 Pro Preview), and token count."
    },
    {
      "t_s": 334,
      "image_path": "/api/video/pack/frames/auJzb1D-fag/334",
      "desc": "Adding a YouTube video URL into Google AI Studio chat prompt interface."
    },
    {
      "t_s": 360,
      "image_path": "/api/video/pack/frames/auJzb1D-fag/360",
      "desc": "Running prompt 'Provide a detailed summary including main points, supporting evidence, and any conclusions' with 415,928 tokens ingested."
    },
    {
      "t_s": 400,
      "image_path": "/api/video/pack/frames/auJzb1D-fag/400",
      "desc": "Detailed structured summary output generated by Gemini 2.5 Pro Preview."
    },
    {
      "t_s": 435,
      "image_path": "/api/video/pack/frames/auJzb1D-fag/435",
      "desc": "Google AI Studio Build tab showcasing template apps including 'Spatial Understanding'."
    },
    {
      "t_s": 455,
      "image_path": "/api/video/pack/frames/auJzb1D-fag/455",
      "desc": "Spatial Understanding demo app detecting items with 2D bounding boxes and displaying React/TypeScript source code."
    }
  ],
  "concepts": [
    "Multimodality",
    "Long context window",
    "Token capacity (1M - 2M tokens)",
    "Video comprehension",
    "Imagen text-to-image generation",
    "Negative prompting",
    "Veo video generation",
    "Real-time streaming multimodal dialog",
    "YouTube video ingestion in Google AI Studio",
    "Spatial understanding and 2D bounding boxes",
    "App prototyping from prompt in Google AI Studio"
  ],
  "requirements": [
    {
      "id": "REQ-01",
      "title": "Long Context Video Ingestion",
      "detail": "Ability to ingest long multimedia inputs such as 22-minute YouTube videos (~415k tokens) into Gemini context window.",
      "priority": "P0",
      "tags": [
        "context-window",
        "multimodal",
        "video"
      ]
    },
    {
      "id": "REQ-02",
      "title": "Video Summarization & Analysis",
      "detail": "Generate detailed, timestamped section summaries with key features, limitations, and calls to action from ingested video.",
      "priority": "P0",
      "tags": [
        "video-analysis",
        "summarization"
      ]
    },
    {
      "id": "REQ-03",
      "title": "Image & Video Generation Prompting",
      "detail": "Support descriptive prompting, text overlay instructions, and negativePrompt exclusions for Imagen and Veo.",
      "priority": "P1",
      "tags": [
        "imagen",
        "veo",
        "prompting"
      ]
    },
    {
      "id": "REQ-04",
      "title": "Real-time Streaming Interaction",
      "detail": "Provide bidirectional live audio/video streaming for conversational assistance.",
      "priority": "P1",
      "tags": [
        "streaming",
        "live-audio",
        "live-video"
      ]
    },
    {
      "id": "REQ-05",
      "title": "Spatial Understanding & Bounding Boxes",
      "detail": "Detect visual elements in images and return labeled 2D/3D bounding boxes and segmentation masks.",
      "priority": "P1",
      "tags": [
        "spatial-understanding",
        "object-detection"
      ]
    }
  ],
  "code_snippets": [
    {
      "path_hint": "google-ai-studio/spatial-understanding/app.tsx",
      "lang": "typescript",
      "content": "export function Content() {\n  const [boxes, setBoxes] = useState<BoundingBox[]>([]);\n  const handleDetect = async (image: ImageSource, mode: '2d_boxes' | 'segmentation' | 'points') => {\n    // Gemini 2.0 Flash / Pro spatial detection\n  };\n}"
    }
  ],
  "architecture": {
    "summary": "Multimodal ingestion and processing pipeline in Google AI Studio, supporting text, image, long-form video URL/file ingestion, real-time audio/video streaming, and structured output extraction (summaries, bounding boxes, code).",
    "stages": [
      {
        "id": "ingest",
        "name": "Multimodal Ingestion",
        "description": "Ingest YouTube video URL, user prompt, images, or real-time camera/mic stream."
      },
      {
        "id": "tokenize",
        "name": "Long-Context Tokenization",
        "description": "Encode video frames and audio tracks into unified token representations (e.g. 415k+ tokens)."
      },
      {
        "id": "inference",
        "name": "Gemini Multimodal Reasoning",
        "description": "Process temporal context with Gemini 2.5 Pro Preview / Flash models to reason, summarize, or extract spatial coordinates."
      },
      {
        "id": "output",
        "name": "Structured Generation & Prototype Code",
        "description": "Render markdown summary, 2D bounding boxes on canvas, and exportable React code."
      }
    ],
    "mermaid": "graph TD\n  A[User / Client] -->|YouTube URL / Video| B[Google AI Studio Chat Prompt]\n  A -->|Webcam / Screen Stream| C[Live Multimodal Streaming Session]\n  B --> D[Gemini Long Context Engine - up to 2M Tokens]\n  C --> D\n  D --> E[Video Structured Summary]\n  D --> F[Imagen / Veo Generators]\n  D --> G[Spatial Understanding Prototype App]\n  G --> H[Render 2D Bounding Boxes & Export Code]"
  },
  "artifacts": [
    {
      "path_hint": "src/components/SpatialDetector.tsx",
      "purpose": "Render user image and overlaid 2D bounding boxes with object labels returned from Gemini model.",
      "interface": "interface SpatialDetectorProps { imageUrl: string; prompt: string; onBoxSelect?: (box: BoundingBox) => void; }",
      "signatures": [
        "function SpatialDetector(props: SpatialDetectorProps): JSX.Element"
      ],
      "stubs": [
        "export const SpatialDetector = ({ imageUrl, prompt }: SpatialDetectorProps) => { return <div className='detector-container'><img src={imageUrl} alt='Target' /></div>; };"
      ]
    }
  ],
  "stack": {
    "tools": [
      {
        "name": "Google AI Studio",
        "kind": "web-ide",
        "evidence": "Visible throughout video UI (header 'Google AI Studio', chat prompt, build tab)",
        "check": "Navigate to Google AI Studio web application"
      },
      {
        "name": "Gemini 2.5 Pro Preview",
        "kind": "llm",
        "evidence": "Selected in Run settings sidebar at 05:12 and 05:38",
        "check": "Verify model selector dropdown in Run settings"
      },
      {
        "name": "Gemini Flash / Gemini 2.0 Flash",
        "kind": "llm",
        "evidence": "Mentioned at 02:42 and shown in Build tab app cards",
        "check": "Check model options for low-latency multimodal reasoning"
      },
      {
        "name": "Imagen",
        "kind": "image-generator",
        "evidence": "Spoken and visual callout at 02:37 for photorealistic image generation",
        "check": "Inspect Imagen prompt modal"
      },
      {
        "name": "Veo",
        "kind": "video-generator",
        "evidence": "Spoken and visual callout at 03:35 as Google's video generator",
        "check": "Inspect Veo video generation prompt feature"
      }
    ]
  },
  "chapters": [
    {
      "start": 0,
      "end": 27,
      "topic": "Welcome to the Multimodal Era",
      "key_points": [
        "Evolution of AI beyond text to images, video, and continuous streams",
        "Overview of Google AI Studio capabilities covered in the video"
      ]
    },
    {
      "start": 27,
      "end": 102,
      "topic": "Long Context Windows (1M - 2M Tokens)",
      "key_points": [
        "Definition of context window as short-term memory",
        "Gemini supports 1 million to 2 million tokens",
        "1M tokens equals ~50k lines of code, 5 years of texts, or 8 novels"
      ]
    },
    {
      "start": 102,
      "end": 167,
      "topic": "Multimodal & Video Long Context Use Cases",
      "key_points": [
        "Question and answer, temporal memory, automated captions",
        "Recommendation metadata, content customization, and moderation"
      ]
    },
    {
      "start": 167,
      "end": 228,
      "topic": "Image Generation with Imagen & Gemini Flash",
      "key_points": [
        "Imagen creates photorealistic and artistic images",
        "Prompting tips: subject, setting, style, camera details",
        "Text rendering on images and negativePrompt exclusions"
      ]
    },
    {
      "start": 228,
      "end": 260,
      "topic": "Video Generation with Veo",
      "key_points": [
        "Veo generates short clips from text descriptions or still images",
        "Directing the scene: actions, camera movement, and moody lighting"
      ]
    },
    {
      "start": 260,
      "end": 332,
      "topic": "Real-time Live Streaming Interaction",
      "key_points": [
        "Streaming webcam or screen directly into AI Studio",
        "Dynamic real-time problem solving (e.g., LEGO castle assistant)"
      ]
    },
    {
      "start": 332,
      "end": 395,
      "topic": "Demo: Ingesting & Summarizing YouTube Video",
      "key_points": [
        "Adding YouTube URL to Chat Prompt interface (415k tokens)",
        "Prompting Gemini 2.5 Pro Preview for main points, evidence, and conclusions",
        "Analyzing 22-minute video in approximately one minute"
      ]
    },
    {
      "start": 395,
      "end": 460,
      "topic": "Demo: Spatial Understanding & App Prototyping",
      "key_points": [
        "Exploring Build tab demo apps in Google AI Studio",
        "Spatial Understanding demo detecting objects with 2D bounding boxes",
        "Inspecting underlying TypeScript/React implementation code"
      ]
    },
    {
      "start": 460,
      "end": 481,
      "topic": "Conclusion & Next Steps",
      "key_points": [
        "Summary of multimodal developer workflows",
        "Preview of app prototyping in the next video"
      ]
    }
  ],
  "action_items": [
    {
      "id": "ACT-01",
      "title": "Open Google AI Studio and attach video URL",
      "description": "In Google AI Studio Chat Prompt, click the '+' button, select YouTube Video, paste a video URL, and observe token consumption in Run Settings.",
      "type": "explore",
      "difficulty": "easy",
      "priority": null
    },
    {
      "id": "ACT-02",
      "title": "Query long video context with structured prompt",
      "description": "Prompt Gemini 2.5 Pro to extract key sections, timestamps, core benefits, and call to action points from the ingested video.",
      "type": "prompt",
      "difficulty": "easy",
      "priority": null
    },
    {
      "id": "ACT-03",
      "title": "Test Spatial Understanding demo app in Build tab",
      "description": "Navigate to Build -> Showcase -> Spatial Understanding, provide an image, request 2D bounding boxes, and review the generated React/TypeScript code.",
      "type": "prototype",
      "difficulty": "medium",
      "priority": null
    }
  ],
  "visual_context": {
    "visual_elements": [
      {
        "timestamp": 14,
        "element_type": "title_slide",
        "content": "Google Cloud title slide: 'Google AI Studio: multimodal capabilities'",
        "confidence": 0.99,
        "frame_path": null
      },
      {
        "timestamp": 85,
        "element_type": "graphic_card",
        "content": "Four equivalence cards for 1M tokens: 50000 lines of code, 5 years of texts, 8 English novels, 200 podcast episodes",
        "confidence": 0.98,
        "frame_path": null
      },
      {
        "timestamp": 272,
        "element_type": "animation",
        "content": "Live streaming interaction mock showing Gemini advising on LEGO castle assembly with 2x4 gray bricks",
        "confidence": 0.95,
        "frame_path": null
      },
      {
        "timestamp": 312,
        "element_type": "ui_screen",
        "content": "Google AI Studio Chat Prompt interface with Gemini 2.5 Pro Preview selected in Run settings panel",
        "confidence": 0.98,
        "frame_path": null
      },
      {
        "timestamp": 334,
        "element_type": "modal_dialog",
        "content": "Video settings modal inserting YouTube URL 'https://youtu.be/Ykyo3tKObas' into chat prompt",
        "confidence": 0.97,
        "frame_path": null
      },
      {
        "timestamp": 360,
        "element_type": "ui_prompt",
        "content": "Chat prompt with embedded video tokenized to 415,928 tokens and text query requesting summary",
        "confidence": 0.98,
        "frame_path": null
      },
      {
        "timestamp": 400,
        "element_type": "ui_response",
        "content": "Structured video summary showing introduction timestamp (0:00 - 0:46), GDC Overview (1:19 - 2:04), and Call to Action",
        "confidence": 0.97,
        "frame_path": null
      },
      {
        "timestamp": 435,
        "element_type": "ui_catalog",
        "content": "Build tab in Google AI Studio showing cards: Mumble Jumble, Live Audio, PromptDJ, Spatial Understanding",
        "confidence": 0.96,
        "frame_path": null
      },
      {
        "timestamp": 455,
        "element_type": "ui_demo",
        "content": "Spatial Understanding web app preview with bounding box toggle controls, image preview with origami cats, and TSX source editor",
        "confidence": 0.97,
        "frame_path": null
      }
    ],
    "summary": "Walkthrough of Google AI Studio multimodal features: conceptual context window scaling, image/video generation guidance (Imagen and Veo), YouTube video upload and summarization demo, and app prototyping using the Spatial Understanding demo.",
    "frame_analysis_count": 9
  },
  "metrics": {
    "keyframes_images": "ok",
    "keyframes_images_source": "stills"
  },
  "provenance": {
    "created_at": "2026-10-16T07:19:03.888Z",
    "tool_versions": {
      "videopack": "v0",
      "extractor": "gemini-3.8-flash",
      "pack_structure": "b1-structured-v1",
      "extract_pipeline": "p1.6-direct-shard-v1"
    },
    "source_hash": "2778c5fc08a1b7f19fe0a83bca959e24ecf20040c3cc1a3b6edd244d68c5e4ea",
    "notes": "Identity pack plus Gemini 3.8 Flash spec extract via direct Interactions shards. Keyframe images OK: YouTube public stills captured as JPEG bytes after storyboard miss (ytimg URLs not stored)."
  },
  "grounded_spec": {
    "status": "available",
    "spec": {
      "version": "1",
      "outputClass": "browser-interactive",
      "sourceStatus": "full",
      "confidence": 0.98,
      "limitations": [
        "Live webcam/audio streaming and external Gemini API key executions require server/cloud backend services outside local browser sandbox.",
        "YouTube video fetching is simulated via local mock data unless connected to active Google AI Studio session."
      ],
      "app": {
        "name": "Google AI Studio Multimodal Playground Explorer",
        "purpose": "Interactive browser tool mimicking Google AI Studio multimodal workflows: video long-context prompt analysis and image spatial bounding box detection."
      },
      "screens": [
        {
          "id": "scr_chat_prompt",
          "name": "Chat Prompt Studio",
          "purpose": "Attach video URLs, configure Gemini model settings, and execute long-context summary prompts."
        },
        {
          "id": "scr_spatial_build",
          "name": "Spatial Understanding Demo",
          "purpose": "Preview object detection with interactive 2D bounding boxes and inspect prototype React code."
        }
      ],
      "state": [
        {
          "id": "st_attached_media",
          "name": "Attached Media Item",
          "description": "Metadata and token count of the attached YouTube video or image source.",
          "persistence": "memory"
        },
        {
          "id": "st_prompt_query",
          "name": "Prompt Query Text",
          "description": "User instruction given to the model for multimodal analysis.",
          "persistence": "memory"
        },
        {
          "id": "st_analysis_output",
          "name": "Analysis Output",
          "description": "Generated structured summary with timestamps or detected 2D bounding boxes.",
          "persistence": "memory"
        }
      ],
      "requirements": [
        {
          "id": "G-REQ-01",
          "screenId": "scr_chat_prompt",
          "title": "Video URL Attachment and Token Display",
          "detail": "Users can paste a YouTube video URL, save it into the prompt session, and display the calculated token count (~415,928 tokens).",
          "classification": "observed",
          "required": true,
          "capabilities": [
            "browser-ui",
            "local-state"
          ],
          "rationale": "Directly demonstrated in video when inserting YouTube video into prompt.",
          "citations": [
            {
              "kind": "transcript",
              "index": 30,
              "videoId": "auJzb1D-fag",
              "startSeconds": 344,
              "endSeconds": 353,
              "quote": "So let's click the plus icon in the chat prompt interface, and this is coming from YouTube. So let's click that YouTube video, paste the video URL here, and click Save."
            },
            {
              "kind": "visual",
              "index": 5,
              "videoId": "auJzb1D-fag",
              "startSeconds": 360,
              "endSeconds": 360,
              "quote": "Chat prompt with embedded video tokenized to 415,928 tokens and text query requesting summary"
            }
          ]
        },
        {
          "id": "G-REQ-02",
          "screenId": "scr_chat_prompt",
          "title": "Detailed Video Summary Generation",
          "detail": "The interface displays a structured summary containing Introduction timestamps, Core Benefits, Specifications, Demo user journeys, and Call to Action.",
          "classification": "observed",
          "required": true,
          "capabilities": [
            "browser-ui",
            "local-state"
          ],
          "rationale": "Model response shown in Google AI Studio after running prompt.",
          "citations": [
            {
              "kind": "transcript",
              "index": 33,
              "videoId": "auJzb1D-fag",
              "startSeconds": 379,
              "endSeconds": 395,
              "quote": "Okay wow, just as instructed, the model provided a detailed summary, very detailed, with main points, evidence, and some conclusions. This output is structured very nicely as well."
            },
            {
              "kind": "visual",
              "index": 6,
              "videoId": "auJzb1D-fag",
              "startSeconds": 400,
              "endSeconds": 400,
              "quote": "Structured video summary showing introduction timestamp (0:00 - 0:46), GDC Overview (1:19 - 2:04), and Call to Action"
            }
          ]
        },
        {
          "id": "G-REQ-03",
          "screenId": "scr_spatial_build",
          "title": "2D Bounding Box Visualizer",
          "detail": "Display uploaded image with overlaid 2D bounding boxes and labels when '2D bounding boxes' option is selected and prompt is sent.",
          "classification": "observed",
          "required": true,
          "capabilities": [
            "browser-ui",
            "local-state"
          ],
          "rationale": "Shown in the Spatial Understanding prototype demo inside the Build tab.",
          "citations": [
            {
              "kind": "transcript",
              "index": 38,
              "videoId": "auJzb1D-fag",
              "startSeconds": 438,
              "endSeconds": 454,
              "quote": "When we send this to the model, we can see that it's added 2D bounding boxes and labeled what each item is. And if we click the code icon, we can see the behind the scenes code for what's actually making this work."
            },
            {
              "kind": "visual",
              "index": 8,
              "videoId": "auJzb1D-fag",
              "startSeconds": 455,
              "endSeconds": 455,
              "quote": "Spatial Understanding web app preview with bounding box toggle controls, image preview with origami cats, and TSX source editor"
            }
          ]
        }
      ],
      "acceptanceCriteria": [
        {
          "id": "AC-01",
          "requirementId": "G-REQ-01",
          "given": "User is on the Chat Prompt Studio screen",
          "when": "User clicks the add media button and selects YouTube Video with a valid URL",
          "then": "A video thumbnail badge appears in the input with token count ~415,928 tokens"
        },
        {
          "id": "AC-02",
          "requirementId": "G-REQ-02",
          "given": "A video is attached and prompt requesting detailed summary is run",
          "when": "Inference finishes",
          "then": "Structured sections with timestamps (e.g. 0:00 - 0:46 Introduction) are rendered"
        },
        {
          "id": "AC-03",
          "requirementId": "G-REQ-03",
          "given": "User is on the Spatial Understanding Demo screen",
          "when": "User clicks '2D bounding boxes' and sends the request",
          "then": "Origami objects in the window frame image are highlighted with labeled colored bounding boxes"
        }
      ],
      "unresolved": [
        {
          "id": "UNRES-01",
          "requirementIds": [
            "G-REQ-01",
            "G-REQ-02"
          ],
          "question": "What is the token cost pricing tier when ingesting over 1M tokens in Gemini 2.5 Pro Preview?",
          "required": false
        }
      ],
      "unsupported": [
        {
          "id": "UNSUPP-01",
          "requirementIds": [
            "G-REQ-01"
          ],
          "capability": "server",
          "reason": "Direct live YouTube audio/video frame extraction requires Google AI Studio backend ingestion servers.",
          "required": true
        }
      ],
      "source": {
        "packId": "vp:v0:auJzb1D-fag",
        "videoId": "auJzb1D-fag",
        "sourceUrl": "https://www.youtube.com/watch?v=auJzb1D-fag",
        "sourceHash": "2778c5fc08a1b7f19fe0a83bca959e24ecf20040c3cc1a3b6edd244d68c5e4ea"
      }
    },
    "contentHash": "e86e5b3383a64cc4508b4d5681a4c3e6e3aafe0c64473cf796e88cb8c82ea40c"
  }
} as VideoPackV0Json;

export function runbookPackFixture(): VideoPackV0Json {
  return JSON.parse(JSON.stringify(SAVED_PACK)) as VideoPackV0Json;
}
