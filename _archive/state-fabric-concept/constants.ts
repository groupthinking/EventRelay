
import { LayerDefinition, GuidingPrinciple, CrossCuttingConcern, ImplementationPhase, SuccessCriterion } from './types';

export const APP_TITLE = "Universal Contextually-Aware State Continuity Fabric";

export const STRATEGIC_VISION_TITLE = "Strategic Vision";
export const STRATEGIC_VISION_CONTENT: string = "We are creating a **Universal Contextually-Aware State Continuity Fabric**, a revolutionary architecture that combines versatile orchestration (e.g., via MCP) with our innovative state management capabilities. This Fabric enables intelligent, seamless, and continuous user experiences across diverse applications, devices, and domains, transcending the limitations of siloed application state.";

export const GUIDING_PRINCIPLES_TITLE = "Guiding Principles";
export const GUIDING_PRINCIPLES_DATA: GuidingPrinciple[] = [
  {
    id: "gp1",
    title: "Orchestration-Centric Philosophy",
    points: [
      "A designated orchestration mechanism (e.g., MCP) serves as a central coordination point for services interacting with the Fabric.",
      "Client applications and integrations leverage the Fabric to enhance, not silo, user experiences.",
      "Seamless integration with evolving orchestration ecosystems and service landscapes."
    ]
  },
  {
    id: "gp2",
    title: "Distributed Intelligence & State Equilibrium",
    points: [
      "Processing and state management prioritize edge/client environments for performance, privacy, and responsiveness.",
      "Cloud capabilities extend and augment the Fabric when advantageous for scale, complex computation, or shared intelligence.",
      "State flows seamlessly and securely between environments, maintaining consistency."
    ]
  },
  {
    id: "gp3",
    title: "Progressive Enhancement & Adaptability Discipline",
    points: [
      "Core Fabric functionality ensures state continuity and basic contextual awareness in all integrated environments.",
      "Advanced capabilities (e.g., deep learning-based intent recognition) activate when supported by the client platform and user consent.",
      "Graceful degradation of non-essential features when resources are constrained or specific integrations are unavailable."
    ]
  },
  {
    id: "gp4",
    title: "Intelligent Resource Governance",
    points: [
      "Continuous monitoring of resource usage across integrated clients and backend services.",
      "Dynamic adaptation of Fabric behavior (e.g., synchronization frequency, data granularity) based on available resources and network conditions.",
      "Predictive optimization of resource allocation for state management and contextual processing."
    ]
  },
  {
    id: "gp5",
    title: "User-Centric Security & Privacy Model",
    points: [
      "User privacy preferences and consent fundamentally drive system behavior and data handling.",
      "Transparent operation with clear visibility for users into how their state and context are managed.",
      "Capability-based access control for services and applications interacting with the Fabric and user state.",
      "Robust cross-domain security policies ensuring data integrity and confidentiality."
    ]
  }
];

export const LAYERED_ARCHITECTURE_TITLE = "Layered Architecture";
export const LAYERED_ARCHITECTURE_INTRO = "Our Fabric's architecture consists of five integrated layers that work together:";

export const LAYERS_DATA: LayerDefinition[] = [
  {
    id: "clientIntegration",
    title: "Client Integration Layer",
    subtitle: "(Applications: Web, Mobile, Desktop, Extensions)",
    points: [
      "Adaptive UI Components", "Context-Aware Suggestions",
      "Rich Content Presentation", "User Input Handling",
      "Local Context Capture", "Fabric API Consumption"
    ],
    connectionTextAfter: "(Fabric APIs & SDKs)",
  },
  {
    id: "orchestration",
    title: "Orchestration Layer",
    points: [
      "Service Registry (e.g. MCP)", "Capability Discovery",
      "Request Routing", "Cross-Service Coordination",
      "Task Execution", "Resource Management"
    ],
  },
  {
    id: "intelligence",
    title: "Intelligence Layer",
    points: [
      "Universal Contextual Graph", "Intent Recognition",
      "Multi-Source Data Analysis", "Query/Action Enhancement",
      "Privacy Boundary Mgmt.", "Adaptive Learning Models"
    ],
  },
  {
    id: "continuity",
    title: "Continuity Layer (THE FABRIC CORE)",
    points: [
      "Differential State Engine", "Vector Clock Synchronization",
      "Encrypted State Transfer", "Multi-Domain Conflict Resol.",
      "Adaptive Persistence", "Cross-Application/Device ID",
      "State Transformation", "Schema Versioning"
    ],
  },
  {
    id: "foundationPlatform",
    title: "Foundation & Platform Layer",
    points: [
      "Platform Abstraction APIs", "Authentication/Authorization",
      "Storage Abstraction", "Secure Network Communication",
      "Capability Detection", "Telemetry & Observability",
      "SDKs for various platforms", "Multi-Domain Identity Mgmt."
    ],
  }
];

