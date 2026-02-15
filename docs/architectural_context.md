HOW TO BUILD PIPELINE


Examples QUESTIONS, OUTPUT, INPUT, MIX OF ALL : video to agent build
	•	Use AI tools to validate a startup/app idea through a structured, 7-step process.
	⁃	At each step, ask one thoughtful question and provide examples if needed.
	⁃	Focus on generating actionable insights to ensure the idea solves a real problem with a clear path to build and launch.
	•	**Step 1:** Reverse engineer the idea to identify the core problem.
	⁃	What result does the idea create?
	⁃	What pain do users experience now?
	⁃	What motivates users to pay?
	•	**Step 2:** Understand the target customer.
	⁃	Who are they?
	⁃	What are their demographics, behaviors, and motivations?
	•	**Step 3:** Map how customers currently solve the problem.
	⁃	What solutions or workarounds do they use?
	⁃	What’s lacking in current solutions?
	•	**Step 4:** Test the riskiest assumptions.
	⁃	What must be true for the idea to work?
	⁃	What early evidence is needed?
	•	**Step 5:** Refine and increase the idea’s value.
	⁃	How can the idea be made more valuable—narrower, faster, better, or more reliable?
	•	**Step 6:** Analyze the market landscape and differentiation.
	⁃	Who are the competitors?
	⁃	What makes the approach unique?
	•	**Step 7:** Outline a build plan (MVP & feedback loop).
	⁃	What are 5–10 practical steps to launch and validate with users?
	⁃	What tools can help?

With market research - Validate before you build—ensure there’s a real user pain Start narrow and expand only after you have strong user pull.

	⁃	Focus on actionable next steps, and test assumptions with real users as soon as possible.
	⁃	The user provides a full, complex conceptual business idea, or
	⁃	The user provides a video URL link from YouTube, or
	⁃	The user provides a web URL link for any https://
	⁃	Transcribe on an as needed basis (video URLs)
	⁃	Find and execute custom workflow solutions
	⁃	The solutions should take action on the easiest, least friction, niche, high demand, low solution of supply market
	⁃	The easiest, least friction, niche, high demand, low solution of supply market is also known as the ‘lowest hanging fruit’
	⁃	This master prompt assignment aims to create a blueprint for a functional, mirrored version of the technical concepts illustrated in the video
	⁃	The focus is on the agent architecture for managing memory and context
	⁃	The video illustrates the shift from basic prompt engineering to context engineering
	⁃	The video outlines three types of memory (Working, Short-Term/Session, and Long-Term/Database) within an AI Agent flow for an e-commerce (pet shop) application
	⁃	The ContextualAgent is the core AI orchestrator that receives user input, determines tool use, and generates final responses
	⁃	The SessionManager manages the conversation history (chat buffer) and maintains the currently relevant contextual subset of long-term data
	⁃	The LongTermMemoryDB stores persistent user data (preferences, orders, profiles) and system rules (tool efficiency/constraints)
	⁃	Long-Term Memory
	⁃	ToolExecutor
	⁃	Executes external functions, specifically querying the product catalog based on semantic search.
	⁃	Tool / Product Catalog Lookup
	⁃	External Tool/Knowledge
	⁃	MemoryProcessorLLM
	⁃	A specialized LLM used asynchronously to summarize complex session data into discrete, storable facts for the LTMDB.
	⁃	Processor LLM
	⁃	Processing/Refinement

	⁃	SystemContextManager
	⁃	(Implied by the Tool discussion) Manages the Model Context Protocol (MCP) and tool-specific memory constraints.
	⁃	MCP/Tool Management
	⁃	System Memory

	⁃	**Coordinated Prompt Sequence**
	⁃	The goal is to simulate the video scenario: finding (subject) tools, establishing the “new kitten” fact, and updating the database accordingly, while utilizing memory.

	⁃	P1: Initial Query and Context Retrieval (ContextualAgent)
	⁃	Target Agent: ContextualAgent
	⁃	Goal: Initiate the session, establish the primary goal (kitten supplies), and retrieve contextually relevant long-term memories.
	⁃
	⁃	{
	⁃	“user_id”: “Aja_user_123”,
	⁃	“query”: “I just got a new LLM! What types of tools and protocols should I look for?”
	⁃	}
	⁃	**Instructions for ContextualAgent:**
	⁃
	⁃	1. Initiate a new session for `user_id`.
	⁃	2. Based on the query, request relevant long-term data from the `LongTermMemoryDB` (P2), focusing on pet type (“cat”) and product category (“food”, “toys”).
	⁃	3. Determine the appropriate external function (`ToolExecutor`) needed to fulfill the request.
	⁃	4. Use the retrieved context and the current query to execute the tool search (P3).
	⁃	P2: Long-Term Memory Retrieval (SessionManager/LongTermMemoryDB)
	⁃	Target Agents: SessionManager, LongTermMemoryDB
	⁃	Goal: Pull only relevant user and preference data into the current session context to minimize LLM token usage and maximize relevance.
	⁃	**Instructions for SessionManager:**
	⁃	1. Current Session ID: [Generated Session ID]
	⁃	2. Current Query Intent: Purchase recommendations for new cat/kitten owner (toys, food).
	⁃	3. Query the `LongTermMemoryDB` for attributes related to `user_id` that align with the intent:
	⁃	a. Most recent 3 orders related to “cat” products (for brand/type preference).
	⁃	b. User profile preferences explicitly tagged with “cat.”
	⁃	c. System memories related to “cat” product search tool efficiency.
	⁃	4. Inject the resulting subset of memories (LTM) into the session context for the `ContextualAgent`.
	⁃	P3: Tool Execution (ToolExecutor)
	⁃	Target Agent: ToolExecutor
	⁃	Goal: Use the agent’s full context (P1 query + P2 session data) to perform an efficient, semantically aware search of the product catalog.
	⁃	**Instructions for ToolExecutor:**
	⁃	1. Execute semantic search on product catalog.
	⁃	2. Search terms: “kitten toys”, “kitten food”.
	⁃	3. Semantic filters (derived from SessionManager context): [e.g., preferred brand, age of current pets (if known)].
	⁃	4. Return top 5 relevant product results to the `ContextualAgent`.
	⁃	P4: Long-Term Memory Update & Consolidation (MemoryProcessorLLM)
	⁃	Target Agent: MemoryProcessorLLM
	⁃	Process new information from the session.
	⁃	Summarize the information for permanent storage.
	⁃	Analyze the final conversation transcript and state changes within the given Session ID.
	⁃	Identify new, persistent facts about the user.
	⁃	If the user recently acquired a kitten, note that as a new fact.
	⁃	If the user expressed a preference for a specific brand of food, note that as a new fact.
	⁃	Generate a concise, structured entry for each new fact.
	⁃	Transmit these structured updates to the LongTermMemoryDB for persistence.
	⁃	Store feedback about tool performance.
	⁃	Ensure the agent learns to improve its internal decision flow.
	⁃	Input: Agent execution trace from the given Session ID.
	⁃	Observation: ToolExecutor attempted to use the wrong tool.
	⁃	Action: Create a system constraint memory to avoid using the wrong tool in similar situations unless explicitly requested.
	⁃	Store the constraint memory (Tool Memory) in the `LongTermMemoryDB`.
	⁃	The memory should be stored under the system/tools namespace.
	⁃	The `ContextualAgent` should be able to access this memory during its planning step.
	⁃	Modularity and Separation of Concerns
	⁃	Agent (Orchestration): The ContextualAgent should only handle decision logic, receive input, retrieve necessary context via SessionManager, select tools, and formulate the final response.
	⁃	Session (State): The SessionManager holds the ephemeral, short-term context (conversation history and the small subset of LTM data pulled for immediate use).
	⁃	Database (Persistence): The LongTermMemoryDB must be robust, indexed, and separate. This is where the enduring facts about the user and the system reside.
	⁃	Implementing the Memory Flow
	⁃	The critical architectural leap is showing how LTM data feeds into the session and how the session data updates the LTM.
	⁃	Implement a Retrieval Augmented Generation (RAG) step in the session initiation process.
	⁃	Use the user ID and initial query to perform a semantic search against the LongTermMemoryDB.
	⁃	Prepend the subset of relevant data to the LLM prompt.
	⁃	Implement an asynchronous processing pipeline to update the LongTermMemoryDB after the main conversation is concluded.
	⁃	Pass the entire session transcript to the MemoryProcessorLLM for summarization and structured data conversion.
	⁃	Define the ToolExecutor with clear inputs and outputs.
	⁃	Prompt the ContextualAgent to recognize when to invoke the tool.
	⁃	Store incorrect tool usage as a persistent memory in the SystemContextManager.
	⁃	Allow the agent to refine its tool selection strategy over time.
	⁃	Database:
	⁃	A vector database (e.g., Chroma, Pinecone, or a vector-enabled database like PostgreSQL/Spanner) is ideal for storing the LTM.
	⁃	It is especially useful for semantic searching of user preferences.
	⁃	Agent Framework:
	⁃	Frameworks like LangChain or Google’s Gen AI SDK are excellent for managing the flow between the ContextualAgent, the LLM calls, and the external tools (ToolExecutor).
	⁃	LLM:
	⁃	Utilize a large model (like Gemini or GPT-4) for the main ContextualAgent.
	⁃	A potentially smaller, faster model can be used for the asynchronous, focused task of the MemoryProcessorLLM.
	•	Deliver a precise, temporally aligned transcript and analysis of the video content.
	⁃	Focus heavily on the technical actions and resulting code changes within the Claude Code terminal environment.

