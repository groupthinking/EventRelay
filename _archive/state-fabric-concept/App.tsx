
import React from 'react';
import {
  APP_TITLE,
  STRATEGIC_VISION_TITLE, STRATEGIC_VISION_CONTENT,
  GUIDING_PRINCIPLES_TITLE, GUIDING_PRINCIPLES_DATA,
  LAYERED_ARCHITECTURE_TITLE, LAYERED_ARCHITECTURE_INTRO, LAYERS_DATA,
  LAYER_DESCRIPTIONS_TITLE, LAYER_DESCRIPTIONS_DATA,
  CROSS_CUTTING_CONCERNS_TITLE, CROSS_CUTTING_CONCERNS_INTRO, CROSS_CUTTING_CONCERNS_DATA,
  IMPLEMENTATION_STRATEGY_TITLE, IMPLEMENTATION_STRATEGY_DATA,
  SUCCESS_CRITERIA_TITLE, SUCCESS_CRITERIA_DATA
} from './constants';
import Section from './components/Section';
import LayerCard from './components/LayerCard';
import { GuidingPrinciple, CrossCuttingConcern, ImplementationPhase, SuccessCriterion } from './types';

// Helper to parse markdown-like bold text
const FormattedText: React.FC<{ text: string }> = ({ text }) => {
  const parts = text.split(/(\*\*.*?\*\*)/g); // Split by **bolded** parts
  return (
    <>
      {parts.map((part, index) => {
        if (part.startsWith('**') && part.endsWith('**')) {
          return <strong key={index} className="font-semibold text-slate-900">{part.slice(2, -2)}</strong>;
        }
        return <React.Fragment key={index}>{part}</React.Fragment>;
      })}
    </>
  );
};

const App: React.FC = () => {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-100 via-gray-100 to-slate-200 text-slate-800 p-4 md:p-8 font-sans leading-relaxed">
      <header className="text-center mb-12 md:mb-16">
        <h1 className="text-4xl md:text-5xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-sky-600 to-teal-500 py-2">
          {APP_TITLE}
        </h1>
      </header>

      <main className="max-w-5xl mx-auto space-y-16">
        <Section title={STRATEGIC_VISION_TITLE}>
          <p className="text-lg text-slate-700">
            <FormattedText text={STRATEGIC_VISION_CONTENT} />
          </p>
        </Section>

        <Section title={GUIDING_PRINCIPLES_TITLE}>
          <div className="space-y-6">
            {GUIDING_PRINCIPLES_DATA.map((principle: GuidingPrinciple) => (
              <div key={principle.id} className="p-4 bg-white shadow-lg rounded-lg border border-slate-200">
                <h3 className="text-xl font-semibold text-sky-600 mb-2">{principle.title}</h3>
                <ul className="list-disc list-inside ml-4 space-y-1 text-slate-700">
                  {principle.points.map((point, index) => (
                    <li key={index}>{point}</li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </Section>

        <Section title={LAYERED_ARCHITECTURE_TITLE}>
          <p className="text-md text-slate-700 mb-8 text-center">{LAYERED_ARCHITECTURE_INTRO}</p>
          <div className="space-y-4">
            {LAYERS_DATA.map((layer, index) => (
              <React.Fragment key={layer.id}>
                <LayerCard layer={layer} />
                {index < LAYERS_DATA.length - 1 && (
                  <div className="flex flex-col items-center my-4 py-3">
                    <div className="text-4xl text-slate-400 transform ">▼</div>
                    {layer.connectionTextAfter && (
                      <div className="text-xs text-center text-slate-600 mt-2 px-3 py-1 bg-slate-200 rounded-full shadow-sm">
                        {layer.connectionTextAfter}
                      </div>
                    )}
                  </div>
                )}
              </React.Fragment>
            ))}
          </div>
        </Section>
        
        <Section title={LAYER_DESCRIPTIONS_TITLE}>
            {LAYER_DESCRIPTIONS_DATA.map(desc => (
                <div key={desc.id} className="mb-6 p-4 bg-white shadow-lg rounded-lg border border-slate-200">
                    <h3 className="text-xl font-semibold text-sky-600 mb-2">{desc.title}</h3>
                    <ul className="list-none space-y-1 text-slate-700">
                        {desc.content.split('\n').map((line, idx) => (
                            <li key={idx} className={line.startsWith('-') ? 'ml-4' : ''}>
                              {line.startsWith('-') ? <span className="text-sky-500 mr-2">&#9679;</span> : null}
                              {line.startsWith('-') ? line.substring(2) : line}
                            </li>
                        ))}
                    </ul>
                </div>
            ))}
        </Section>


        <Section title={CROSS_CUTTING_CONCERNS_TITLE}>
          <p className="text-md text-slate-700 mb-6">{CROSS_CUTTING_CONCERNS_INTRO}</p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {CROSS_CUTTING_CONCERNS_DATA.map((concern: CrossCuttingConcern) => (
              <div key={concern.id} className="p-4 bg-white shadow-lg rounded-lg border border-slate-200">
                <h3 className="text-xl font-semibold text-sky-600 mb-2">{concern.title}</h3>
                <ul className="list-disc list-inside ml-4 space-y-1 text-slate-700">
                  {concern.points.map((point, index) => (
                    <li key={index}>{point}</li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </Section>

        <Section title={IMPLEMENTATION_STRATEGY_TITLE}>
          <div className="space-y-6">
            {IMPLEMENTATION_STRATEGY_DATA.map((phase: ImplementationPhase) => (
              <div key={phase.id} className="p-4 bg-white shadow-lg rounded-lg border border-slate-200">
                <h3 className="text-xl font-semibold text-sky-600 mb-2">{phase.title}</h3>
                <ul className="list-disc list-inside ml-4 space-y-1 text-slate-700">
                  {phase.details.map((detail, index) => (
                    <li key={index}>{detail}</li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </Section>

        <Section title={SUCCESS_CRITERIA_TITLE} className="pb-8">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {SUCCESS_CRITERIA_DATA.map((criterion: SuccessCriterion) => (
              <div key={criterion.id} className="p-4 bg-white shadow-lg rounded-lg border border-slate-200">
                <h3 className="text-xl font-semibold text-sky-600 mb-2">{criterion.title}</h3>
                <ul className="list-disc list-inside ml-4 space-y-1 text-slate-700">
                  {criterion.points.map((point, index) => (
                    <li key={index}>{point}</li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </Section>
      </main>

      <footer className="text-center py-8 mt-12 border-t border-slate-300">
        <p className="text-sm text-slate-600">&copy; {new Date().getFullYear()} Fabric Vision. All rights reserved (conceptually).</p>
      </footer>
    </div>
  );
};

export default App;
