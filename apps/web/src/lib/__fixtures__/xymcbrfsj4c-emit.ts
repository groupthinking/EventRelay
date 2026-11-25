/**
 * Allowed emit slice for vp:v0:XYMcBrFSJ4c (live pack 200 on 2026-09-12).
 * Transcript + visual events + SOP requirements only.
 * architecture / code_snippets from that pack are held here solely so tests
 * can prove they are stripped — they must never reach App Builder files.
 * Do not substitute QjZ5ohr7sGA.
 */
export const XYMC_VIDEO_ID = "XYMcBrFSJ4c";
export const XYMC_PACK_ID = "vp:v0:XYMcBrFSJ4c";
export const XYMC_SOURCE_URL = "https://www.youtube.com/watch?v=XYMcBrFSJ4c";
export const XYMC_SOURCE_HASH = "b7d0ea083b1f8a6146fd6db818896ed09abfaa3f92babf976f5c209e07d3b959";

export const XYMC_TRANSCRIPT_TEXT =
  "So a friend of mine runs one AI automation that is simply so boring and almost embarrassed to describe it. And I can tell you that it makes more money than half of the flashy AI agents that you've probably seen on YouTube right now. All it does is that it takes a spreadsheet of unpaid invoices and it sends a polite follow-up email when one goes overdue. That's the whole thing. Which means that the AI services that actually pay aren't the ones that are exciting or even fancy. They are the boring, repetitive, no one wants to do jobs that businesses are already paying a human to handle. In this video, I'm going to give you the nine boring AI automations you can actually sell. Starting with number nine, which is inbox triage and email sorting. It watches and classifies emails, drafts replies, labels them, and sends Telegram alerts for urgent queries. Number eight: automatic invoice and payment follow-up using Stripe, Make, and Google Sheets to follow up overdue invoices on set cadences. Number seven: content repurposing engine, turning long-form video into social captions for Instagram, LinkedIn, and Twitter with AI-generated images. Number six: AI-personalized cold email system with Google Maps lead scraping, email verification, and dynamic icebreaker writing. Number five: AI lead generation agent, a website chatbot qualifying visitors and booking calls. Number four: speed-to-lead voice agent that dials inbound form submissions within 60 seconds to qualify and schedule appointments. Number three: lead reactivation voice agent calling cold CRM lists to book appointments. Number two: inbound AI receptionist handling customer calls, answering FAQs, and booking consultations 24/7. And number one: the fully systemized lead engine combining all inbound, outbound, voice, and reactivation systems into an end-to-end sales engine.";

export const XYMC_TRANSCRIPT = {
  language: "en" as const,
  full_text: XYMC_TRANSCRIPT_TEXT,
  segments: [
  {
    "idx": 0,
    "start_s": 0,
    "end_s": 26,
    "text": "Discussion on high-ROI boring AI automations versus flashy YouTube demos, introducing the invoice follow-up concept."
  },
  {
    "idx": 1,
    "start_s": 26,
    "end_s": 71,
    "text": "Personal background moving from investment banking to AI agency after zero initial earnings chasing complex shiny tools."
  },
  {
    "idx": 2,
    "start_s": 71,
    "end_s": 260,
    "text": "Automation 9: Inbox triage and email classification built in n8n with Gmail, OpenAI, drafts, and Telegram notifications."
  },
  {
    "idx": 3,
    "start_s": 260,
    "end_s": 425,
    "text": "Automation 8: Automated invoice and payment follow-up via Stripe webhooks, Google Sheets, and Make.com escalation emails."
  },
  {
    "idx": 4,
    "start_s": 425,
    "end_s": 665,
    "text": "Automation 7: Content repurposing engine using Apify YouTube scraper, prompt hubs, LLMs, and image generation in n8n."
  },
  {
    "idx": 5,
    "start_s": 665,
    "end_s": 890,
    "text": "Automation 6: AI-personalized cold outbound system with Google Maps lead scraping, AnyMail Finder, and AI icebreakers."
  },
  {
    "idx": 6,
    "start_s": 890,
    "end_s": 1085,
    "text": "Automation 5: AI website lead generation chatbot built on Voiceflow for qualification and meeting booking."
  },
  {
    "idx": 7,
    "start_s": 1085,
    "end_s": 1525,
    "text": "Automation 4: Speed-to-lead voice agent using Retell AI and n8n triggering phone calls within 60 seconds of form submission."
  },
  {
    "idx": 8,
    "start_s": 1525,
    "end_s": 1600,
    "text": "Automation 3: Lead reactivation voice agent calling dead CRM leads to re-qualify and book consultations."
  },
  {
    "idx": 9,
    "start_s": 1600,
    "end_s": 1900,
    "text": "Automation 2: 24/7 Inbound AI receptionist voice agent handling after-hours calls, qualification, and scheduling."
  },
  {
    "idx": 10,
    "start_s": 1900,
    "end_s": 2095,
    "text": "Automation 1: The fully systemized lead engine bundling all core automations into a recurring agency service."
  }
],
};