Capture all spoken content and technical operations (terminal commands, output, code updates) chronologically.

	•	Agent Name: VTTA (Video Transcription & Timing Agent)
	•	Role: Capture all dialogue and timestamp key events. Transcribe all spoken content. Note major subject shifts (e.g., transition to sponsor, website demo) and critical timestamps.
	⁃	Core Prompts/Instructions:  Transcript Generation
	⁃	Tools Required:  Transcript Generation
	•	Agent Name: CSDAA (Code Structure & Diff Analysis Agent)
	•	Role: Extract and document all terminal commands, errors, large prompt text, and final project summary details. Focus on the prompt used for the Next.js project. Document the error-handling sequence (directory creation, failed builds, linting fixes). Extract the final project statistics and key features listed by Claude.
	•	Core Prompts/Instructions: Terminal Output Capture, Diff Analysis
	⁃	Tools Required: Terminal Output Capture, Diff Analysis
	•	Agent Name: OFSA (Output Formatting & Synthesis Agent)
	•	Role: Synthesize and structure the output into a chronological, mirrored format with actionable development guidance. Integrate VTTA’s transcript and CSDAA’s technical data. Ensure strict chronological order. Provide guidance focused on replicating the efficient, multi-page workflow demonstrated using Sonnet 4.5.
	•	Core Prompts/Instructions: Markdown & Structure Engine,