export const LAYER_DESCRIPTIONS_TITLE = "Layer Descriptions";
export const LAYER_DESCRIPTIONS_DATA = [
    {
        id: "ld1",
        title: "1. Client Integration Layer (formerly Experience Layer)",
        content: "This layer represents the various applications and environments that integrate with the State Continuity Fabric. It focuses on:\n- Capturing local context relevant to the application (e.g., current document, user activity, sensor data).\n- Utilizing Fabric APIs/SDKs to send and receive state and contextual information.\n- Rendering user interfaces and experiences informed by the Fabric's intelligence and continuous state.\n- Examples: Browser extensions, web applications, mobile apps, desktop software, IoT device firmware."
    },
    {
        id: "ld2",
        title: "2. Orchestration Layer",
        content: "The Orchestration Layer serves as the central nervous system, coordinating interactions between various services, the Fabric's core, and integrated client applications. It focuses on:\n- Managing connections and interactions with diverse services (e.g., MCP-managed services, third-party APIs).\n- Discovering and mapping available capabilities across the ecosystem.\n- Routing requests and data flows to appropriate services or Fabric layers."
    },
    {
        id: "ld3",
        title: "3. Intelligence Layer",
        content: "The Intelligence Layer provides the contextual understanding that powers the Fabric's value. It focuses on:\n- Aggregating and analyzing context from multiple sources (various client integrations, services).\n- Building a Universal Contextual Graph representing entities, relationships, and user activities across domains.\n- Recognizing user intent and enhancing queries or actions with rich contextual data.\n- Managing privacy boundaries for contextual data processing and sharing."
    },
    {
        id: "ld4",
        title: "4. Continuity Layer (The Fabric Core)",
        content: "The Continuity Layer *is* the State Continuity Fabric. It enables seamless and consistent experiences across diverse applications, sessions, devices, and domains. It focuses on:\n- Capturing, synchronizing, and merging differential state changes from various sources.\n- Providing encrypted, privacy-preserving state transfer and storage.\n- Resolving conflicts and ensuring data consistency across disparate systems using mechanisms like vector clocks.\n- Managing cross-application and cross-device identity securely.\n- Adapting persistence strategies based on data sensitivity, volume, and platform capabilities.\n- Handling state transformation and schema versioning for long-term compatibility."
    },
    {
        id: "ld5",
        title: "5. Foundation & Platform Layer",
        content: "The Foundation Layer provides the essential, abstracted building blocks for the Fabric and its integrations. It focuses on:\n- Abstracting platform-specific APIs (e.g., OS-level functions, browser APIs, mobile SDKs).\n- Managing robust authentication, authorization, and identity across multiple domains.\n- Providing secure and abstracted storage and network communication primitives.\n- Offering SDKs to simplify integration of the Fabric into diverse client applications and platforms.\n- Collecting telemetry for performance monitoring, diagnostics, and operational health."
    }
];


export const CROSS_CUTTING_CONCERNS_TITLE = "Cross-Cutting Concerns";
export const CROSS_CUTTING_CONCERNS_INTRO = "These remain critical and are even more important in a universal, multi-domain context:";
export const CROSS_CUTTING_CONCERNS_DATA: CrossCuttingConcern[] = [
  {
    id: "ccc1",
    title: "Security & Privacy",
    points: [
      "End-to-end encryption for all state and sensitive contextual data in transit and at rest.",
      "Granular, explicit user consent for data collection, processing, and sharing across domains.",
      "Strong privacy boundaries and data minimization principles.",
      "Secure identity management and federated trust mechanisms for cross-domain operations."
    ]
  },
  {
    id: "ccc2",
    title: "Performance",
    points: [
      "Adaptive resource usage optimized for diverse client capabilities (from IoT to powerful desktops).",
      "Highly efficient and low-latency state synchronization algorithms.",
      "Scalable backend infrastructure for the Continuity and Intelligence layers."
    ]
  },
  {
    id: "ccc3",
    title: "Error Handling & Resilience",
    points: [
      "Graceful degradation and fault tolerance across a distributed system.",
      "Comprehensive distributed tracing, logging, and diagnostics.",
      "Robust conflict resolution and data recovery mechanisms."
    ]
  },
  {
    id: "ccc4",
    title: "Accessibility & Inclusivity",
    points: [
      "Ensuring that experiences enabled by the Fabric are accessible when rendered in client applications.",
      "Providing guidance and tools within SDKs to promote accessible design."
    ]
  }
];