export const XYMC_VISUAL_EVENTS = [
  {
    "timestamp": 0,
    "element_type": "n8n_flow",
    "content": "Three-part email classifier workflow: trigger/classify, draft reply, alert team via Telegram"
  },
  {
    "timestamp": 0,
    "element_type": "make_router",
    "content": "Circular Make.com router triggering reminder drafts at 7, 14, 21, 28, 35, and 42 days overdue"
  },
  {
    "timestamp": 0,
    "element_type": "spreadsheet",
    "content": "Scraped lead table with populated custom icebreaker copy generated by LLM"
  },
  {
    "timestamp": 0,
    "element_type": "web_chat_widget",
    "content": "Torty Gym landing page displaying active Voiceflow AI assistant widget answering member questions"
  },
  {
    "timestamp": 0,
    "element_type": "calendar_ui",
    "content": "Google Calendar slot successfully booked during live phone conversation with Retell AI"
  }
];

export const XYMC_SOP_STEPS = [
  {
    "id": "REQ-001",
    "order": 1,
    "title": "Email Triage Workflow",
    "description": "Monitor inbox, classify intent with LLM, draft replies, and alert via Telegram on urgent matters."
  },
  {
    "id": "REQ-002",
    "order": 2,
    "title": "Invoice Payment Follow-Up",
    "description": "Track invoice statuses in Google Sheets; update on Stripe webhook; dispatch staggered reminder emails."
  },
  {
    "id": "REQ-003",
    "order": 3,
    "title": "Multi-Platform Content Repurposing",
    "description": "Transcribe long-form video, generate platform-specific drafts in Google Sheets, and generate thumbnail images."
  },
  {
    "id": "REQ-004",
    "order": 4,
    "title": "AI Cold Outbound Prospecting",
    "description": "Scrape local businesses, find verified decision-maker emails, and generate personalized website icebreakers."
  },
  {
    "id": "REQ-005",
    "order": 5,
    "title": "Sub-60s Speed-to-Lead Calling",
    "description": "Trigger outbound phone call via Retell AI upon web form submission, qualify caller, and book calendar event."
  },
  {
    "id": "REQ-006",
    "order": 6,
    "title": "24/7 AI Inbound Receptionist",
    "description": "Receive incoming calls via Twilio, extract case details, handle objections, and schedule consultations."
  }
];