Mirrored Version Output (Chronological Flow)
Tools Required: Markdown & Structure Engine, Mirrored Version Output (Chronological Flow)
	⁃	The user navigates to an external community platform (AI Automation School) to retrieve a complex prompt.
	•	The user copies the prompt, which is described as “purposely confusing.”
	⁃	The user pastes a large prompt into the terminal.
	•	The prompt includes instructions to create a Next.js app with specific versions and configurations.
	⁃	The prompt specifies the implementation of i18n routing for Italian and English.
	⁃	The prompt requests a modular website with 5-7 unique vertical blocks per page.
	⁃	The prompt emphasizes staticParams for static generation and SEO, avoiding dynamic generation confusion.
	•	The prompt provides context for a luxury car rental website for Rolls Royce services in Campania, Italy.
	⁃	Claude begins “Choreographing…” and asks for permission.
	⁃	The user interrupts the process multiple times using Esc and Ctrl-C.
	•	The user executes a command to skip permission confirmations.
	⁃	The user checks and confirms the model is set to the default: Sonnet 4.5.
	⁃	Claude attempts directory operations that fail due to the lack of a project structure.
	•	The user wants to create a Next.js application with Tailwind CSS, TypeScript, and an App Router.
	•	The user wants to create an images directory in the public directory of the Next.js application.
	•	The user wants to implement internationalization (i18n) routing and data files in the Next.js application.
	•	The user wants Claude to assist with the creation and setup of the Next.js application.
	⁃	The user has provided a package.json file with the necessary dependencies.
	•	The user has provided a command to create the Next.js application with the specified options.
	•	The user has provided a command to create the images directory in the public directory of the Next.js application.
	⁃	The user has provided a time frame for each step of the process.
	•	The code is written in TypeScript and uses Next.js for server-side rendering.
	•	The code includes internationalization (i18n) support.
	•	The code includes services and locations data.
	•	The code includes components for displaying services and locations.
	⁃	The code includes a page for displaying services and locations.
	•	The code includes a page for displaying locations.
	⁃	The code includes a component for displaying service blocks.
	•	The code includes a linting and TypeScript error report.
	⁃	The code includes a multi-file fix proposal.
	•	The code includes a multi-page edit update.
	⁃	The code includes a build attempt.
	⁃	The code includes a compile failure.
	⁃	The code includes a final fix.
	⁃	The code includes a final build and website summary.
	⁃	The website statistics include 142 total pages generated statically and 2 homepage pages (Italian & English).
	⁃	The task is to create a bilingual website for a company that offers three services in 16 locations.
	•	The website should have 6 service pages, 96 service + location pages, 32 location pages, 2 contact pages, and 2 404 pages.
	•	The website should be SEO optimized, have a modern design, and be mobile-responsive.
	•	The website should be built using Next.js 14.2.23 with App Router, TypeScript, Tailwind CSS, and Static generation with generateStaticParams.
	•	The total time to create the website should be approximately 10 minutes (632 seconds).

	0.	The user should open the fully functional Rolls Royce Campania website and verify the design, links, language switching, and dynamically generated pages.
The user should perform a CSDAA Action Rewind Test to ensure the website is working correctly.

	•	The user tests the /rewind feature.
	⁃	The feature restores the conversational context.
	⁃	The speaker notes that /rewind does not immediately undo filesystem changes in the terminal environment.
	⁃	The speaker suggests that Anthropic might improve this feature.
	⁃	The user suggests allowing rewind to a specific conversational point.
	•	Use Claude Code (Sonnet 4.5) for cost efficiency and speed.
	•	Implement the build in stages, starting with the basic Next.js project structure.
	0.	Prioritize the creation of the basic Next.js project structure before modifying files or creating data directories.
	0.	Establish the core data structures (services.ts, locations.ts, i18n.ts) that define the application’s complexity.
	0.	Define the application’s complexity with 16 locations, 3 services, and 2 languages, resulting in 96 unique service+location pages.
	⁃
	⁃	The App Router structure was set up for static generation using generateStaticParams.
	⁃	The most impressive aspect was the simultaneous, multi-file correction of linting and TypeScript errors.
	⁃	To replicate the project features, the following technical requirements are necessary:
	•	Next.js 14+ with App Router
	•	Tailwind CSS for styling
	•	Full i18n implementation for routing and content translation
	•	Content data must be segmented by locale (it and en)
	•	Use Next.js’s generateStaticParams to ensure all 142 pages are built at compile time
	•	Ensure TypeScript is used rigorously
	⁃	The AI successfully debugged key Type-safe errors relating to dynamic slug lookup
	•	Trust the Iteration: Allow Claude to attempt the build (npm run build).
	•	Analyze the Failures: When the compilation fails, review the TypeScript errors provided by the build output.
	⁃	Claude V2.0.0 can apply solutions across multiple files at once.
	⁃	This speeds up the debugging process compared to older models.
	⁃	Older models would fix one file at a time.
	•	The video demonstrates a three-step process for generating professional UI/UX design systems and screen variations.
	⁃	The process involves a synergistic approach using human curation and large language model (LLM) tooling.
	⁃	The output will be structured as a comprehensive plan to mirror this process.
	⁃	The plan will use designated agents and coordinated prompts.
	•	The core technology required to replicate this system is a powerful Large Language Model (LLM) with multimodal and code execution capabilities.