export const IMPLEMENTATION_STRATEGY_TITLE = "Implementation Strategy (Revised for a Fabric)";
export const IMPLEMENTATION_STRATEGY_DATA: ImplementationPhase[] = [
  {
    id: "is1",
    title: "Phase 1: Core Fabric & Orchestration Foundation",
    details: [
      "Develop the core Continuity Layer: differential state engine, synchronization, basic persistence.",
      "Establish core Orchestration Layer: service registry, basic request routing.",
      "Define initial Fabric APIs and data models."
    ]
  },
  {
    id: "is2",
    title: "Phase 2: Initial Platform SDK & Contextual Intelligence",
    details: [
      "Implement the Foundation & Platform Layer: key abstractions, auth/authz basics.",
      "Develop a primary SDK (e.g., Web SDK for browser extensions and web apps).",
      "Build foundational Intelligence Layer capabilities: basic contextual variable system, initial data analysis.",
      "Create a reference client application (e.g., a browser extension or a web app) to validate the Fabric."
    ]
  },
  {
    id: "is3",
    title: "Phase 3: Expanding Platform Support & Advanced Intelligence",
    details: [
      "Develop SDKs for other key platforms (e.g., mobile - iOS/Android, desktop).",
      "Enhance Intelligence Layer: intent recognition, multi-source context aggregation, adaptive learning.",
      "Refine multi-domain identity and conflict resolution in the Continuity Layer."
    ]
  },
  {
    id: "is4",
    title: "Phase 4: Ecosystem Enablement & Edge-Cloud Optimization",
    details: [
      "Develop tools and documentation for third-party developers to integrate with the Fabric.",
      "Implement advanced Edge-Cloud Continuum strategies for processing and state.",
      "Optimize resource governance and scalability."
    ]
  },
  {
    id: "is5",
    title: "Phase 5: Maturation & Specialized Use Cases",
    details: [
      "Enhance security protocols for complex multi-domain trust scenarios.",
      "Optimize performance across all layers and platforms.",
      "Explore specialized versions or configurations of the Fabric for specific industries or use cases."
    ]
  }
];

export const SUCCESS_CRITERIA_TITLE = "Success Criteria (Revised)";
export const SUCCESS_CRITERIA_DATA: SuccessCriterion[] = [
  {
    id: "sc1",
    title: "Adoption & Integration Metrics",
    points: [
      "Number of distinct applications/platforms successfully integrating the Fabric.",
      "Time-to-integrate for new client applications (developer experience).",
      "Active user base experiencing continuous state across multiple touchpoints."
    ]
  },
  {
    id: "sc2",
    title: "Continuity & Contextual Relevance Metrics",
    points: [
      "State synchronization latency and success rates across diverse devices/networks.",
      "Accuracy and relevance of context-aware suggestions/actions powered by the Fabric.",
      "User-perceived seamlessness of transitions between applications/devices."
    ]
  },
  {
    id: "sc3",
    title: "Technical Quality & Scalability Metrics",
    points: [
      "Architectural compliance and modularity of the Fabric components.",
      "Test coverage (>90% for core Fabric layers).",
      "Zero critical security vulnerabilities across the Fabric and SDKs.",
      "Scalability of the Continuity and Intelligence layers to support a growing number of users, devices, and data volume.",
      "Efficiency of resource utilization (CPU, memory, network) on client devices and backend infrastructure."
    ]
  },
  {
    id: "sc4",
    title: "User Trust & Privacy Metrics",
    points: [
      "User opt-in rates for advanced contextual features.",
      "Successful audits for privacy compliance (e.g., GDPR, CCPA).",
      "User satisfaction with transparency and control over their data."
    ]
  }
];