export const XYMC_KEYFRAMES = [
  {
    "t_s": 11,
    "image_path": null,
    "desc": "Diagram showing CRM, AI Agent, and Client unpaid invoice follow-up flow"
  },
  {
    "t_s": 60,
    "image_path": null,
    "desc": "Grid of the 9 boring AI automations ranked by category"
  },
  {
    "t_s": 102,
    "image_path": null,
    "desc": "n8n workflow editor for email triage and automated classification"
  },
  {
    "t_s": 328,
    "image_path": null,
    "desc": "Make.com scenario syncing Stripe customer events with Google Sheets"
  },
  {
    "t_s": 365,
    "image_path": null,
    "desc": "Make.com router branching delayed follow-up emails across 7 to 42 days"
  },
  {
    "t_s": 465,
    "image_path": null,
    "desc": "n8n pipeline transcribing YouTube video and generating multi-platform posts"
  },
  {
    "t_s": 670,
    "image_path": null,
    "desc": "n8n workflow for Google Maps scraping, email finding, and icebreaker synthesis"
  },
  {
    "t_s": 950,
    "image_path": null,
    "desc": "Voiceflow canvas configuring gym AI concierge agent instructions and playbooks"
  },
  {
    "t_s": 1210,
    "image_path": null,
    "desc": "Retell AI dashboard defining outbound speed-to-lead agent voice persona and calendar functions"
  },
  {
    "t_s": 1270,
    "image_path": null,
    "desc": "Live call demonstration of Retell AI agent qualifying solar customer and booking calendar slot"
  },
  {
    "t_s": 1680,
    "image_path": null,
    "desc": "Retell AI inbound legal receptionist test call qualifying divorce custody lead"
  },
  {
    "t_s": 1850,
    "image_path": null,
    "desc": "Architecture overview of the fully systemized lead engine combining all 5 core modules"
  }
];

/** Live pack invented these. Emit must drop them. */
export const XYMC_FORBIDDEN_ARCHITECTURE = {
  "summary": "Modular agency architecture connecting lead capture, outbound outreach, automated triage, and conversational voice agents with Google Sheets and Calendar backends.",
  "stages": [
    {
      "id": "capture",
      "name": "Inbound & Outbound Capture",
      "description": "Scrapes prospects or receives web form/chat leads and pushes to central storage."
    },
    {
      "id": "voice_dispatch",
      "name": "Conversational Telephony",
      "description": "Retell AI initiates outbound speed-to-lead calls or handles incoming receptionist calls."
    },
    {
      "id": "triage_followup",
      "name": "Asynchronous Operations",
      "description": "n8n and Make scenarios automate email classification and payment collection routines."
    },
    {
      "id": "conversion",
      "name": "Booking & Handoff",
      "description": "Direct appointment booking to Google Calendar / CRM with human-in-the-loop escalation."
    }
  ],
  "mermaid": "graph TD\n  Form[Web Form / Ad Lead] -->|Webhook| N8N[n8n Automation]\n  N8N -->|POST /call| Retell[Retell AI Voice Agent]\n  Retell -->|Qualify Caller| User((Lead Phone))\n  Retell -->|Tool Call: Book| GCal[(Google Calendar)]\n  Sheets[(Google Sheets DB)] -->|Cron Trigger| Make[Make.com Router]\n  Make -->|Escalated Email| Invoices[Overdue Client Email]\n  Stripe[Stripe Events] -->|Webhook| Make"
};

export const XYMC_FORBIDDEN_CODE_SNIPPETS = [
  {
    "path_hint": "workflows/email_triage.ts",
    "lang": "typescript",
    "content": "export interface EmailClassification {\n  priority: 'High' | 'Normal' | 'Low';\n  category: 'Customer Support' | 'Promotion' | 'Finance/Billing' | 'General';\n  isUrgent: boolean;\n  suggestedDraft: string;\n}\nexport declare function classifyEmail(subject: string, body: string): Promise<EmailClassification>;"
  },
  {
    "path_hint": "integrations/retell_voice.ts",
    "lang": "typescript",
    "content": "export interface OutboundCallPayload {\n  agent_id: string;\n  to_number: string;\n  from_number: string;\n  retell_llm_dynamic_variables: Record<string, string>;\n}\nexport declare function triggerSpeedToLeadCall(payload: OutboundCallPayload): Promise<{ call_id: string }>;"
  },
  {
    "path_hint": "services/calendar_tool.ts",
    "lang": "typescript",
    "content": "export interface BookingRequest {\n  lead_name: string;\n  lead_email: string;\n  slot_iso: string;\n  notes: string;\n}\nexport declare function bookCalendarAppointment(req: BookingRequest): Promise<{ success: boolean; event_id: string }>;"
  }
];