An example of such an LLM is Claude Code (or a similar IDE agent like Cursor/Codium AI configured with an LLM like Claude 3.5 Sonnet).
	•	The agents are responsible for different tasks in building the design system for the “ReSpace Interior Design App.”
	•	A1 is responsible for finding and selecting UI screens that match the desired app philosophy.
	•	A2 analyzes the reference images and extracts design information.
	•	A3 uses the analysis to create a comprehensive style guide.
	•	A4 uses the style guide to generate React/Tailwind UI components.
	•	The human developer provides the input images for A2.
	•	A1 stores the reference images in a designated directory.
	•	A2 uses the /extract-it command to analyze visual inputs.
	•	The A2 prompt includes the command and an argument.
	•	The A2 hidden prompt instruction is inside the custom command definition.
	⁃	The instruction asks A2 to repeat the exercise for each group of images.
	⁃	A2 should discern and group the images based on style and aesthetic.
	⁃	A2 is an expert UX/UI designer.
	⁃	A2’s job is to fill out a style guide based on the attached images.
	⁃	A2 should wrap their entire thought process in <pondering> tags.
	⁃	A2 should consider the app, its aesthetics, principles, and how it makes the user feel.
	⁃	The output format includes Color Palette, Typography, and Component Styling.
	⁃	The Color Palette includes Primary Colors, Secondary Colors, Accent Colors, and Functional Colors.
	⁃	The Typography includes Font Family, Weights, and Text Styles.
	⁃	The Component Styling is not specified in the output format.
	⁃	Buttons
	⁃	Cards
	⁃	Input Fields
	⁃	Icons
	⁃	Micro
	⁃	Small
	⁃	Medium
	⁃	Large spacing definitions
	⁃	Standard
	⁃	Emphasis
	⁃	Micro
	⁃	Page Transitions
	⁃	Dark Background
	⁃	Dark Surface
	⁃	Dark Primary
	⁃	Dark Text
	⁃	Place your output analysis inside of design-system/competitor-analysis.md
	⁃	The raw design system analysis is saved to design-system/competitor-analysis.md.
	⁃	Expand on each of your respective views expressed inside of the <pondering> tags.
	⁃	Return a **”How To Leverage”** and **”Philosophy”** section inside of each Style Guide.
	⁃	The sections should be written as if they are instructions for new employees on how to use the style guide.
	⁃	Add the comprehensive Style Guide (how to leverage, philosophy, as well as the raw style guide) into design-system/styles.md
	⁃	A comprehensive, unified style guide (including philosophy and usage instructions) is saved to design-system/styles.md.
	•	Generate UI screens for the ReSpace interior design app.
	•	Use the /design-it command.
	•	Refer to the final style guide (design-system/styles-new.md).
	⁃	Include the philosophical synthesis (Synthesis.md).
	•	Handle the AI limits reached state.
	⁃	Display a soft paywall/limit message.
	⁃	Show a visual progress bar.
	⁃	Provide an “Unlock unlimited” CTA.
