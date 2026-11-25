/**
 * Allowed emit slice for vp:v0:QjZ5ohr7sGA (live pack 200 on 2026-09-12).
 * Transcript + visual events + SOP requirements only.
 * architecture / code_snippets from that pack are held here solely so tests
 * can prove they are stripped — they must never reach App Builder files.
 */
export const QJ_VIDEO_ID = 'QjZ5ohr7sGA';
export const QJ_PACK_ID = 'vp:v0:QjZ5ohr7sGA';
export const QJ_SOURCE_URL = 'https://www.youtube.com/watch?v=QjZ5ohr7sGA';
export const QJ_SOURCE_HASH = '0c351eae941cc151f9581ef22d9a0c7a585b75fe5e4aef890813a143c7a5fd8a';

export const QJ_TRANSCRIPT_TEXT =
  "The average American will experience five flat tires over the course of their motoring lifetime. But one in five American drivers doesn't even know how to change a tire. But don't worry, I got you. The three essential things you'll need are a jack, a lug wrench, and of course, a spare tire. You're also going to want to pull out your owner's manual. We're going to show you our best practices, but there's no substitute for your automaker's recommendations. Once you detect the flat, turn on your emergency flashers, slow down and find a safe level place to stop. Put your parking brake on to prevent a rollaway, and have passengers exit. Now remove your hubcaps if you have them, using a flat-headed tool. This may require a special tool, so consult your owner's manual to be sure. Loosen the lug nuts or bolts before jacking up the car. Give it all you've got to break the lugs loose, but don't loosen them much, just enough so you can take it easy once your car is on the jack. There are different kinds of jacks stored in different places in different kinds of cars, so again, familiarize yourself with your manual in advance. Place the jack on your manual's recommended jack point, often marked. The jack point will be a flat metal area of the car's frame near the flat tire, not the body, which won't likely support the car's weight. Jack up the car just enough to let you ultimately slide the tire off, and keep all body parts out from underneath the car while it's jacked up. Finish loosening the lugs and keep them in a safe place. Pull the flat tire off and replace it with your spare. Likely it will be a smaller temporary tire or a donut. Hand tighten the lugs, then give them a quarter turn with the wrench while the car is still jacked. Now lower the car slowly until the jack slides easily out, and finish tightening the lugs in a star pattern. Don't try to be Thor here, just tighten the lugs so that they feel equally snug and require some elbow grease to break loose again. And boom, you're back on your way. One more important thing to bear in mind: that temporary spare is just that, temporary. Most donuts aren't meant to be driven more than around 50 mph or 100 miles in distance. So do nut procrastinate; get it patched or replaced ASAP.";

export const QJ_TRANSCRIPT = {
  language: 'en' as const,
  full_text: QJ_TRANSCRIPT_TEXT,
  segments: [
    {
      idx: 0,
      start_s: 0,
      end_s: 9.8,
      text: "The average American will experience five flat tires over the course of their motoring lifetime. But one in five American drivers doesn't even know how to change a tire. But don't worry, I got you.",
    },
    {
      idx: 2,
      start_s: 21.8,
      end_s: 30.8,
      text: 'Once you detect the flat, turn on your emergency flashers, slow down and find a safe level place to stop. Put your parking brake on to prevent a rollaway, and have passengers exit.',
    },
    {
      idx: 8,
      start_s: 110,
      end_s: 118.8,
      text: 'Finish loosening the lugs and keep them in a safe place. Pull the flat tire off and replace it with your spare. Likely it will be a smaller temporary tire or a donut.',
    },
  ],
};

export const QJ_VISUAL_EVENTS = [
  {
    timestamp: 10.5,
    element_type: 'tools',
    content: 'Required tools: spare tire, scissor jack, and lug wrench',
  },
  {
    timestamp: 39,
    element_type: 'wheel',
    content: 'Loosening lug nuts with wrench while wheel is on ground',
  },
  {
    timestamp: 55,
    element_type: 'underbody',
    content: 'Aligning scissor jack to frame jack point',
  },
  {
    timestamp: 128,
    element_type: 'wheel_hub',
    content: 'Torquing lug nuts in star pattern on ground',
  },
];

export const QJ_SOP_STEPS = [
  {
    id: 'REQ-01',
    order: 1,
    title: 'Safety and Vehicle Staging',
    description:
      'Engage emergency flashers, park on flat ground, set parking brake, and exit passengers.',
    timestamp: 21.8,
  },
  {
    id: 'REQ-02',
    order: 2,
    title: 'Lug Loosening Before Elevation',
    description: 'Break lug nut friction with wrench prior to elevating vehicle with jack.',
    timestamp: 37.8,
  },
  {
    id: 'REQ-03',
    order: 3,
    title: 'Frame Point Jacking',
    description: 'Align jack with reinforced frame pinch weld, not cosmetic body panels.',
    timestamp: 53.6,
  },
  {
    id: 'REQ-04',
    order: 4,
    title: 'Star Pattern Torquing',
    description: 'Tighten wheel lugs evenly using a cross/star sequence after lowering.',
    timestamp: 123,
  },
  {
    id: 'REQ-05',
    order: 5,
    title: 'Spare Tire Operating Envelope',
    description: 'Restrict driving speed to 50 mph and range to 100 miles on donut spares.',
    timestamp: 134.8,
  },
];

/** Live pack invented these. Emit must drop them. */
export const QJ_FORBIDDEN_ARCHITECTURE = {
  summary: 'Procedural pipeline for roadside tire changing and validation.',
  stages: [{ id: 'stage_1', name: 'Vehicle Staging', description: 'Park safely.' }],
  mermaid: null,
};

export const QJ_FORBIDDEN_CODE_SNIPPETS = [
  {
    path_hint: 'tire_procedure.ts',
    lang: 'typescript',
    content:
      'export interface TireChangeContext { hazardsOn: boolean }\nexport function validatePreLiftSafety(ctx: TireChangeContext): boolean;',
  },
];