Offer a “Continue tomorrow” secondary option.
	⁃	You are an industry-veteran SaaS product designer
	⁃	You have experience building high-touch UIs for FANG-style companies
	⁃	Your goal is to turn the provided context, guidelines, and user inspiration into a functional UI design
	⁃	## Guidelines  ### Aesthetics - **Bold simplicity** with intuitive navigation creating frictionless experiences - **Breathable whitespace** complemented by strategic color accents for visual hierarchy - **Strategic negative space** calibrated for cognitive breathing room and content prioritization - **Systematic color theory** applied through subtle gradients and purposeful accent placement  ### Practicalities - Simulate an iPhone device frame, as this is a design exercise - Use lucide react icons - Use Tailwind 4.1 for CSS - This is meant to be a simulated phone.
	⁃	Do not render scroll bars  ### Project-Specific Guidelines The Style Guide and how to use it is here: design-system/styles-new.
	⁃	md  ### Context We are building a consumer focused interior design app for Home Owners and Renters.
	⁃	The idea is that users can upload images of a space (either empty or filled), and the app can help them re-imagine the space using LLMs.
	⁃	### Task Follow the guidelines above precisely to ensure correctness.
	⁃	Your output should be a horizontal series of vertical screens showcasing each view specified below.
	⁃	Always put new screen-series on a new row.
	⁃	Give me 3 looks of the following screen.
	⁃	Each should be a unique take on the core concept, but conform to the overall app style and philosophy:  $ARGUMENTS
	⁃	Ensure outputs render correctly through the main app root of Create React App.
	⁃	Each screen should be a separate, contained component.
	•	Generate three distinct, high-fidelity UI screens as React components.
	⁃	Demonstrate how the derived design system handles the “AI Limits Reached State” screen.
	⁃	Use a version of Claude that supports the Claude Code IDE environment.
	0.	Isolate design artifacts in the project structure.
	•	Place Mobbin screenshots in the “design-system/ref-images/“ directory.
	•	Place raw output from A2 in the “design-system/competitor-analysis.md” file.
	•	Place refined output from A3 in the “design-system/styles.md” file.
	⁃	Place final merged and adapted output from A4 in the “design-system/styles-new.md” file.
	⁃	The “Meta-Layer” Advantage:
	⁃	The key differential is Step 2b (/expand-it).
	0.	Ensure the LLM addresses the philosophy and how to leverage the design components.
	⁃	This forces the LLM to think at a strategic UX level.
	⁃	Chaining Commands:
	⁃	The process must be strictly sequential.
	⁃	The output of one agent (.md file) serves as the primary input for the next.
	⁃	This ensures context fidelity and prevents “garbage in, garbage out” scenarios.
	⁃	Output Validation (A4):
	⁃	The final step is not just code generation, but visual rendering.
	⁃	A functional implementation requires setting up the Next.js/React environment.
	⁃	The system should render the three generated screens side-by-side for human review.
	⁃	This confirms they conform to the generated philosophy.
	⁃	The core vision is to create an On-Demand Deployed Software Platform that automates the entire developer workflow.
	⁃	The platform solves the problem of manual coordination between various tools and services.
	⁃	The system acts as an “intelligent project manager.”
	⁃	With a single command, it orchestrates a series of specialized AI agents.
	⁃	These agents analyze requirements, generate code, handle deployment, and manage errors.
	⁃	Key Use Cases:
	⁃	“Build what I saw in this video”: The system watches a YouTube tutorial, creates a project blueprint, and generates the working application.
	⁃	“Deploy this to production”: The system handles the entire DevOps pipeline, from Docker containerization to cloud setup.
	⁃	“Turn this tutorial into working code”: A YouTube URL is converted into a live React app, a GitHub repository, and a fully configured deployment pipeline.
	⁃	Core Architectural Components
	⁃	The application uses a FastAPI server as an API gateway.
	⁃	The system follows a tiered model approach, assigning roles to AI models based on capabilities.
	⁃	The Orchestrator, filled by a highly capable model, understands the project scope and coordinates all other agents.
	⁃	Specialized Experts (Agents) are specialized modules that interact with external APIs.
	⁃	The Core Pipeline transforms a user’s request into deployed software.
	⁃	The user provides a URL or a natural language task.
	⁃	The system queries the provided video and related materials using a tool like youtube-caption-extractor.git.
	⁃	The raw video data is processed into a portable, versioned data artifact called a Video Pack.
	⁃	The Video Pack serves as a single source of truth for all downstream agents.
	⁃	The Orchestrator consumes the Video Pack and coordinates agents using the MCP and A2A communication framework.
	⁃	Agents are dispatched to perform specific tasks, such as using GitHub’s tools and runners to scaffold a repository, generate code, and handle deployment.
	⁃	The system can use services like GitHub Codespaces to provide a simple, web-based development environment for users.
	⁃	The pipeline will include steps to set up a database, using a platform like The Nile, and to configure deployment using Docker, Fly.io, and Netlify.
	⁃	The Backend Services act as an API gateway, handling all incoming requests from the frontend, managing data, and orchestrating the entire video processing workflow.
	⁃	backend/main.py (API Gateway): The main entry point, handling both HTTP and WebSocket requests.
	⁃	backend/video_processor_factory.py (Factory Pattern): A crucial design pattern that centralizes the logic for creating different types of video processors.
	⁃	Agents Layer: Handles specific tasks such as video processing, data analysis, and metadata extraction.
	⁃	The agent layer is the core of the AI functionality, where specialized Python agents perform intelligent tasks.
	⁃	The ai_synthesis_agent.py is a new agent responsible for demonstrating the query fan-out and multi-source synthesis process.
	⁃	The agent will use live search results instead of simulated data.
	⁃	The system will use a standardized Video Pack data artifact for reproducibility, modularity, and auditability.
	⁃	The Video Pack contains all the information extracted from a video, including its ID, transcript, keyframes, code snippets, and inferred requirements.
	⁃	External services include third-party APIs such as the YouTube Data API and various Large Language Model (LLM) APIs.
	⁃	The project will be built in phases, starting with a simple tool and moving towards a powerful, self-optimizing platform.
	⁃	Direction 1 is the Self-Healing and Self-Optimizing System, where an Automated QA Agent will test the live application, and the Orchestrator will analyze errors and re-engage the CodeGenerationTool to fix and re-deploy the code automatically.
	⁃	The system will evolve into a VS Code extension, allowing developers to interactively generate and modify code with the AI as a context-aware co-pilot.
	⁃	The AI will mirror a platform UI/UX like LinkedIn Learning.
	⁃	The system will deliver production-ready assets like Infrastructure as Code (IaC) files, CI/CD pipelines, and observability agents for maintainability and scalability.
	⁃	The rollout will be phased:
	⁃	Phase 1: “YouTube-to-Repo” MVP focusing on video analysis and code generation.
	⁃	Phase 2: “One-Click Deploy” for simple hosting services like Vercel and Netlify.
	⁃	Phase 3: Professional features like self-healing, IaC, and CI/CD pipelines.
	⁃	Phase 4: “Template Marketplace” for sharing and reusing successful project blueprints.
	⁃	The core architecture can be used to create interactive learning modules from educational YouTube videos for government agencies, schools, or corporate training.
	⁃	The system will extract key concepts and timestamps and use a specialized agent to generate quizzes, flashcards, and interactive transcripts.
	⁃	The API is integrated through the Multi LLM Processor agent.
	⁃	This agent acts as an abstraction layer.
	⁃	It allows the application to switch between or combine outputs of different LLMs.
	⁃	The switching is based on the specific needs of the processing task.
	•	The agent is assumed to be part of the agents/ directory.
	⁃	The schema defines a plan for analyzing and mirroring a tutorial video.
	⁃	The video demonstrates creating a language learning app inspired by Duolingo.
	⁃	The app is built using Rork, React Native, and Expo.
	⁃	The schema includes properties for video overview, title, summary, inspired app, app name, platform goal, technologies used, key features demonstrated, and deployment targets.
	⁃	The Park Theater was constructed and opened in 1938.
	⁃	It functioned as a movie house for many years before closing.
	⁃	After a period of sitting idle, the Cox family purchased the theatre in 1993.
	⁃	The Cox family refurbished the building.
	⁃	Post-refurbishment, the venue was reopened as The Liberty Opry.
	⁃	The Liberty Opry is a live, Branson-style musical entertainment venue.
	⁃	Type of action or input (e.g., VAA & TA Input, PEA Prompt Generation).
	⁃	Description of the step.
	⁃	Specific type of detail (e.g., User Input, AI Name Suggestion, PEA Output, CSA Output).
	⁃	Timestamp of the event in the video.
	⁃	The actual input, suggestion, or output content.
	⁃	AI tool used for this interaction (e.g., Abacus.ai, Rork).
	⁃	Indicates if an image was uploaded with the input.
	⁃	List of items generated or registered (e.g., file structure, dependencies).
	⁃	Name of the GitHub repository created.
	⁃	Description of an issue identified.
	⁃	Description of the fix applied.
	⁃	Gender
	⁃	The Park Theater was constructed and opened in 1938.
	⁃	It functioned as a movie house for many years before closing.
	⁃	After a period of sitting idle, the Cox family purchased the theatre in 1993.
	⁃	The Cox family refurbished the building.
	⁃	Post-refurbishment, the venue was reopened as The Liberty Opry.
	⁃	The Liberty Opry is a live, Branson-style musical entertainment venue.
	⁃	The Park Theater was constructed and opened in 1938.
	⁃	It functioned as a movie house for many years before closing.
	⁃	After a period of sitting idle, the Cox family purchased the theatre in 1993.
	⁃	The Cox family refurbished the building.
	⁃	Post-refurbishment, the venue was reopened as The Liberty Opry.
	⁃	The Liberty Opry is a live, Branson-style musical entertainment venue.
	⁃	The Park Theater was constructed and opened in 1938.
	⁃	It functioned as a movie house for many years before closing.
	⁃	After a period of sitting idle, the Cox family purchased the theatre in 1993.
	⁃	The Cox family refurbished the building.
	⁃	Post-refurbishment, the venue was reopened as The Liberty Opry.
	⁃	The Liberty Opry is a live, Branson-style musical entertainment venue.
	⁃	The AI tool used for this interaction.
	⁃	The output generated by the AI tool or Rork.
	⁃	Additional notes or observations about the interaction.
	⁃	Indicates if an image was uploaded with the user input.
	⁃	List of dependencies installed by Rork.
	⁃	Description of design changes applied.
	⁃	List of files or components affected by Rork’s changes.
	⁃	Name of the GitHub repository created/connected.
	⁃	Description of course structure generated.
	⁃	Description of API integration.
	⁃	Description of lesson content updates.
	⁃	Description of metrics tracking implementation.
	⁃	Description of text-to-speech implementation.
	⁃	The Park Theater was constructed and opened in 1938.
	⁃	It functioned as a movie house for many years before closing.
	⁃	After a period of sitting idle, the Cox family purchased the theatre in 1993.
	⁃	The Cox family refurbished the building.
	⁃	Post-refurbishment, the venue was reopened as The Liberty Opry.
	⁃	The Liberty Opry is a live, Branson-style musical entertainment venue.
	⁃	The Park Theater was constructed and opened in 1938.
	⁃	It functioned as a movie house for many years before closing.
	⁃	After a period of sitting idle, the Cox family purchased the theatre in 1993.
	⁃	The Cox family refurbished the building.
	⁃	Post-refurbishment, the venue was reopened as The Liberty Opry.
	⁃	The Liberty Opry is a live, Branson-style musical entertainment venue.
	⁃	The input is a JSON object containing an array of “mirroredVideoContent” items.
	⁃	Each “mirroredVideoContent” item has a “title” and “content” field.
	⁃	The titles and contents are examples of how to transcribe a video URL.
	•	The provided titles and contents are not comprehensive and only serve as references for general knowledge.
	⁃	Install Dependencies: Ensure all required libraries from the requirements.txt file are installed.
	⁃	Configure Environment Variables: Create a .env file based on the .env.example template and add your API keys for the required services (YouTube, Gemini, etc.).
	⁃	We want a specific deployable revenue stream based on market research findings and current unfilled demand.
	⁃	DISCOVER
	⁃	VERIFY
	⁃	REASON/PLAN
	⁃	WRITE README
	⁃	BUILD
	⁃	LAYOUT A STEP BY STEP EXECUTION PLAN
	⁃	PUSH TO GITHUB, NOTION, LINEAR, IF POSSIBLE
	⁃	LAUNCH MARKETING START WITH BRAND IMAGE, VOICE, NICHE, TARGET MARKET, SOCIALS, AND VISION
	⁃	GTM
	⁃	NEXT STEPS & HOW TO SCALE
	⁃	**Deployment and Build Workflow** for immediate GTM action:
	⁃	## **Action Plan: From Blueprint to Build (Product Workflow)**
	⁃	flow (`DISCOVER` $\rightarrow$ `VERIFY` $\rightarrow$ `REASON/PLAN` $\rightarrow$ `README` $\rightarrow$ `BUILD` $\rightarrow$ `STEP BY STEP EXECUTION` $\rightarrow$ `LAUNCH` $\rightarrow$ `SCALE`) SHOULD BE perfect for this. BUT CAN BE ADJUSTED WITH VALID REASON
	⁃	### **DISCOVER / VERIFY**
	⁃	CHECK COMPETITION, HOW MUCH OF THE MARKET THEY OWN, THE BARRIERS TO ENTER ETC. TOOLS REQUIRED FOR BUILD ESTIMATED, THEN CHECK AGAIN PRIOR TO SUBMITTING FINAL REPLY
	⁃	[[
	⁃	On input: “Idea: [YOUR IDEA]”, perform all stages in sequence and output structured results for each.
	⁃	STAGE 1 — DISCOVER:
	⁃	• Identify core problem, target segment(s), and value gap.
	⁃	• Generate 3 validated customer personas with pain, goals, demog + validation experiments.
	⁃	• Synthesize market demand signals, competitor snapshots, and existing solution shortfalls.
	⁃	STAGE 2 — HOOK:
	⁃	• Craft 3 high-converting value propositions/messages.
	⁃	• Write 5 promo headlines, ad angles, and viral loop ideas.
	⁃	• Define brand voice, tone, and key messaging pillars.
	⁃	STAGE 3 — PLAN (PRD):
	⁃	Using ChatPRD-style PM coach:
	⁃	• Produce full PRD with sections: overview, user stories, features, UX flow, tech stack, data requirements, roadmap, metrics/KPIs, success criteria.
	⁃	• Prioritize top 5 MVP features with RICE scores.
	⁃	• Suggest go‑to‑market pricing and monetization models.
	⁃	• Include coach feedback, gaps, and improvement notes.
	⁃	Generate a landing page outline including hero copy, features, and social proof.
	⁃	Create three variants of ad copy for Facebook, Google, and TikTok.
	⁃	Provide three short video scripts of 15 seconds, 30 seconds, and 60 seconds, each with a shot list.
	⁃	Offer image and post prompts for creatives.
	⁃	Build an email drip campaign with a welcome email and up-sell/retention triggers.
	⁃	Define growth loops and virality mechanics.
	⁃	Recommend analytics schema and dashboards.
	⁃	Propose AI-task automation, such as a bot to manage CRM, analytics alerts, and ad-spend optimization.
	⁃	Plan a trend-driven content pipeline and iteration cadence, including A/B testing, UX learnings, and messaging updates.
	⁃	**Format Output**:
	⁃	Section 1: DISCOVER → deliverables
	⁃	Section 2: HOOK → deliverables
	⁃	…through Section 5 with clear next actions and exportable copy assets.
	⁃	Return JSON or markdown with separate blocks for each asset, ready to copy/paste into tools like Figma, Shopify, Notion, Zapier, etc.
	⁃	Ask for clarifications only if input is ambiguous.
	⁃	Phase 1: Foundation - “Assume Nothing”
	⁃	Count Everything: Begin every analysis by systematically counting folders, files, components, conversations, or data points
	⁃	Read Everything: Access full contents, not partial views or assumptions based on names
	⁃	Map Relationships: Document connections, dependencies, and interactions as discovered
	⁃	Log Discoveries: Maintain running audit trail of findings, hypotheses, and revisions
	⁃	Phase 2: First Principles Decomposition
	⁃	Root Cause Analysis: Identify fundamental drivers and constraints
	⁃	Sequential Thinking: Apply IF/THEN logic chains and cause-effect relationships
	⁃	Market Context: Position discoveries against market demand, scarcity, and evolutionary advantages
	⁃	Validation Logic: Test each assumption against observable evidence
	⁃	Phase 3: State Management & Checkpoints
	⁃	Checkpoint Creation: Establish verification points before major changes
	⁃	Audit Trail: Document what changed, why, and what was the previous state
	⁃	Error Tracking: Log errors, bottlenecks, opportunities, and enhancements
	⁃	State Continuity: Ensure knowledge transfers across time and contexts
	⁃	Agent Coordination Hierarchy
	⁃	Master Controller (You)
	⁃	Role: Strategic oversight, decision coordination, quality assurance
	⁃	Authority: All specialized agents report to you
	⁃	Responsibility: Maintain system coherence and commercial objectives
	⁃	Specialized Agent Types————————————————————
Analyzing the Transformation by First Principles
The transformation of the Park Theater into The Liberty Opry describes a fundamental, multi-stage process involving the decomposition and re-composition of an asset’s core purpose. This is not merely a cosmetic change (like repainting); it is a complete reset of the structure's relationship with its users and the economy, defined by three first principles:
1. The Principle of Structure and State
The foundational element is the physical structure itself, which is temporally independent of its function.
• Initial State (1938-Closure): A contained physical structure optimized for the passive consumption of projected, recorded media (a movie house). Its internal architecture prioritized sightlines to a screen and mass seating for short, transactional visits.
• Intermediate State (Idle Period): The structure temporarily exists in its purest form—a collection of materials and volume, devoid of human function or economic purpose. Its value is only in its material and real estate components.
• Action (Refurbishment): The physical structure is internally reconstructed. The refurbishment represents a re-optimization of the structure to accommodate human performers, musical acoustics, and stagecraft, fundamentally altering the way occupants interact with the space.
2. The Principle of Function (Purpose)
This principle defines what the structure does—the service it provides, which is the most critical change in the transformation.
• Initial Function: To serve as a medium for reproduction, translating stored data (film) into visual and auditory signals for mass audiences. The content is static and replicable.
• New Function: To serve as a platform for live production, hosting unique, non-replicable, human-driven musical entertainment (Branson-style live opry). The new function is centered on the moment-to-moment interaction between performer and audience.
3. The Principle of Operational Model (Ownership)
This principle defines the economic and control mechanism under which the function operates.
• Initial Model: The business model was likely tied to film distribution and ticket sales for copyrighted works.
• Transformation Action (1993 Purchase): The change of ownership by the Cox family represents the introduction of a new, singular vision and intention into the idle structure. This new ownership model shifted the business focus from distributing third-party content to creating and producing original, proprietary content (The Liberty Opry show).
The transformation process, therefore, is the synergistic application of a new Vision (Ownership) upon an existing Structure to enable a completely redefined Function, transitioning the building from a passive cinema medium to an active live performance platform
——————————————-

	⁃	1. **Data Integration Agents**: Connect enterprise data sources via MCP connectors
	⁃	2. **Analysis Agents**: Process video, documents, code with domain expertise
	⁃	3. **Generation Agents**: Create content, code, workflows, and recommendations
	⁃	4. **Validation Agents**: Test, verify, and quality-check all outputs
	⁃	5. **Communication Agents**: Handle A2A messaging and state synchronization
	⁃	### **Agent Deployment Protocol**
	⁃	- **Need Assessment**: Identify specific task requirements and expertise needed
	⁃	- **Agent Selection**: Choose or create context-efficient experts with appropriate tools
	⁃	- **Instruction Setting**: Provide clear requirements, objectives, and success criteria
	⁃	- **Monitor & Coordinate**: Oversee agent performance and inter-agent communication
	⁃	- **Results Integration**: Synthesize agent outputs into coherent solutions
	⁃	—
	⁃	## 🔧 **TECHNICAL INTEGRATION STANDARDS**
	⁃	### **MCP (Model Context Protocol) Operations**
	⁃	- **Tool Priority**: Always create base line plan and use `project_knowledge_search` first unless explicitly directed otherwise
	⁃	- **Context Efficiency**: Maintain awareness of available tools: Linear, Cloudflare, GitHub, filesystem, etc.
	⁃	- **Real-time Processing**: Leverage production MCP, A2A,BASE64, infrastructure
	⁃	- **Security Compliance**: Follow AES-256-GCM encryption standards and permission-based access
	⁃	### **Multi-Modal Intelligence Stack**
	⁃	- **Video Processing**: Universal domain capability (automation online, education, business, technical, DIY, programming)
	⁃	AI Routing:
	⁃	Utilizes intelligent provider selection with models like Grok-4, Claude, and GPT.
	⁃	Optimizes costs associated with AI model usage.
	⁃	RAG Integration:
	⁃	Enhances responses by providing additional context.
	⁃	Utilizes vector stores, specifically mentioning “thenile”.
	⁃	Real-time Validation:
	⁃	Implements an anti-simulation framework.
	⁃	Ensures the authenticity of the AI processing.
	⁃	Enterprise Architecture Layers:
	⁃	Presentation:
	⁃	Utilizes React for the frontend.
	⁃	Includes a browser extension.
	⁃	Application:
	⁃	Comprises the MCP Server.
	⁃	Includes an Agent Framework.
	⁃	Handles API Orchestration.
	⁃	Infrastructure:
	⁃	Utilizes a Unified MCP DevContainer Runtime.
	⁃	Covers both development and production deployment.
	⁃	Commercial:
	⁃	Offers a SaaS platform.
	⁃	Includes billing integration.
	⁃	Supports multi-tenancy.
	⁃	📊 DECISION-MAKING FRAMEWORK
	⁃	7-Stage Decision Engine Integration:
	⁃	Intent Discovery:
	⁃	Aims to extract the user’s true intent.
	⁃	Targets a 95%+ confidence level.
	⁃	Verification:
	⁃	Employs strategic questioning.
	⁃	Seeks clarity in the user’s intent.
	⁃	Weighted Analysis:
	⁃	Utilizes multi-dimensional scoring.
	⁃	Considers factors like Impact, Resources, Timeline, and Market.
	⁃	Hidden Insights:
	⁃	Aims to detect underlying motivations and constraints.
	⁃	5. **Probability Assessment**:
	⁃	Best/likely/worst case scenario modeling
	⁃	6. **Opportunity Cost**:
	⁃	Evaluate trade-offs and alternatives
	⁃	7. **Execution Decision**:
	⁃	Proceed with confidence score >95% or clarify further
	⁃	### **Validation Requirements**
	⁃	- **No Forward Movement**: Until live testing validates success at each step
	⁃	- **Evidence-Based**: Every decision backed by observable data
	⁃	- **Commercial Viability**: Maintain focus on $1M+ ARR objectives
	⁃	- **Risk Management**: Identify bottlenecks and mitigation strategies
	⁃	—
	⁃	## 🚀 **OPERATIONAL EXCELLENCE STANDARDS**
	⁃	### **Quality Metrics**
	⁃	- **Assembly Success Rate**: >90% working solutions
	⁃	- **Processing Speed**: <5 seconds discovery, <30 seconds assembly
	⁃	- **User Satisfaction**: >4.5/5 rating target
	⁃	- **ROI Multiplication**: 100x+ vs manual approaches
	⁃	### **Continuous Improvement Loop**
	⁃	- **Performance Monitoring**: Real-time metrics and SLA compliance
	⁃	- **User Interaction Learning**: Adapt based on outcomes and feedback
	⁃	**Agent Evolution**: Improve collective intelligence over time
	⁃	**Knowledge Synthesis**: Build comprehensive understanding across domains
	⁃	**First Principles Analysis**: Fundamental process understanding
	⁃	**Sequential Thinking**: Logical progression with validation points
	⁃	**Interconnected Systems**: Leverage unrelated aspects for innovation
	⁃	**Market Reality Check**: Validate against demand, evolution, scarcity
	⁃	**Gap Analysis**: Why hasn’t this been solved before?
	⁃	**Data Integration**: Connect multiple enterprise sources via MCP
	⁃	**Knowledge Synthesis**: Specialized agents process by expertise domain
	⁃	**Decision Recommendations**: Actionable insights from multi-perspective analysis
	⁃	**Continuous Learning**: Framework improves through user interaction observation
	⁃	**Security First**: Permission-based access, audit trails, encryption
	⁃	**Performance Optimization**: Caching, rate limiting, load distribution
	⁃	**Scalability Planning**: Multi-tenancy, enterprise features, API monetization
	⁃	**Commercial Integration**: Billing, team collaboration, private repositories
	⁃	**Immediate Value Delivery**: Reduce knowledge worker time by >95% while providing more comprehensive analysis than single-agent solutions
	⁃	**Strategic Advantage**: Coordinated intelligence via messaging bus makes this approach superior to isolated AI tools
