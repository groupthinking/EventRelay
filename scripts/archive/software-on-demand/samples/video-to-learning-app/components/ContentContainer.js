"use strict";
/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
*/
/* tslint:disable */
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const react_1 = __importDefault(require("@monaco-editor/react"));
const react_2 = __importStar(require("react"));
const react_tabs_1 = require("react-tabs");
// import 'react-tabs/style/react-tabs.css'
const parse_1 = require("@/lib/parse");
const prompts_1 = require("@/lib/prompts");
const textGeneration_1 = require("@/lib/textGeneration");
// Export the ContentContainer component as a forwardRef component
exports.default = (0, react_2.forwardRef)(function ContentContainer({ contentBasis, preSeededSpec, preSeededCode, onLoadingStateChange, }, ref) {
    const [spec, setSpec] = (0, react_2.useState)(preSeededSpec || '');
    const [code, setCode] = (0, react_2.useState)(preSeededCode || '');
    const [iframeKey, setIframeKey] = (0, react_2.useState)(0);
    const [saveMessage, setSaveMessage] = (0, react_2.useState)('');
    const [loadingState, setLoadingState] = (0, react_2.useState)(preSeededSpec && preSeededCode ? 'ready' : 'loading-spec');
    const [error, setError] = (0, react_2.useState)(null);
    const [isEditingSpec, setIsEditingSpec] = (0, react_2.useState)(false);
    const [editedSpec, setEditedSpec] = (0, react_2.useState)('');
    const [activeTabIndex, setActiveTabIndex] = (0, react_2.useState)(0); // 0: Render, 1: Code, 2: Spec
    // Expose methods to the parent component through ref
    (0, react_2.useImperativeHandle)(ref, () => ({
        getSpec: () => spec,
        getCode: () => code,
    }));
    // Helper function to generate content spec from video
    const generateSpecFromVideo = async (videoUrl) => {
        const specResponse = await (0, textGeneration_1.generateText)({
            modelName: 'gemini-2.5-flash',
            prompt: prompts_1.SPEC_FROM_VIDEO_PROMPT,
            videoUrl: videoUrl,
        });
        let spec = (0, parse_1.parseJSON)(specResponse).spec;
        spec += prompts_1.SPEC_ADDENDUM;
        return spec;
    };
    // Helper function to generate code from content spec
    const generateCodeFromSpec = async (spec) => {
        const codeResponse = await (0, textGeneration_1.generateText)({
            modelName: 'gemini-2.5-pro',
            prompt: spec,
        });
        const code = (0, parse_1.parseHTML)(codeResponse, prompts_1.CODE_REGION_OPENER, prompts_1.CODE_REGION_CLOSER);
        return code;
    };
    // Propagate loading state changes as a boolean
    (0, react_2.useEffect)(() => {
        if (onLoadingStateChange) {
            const isLoading = loadingState === 'loading-spec' || loadingState === 'loading-code';
            onLoadingStateChange(isLoading);
        }
    }, [loadingState, onLoadingStateChange]);
    // On mount (or when contentBasis changes), generate a content spec and then use that spec to generate code
    (0, react_2.useEffect)(() => {
        async function generateContent() {
            // If we have pre-seeded content, skip generation
            if (preSeededSpec && preSeededCode) {
                setSpec(preSeededSpec);
                setCode(preSeededCode);
                setLoadingState('ready');
                return;
            }
            try {
                // Reset states
                setLoadingState('loading-spec');
                setError(null);
                setSpec('');
                setCode('');
                // Generate a content spec based on video content
                const generatedSpec = await generateSpecFromVideo(contentBasis);
                setSpec(generatedSpec);
                setLoadingState('loading-code');
                // Generate code using the generated content spec
                const generatedCode = await generateCodeFromSpec(generatedSpec);
                setCode(generatedCode);
                setLoadingState('ready');
            }
            catch (err) {
                console.error('An error occurred while attempting to generate content:', err);
                setError(err instanceof Error ? err.message : 'An unknown error occurred');
                setLoadingState('error');
            }
        }
        generateContent();
    }, [contentBasis, preSeededSpec, preSeededCode]);
    // Re-render iframe when code changes
    (0, react_2.useEffect)(() => {
        if (code) {
            setIframeKey((prev) => prev + 1);
        }
    }, [code]);
    // Show save message when code changes manually (not during initial load)
    (0, react_2.useEffect)(() => {
        if (saveMessage) {
            const timer = setTimeout(() => {
                setSaveMessage('');
            }, 2000);
            return () => clearTimeout(timer);
        }
    }, [saveMessage]);
    const handleCodeChange = (value) => {
        setCode(value || '');
        setSaveMessage('HTML updated. Changes will appear in the Render tab.');
    };
    const handleSpecEdit = () => {
        setEditedSpec(spec);
        setIsEditingSpec(true);
    };
    const handleSpecSave = async () => {
        const trimmedEditedSpec = editedSpec.trim();
        // Only regenerate if the spec has actually changed
        if (trimmedEditedSpec === spec) {
            setIsEditingSpec(false); // Close the editor
            setEditedSpec(''); // Reset edited spec state
            return;
        }
        try {
            setLoadingState('loading-code');
            setError(null);
            setSpec(trimmedEditedSpec); // Update spec state with trimmed version
            setIsEditingSpec(false);
            setActiveTabIndex(1); // Switch to code tab
            // Generate code using the edited content spec
            const generatedCode = await generateCodeFromSpec(trimmedEditedSpec);
            setCode(generatedCode);
            setLoadingState('ready');
        }
        catch (err) {
            console.error('An error occurred while attempting to generate code:', err);
            setError(err instanceof Error ? err.message : 'An unknown error occurred');
            setLoadingState('error');
        }
    };
    const handleSpecCancel = () => {
        setIsEditingSpec(false);
        setEditedSpec('');
    };
    const renderLoadingSpinner = () => (<div style={{
            alignItems: 'center',
            color: '#666',
            display: 'flex',
            flexDirection: 'column',
            height: '100%',
            justifyContent: 'center',
            marginTop: '-2.5rem',
        }}>
      <div className="loading-spinner"></div>
      <p style={{
            color: 'light-dark(#787878, #f4f4f4)',
            fontSize: '1.125rem',
            marginTop: '20px',
        }}>
        {loadingState === 'loading-spec'
            ? 'Generating content spec from video...'
            : 'Generating code from content spec...'}
      </p>
    </div>);
    const renderErrorState = () => (<div style={{
            alignItems: 'center',
            color: 'var(--color-error)',
            display: 'flex',
            flexDirection: 'column',
            height: '100%',
            justifyContent: 'center',
            marginTop: '-2.5rem',
            textAlign: 'center',
        }}>
      <div style={{
            fontFamily: 'var(--font-symbols)',
            fontSize: '5rem',
        }}>
        error
      </div>
      <h3 style={{ fontSize: '1.5rem', marginBottom: '0.5rem' }}>Error</h3>
      <p>{error || 'Something went wrong'}</p>
      {!contentBasis.startsWith('http://') &&
            !contentBasis.startsWith('https://') ? (<p style={{ marginTop: '0.5rem' }}>
          (<strong>NOTE:</strong> URL must begin with http:// or https://)
        </p>) : null}
    </div>);
    // Styles for tab list
    const tabListStyle = {
        backgroundColor: 'transparent',
        display: 'flex',
        listStyle: 'none',
        margin: 0,
        padding: '0 12px',
    };
    // Styles for tabs
    const tabStyle = {
        borderTopLeftRadius: '4px',
        borderTopRightRadius: '4px',
        cursor: 'pointer',
        fontSize: '14px',
        marginRight: '4px',
        padding: '8px 12px',
    };
    // Base style for button container in spec tab
    const buttonContainerStyle = { padding: '0 1rem 1rem' };
    const renderSpecContent = () => {
        if (loadingState === 'error') {
            return spec ? (<div style={{
                    whiteSpace: 'pre-wrap',
                    fontFamily: 'var(--font-technical)',
                    lineHeight: 1.75,
                    flex: 1,
                    overflow: 'auto',
                    padding: '1rem 2rem',
                    maskImage: 'linear-gradient(to bottom, black 95%, transparent 100%)',
                    WebkitMaskImage: 'linear-gradient(to bottom, black 95%, transparent 100%)',
                }}>
          {spec}
        </div>) : (renderErrorState());
        }
        if (loadingState === 'loading-spec') {
            return renderLoadingSpinner();
        }
        if (isEditingSpec) {
            return (<div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
          <react_1.default height="100%" defaultLanguage="text" value={editedSpec} onChange={(value) => setEditedSpec(value || '')} theme="light" options={{
                    minimap: { enabled: false },
                    fontSize: 14,
                    wordWrap: 'on',
                    lineNumbers: 'off',
                }}/>
          <div style={{ display: 'flex', gap: '6px', ...buttonContainerStyle }}>
            <button onClick={handleSpecSave} className="button-primary">
              Save & regenerate code
            </button>
            <button onClick={handleSpecCancel} className="button-secondary">
              Cancel
            </button>
          </div>
        </div>);
        }
        return (<div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
        <div style={{
                whiteSpace: 'pre-wrap',
                fontFamily: 'var(--font-technical)',
                lineHeight: 1.75,
                flex: 1,
                overflow: 'auto',
                padding: '1rem 2rem',
                maskImage: 'linear-gradient(to bottom, black 95%, transparent 100%)',
                WebkitMaskImage: 'linear-gradient(to bottom, black 95%, transparent 100%)',
            }}>
          {spec}
        </div>
        <div style={buttonContainerStyle}>
          <button style={{ display: 'flex', alignItems: 'center', gap: '5px' }} onClick={handleSpecEdit} className="button-primary">
            Edit{' '}
            <span style={{
                fontFamily: 'var(--font-symbols)',
                fontSize: '1.125rem',
            }}>
              edit
            </span>
          </button>
        </div>
      </div>);
    };
    return (<div style={{
            border: '2px solid light-dark(#000, #fff)',
            borderRadius: '8px',
            boxSizing: 'border-box',
            display: 'flex',
            flexDirection: 'column',
            height: '100%',
            maxHeight: 'inherit',
            minHeight: 'inherit',
            overflow: 'hidden',
            position: 'relative',
        }}>
      <react_tabs_1.Tabs style={{
            bottom: 0,
            display: 'flex',
            flexDirection: 'column',
            height: '100%',
            left: 0,
            position: 'absolute',
            right: 0,
            top: 0,
        }} selectedIndex={activeTabIndex} onSelect={(index) => {
            // If currently editing spec and switching away from spec tab
            if (isEditingSpec && index !== 2) {
                setIsEditingSpec(false); // Exit edit mode
                setEditedSpec(''); // Clear edited content
            }
            setActiveTabIndex(index); // Update the active tab index
        }}>
        <react_tabs_1.TabList style={tabListStyle}>
          <react_tabs_1.Tab style={tabStyle} selectedClassName="selected-tab">
            Render
          </react_tabs_1.Tab>
          <react_tabs_1.Tab style={tabStyle} selectedClassName="selected-tab">
            Code
          </react_tabs_1.Tab>
          <react_tabs_1.Tab style={tabStyle} selectedClassName="selected-tab">
            Spec
          </react_tabs_1.Tab>
        </react_tabs_1.TabList>

        <div style={{ flex: 1, overflow: 'hidden' }}>
          <react_tabs_1.TabPanel style={{ height: '100%', padding: '0' }}>
            {loadingState === 'error' ? (renderErrorState()) : loadingState !== 'ready' ? (renderLoadingSpinner()) : (<div style={{ height: '100%', width: '100%', position: 'relative' }}>
                <iframe key={iframeKey} srcDoc={code} style={{
                border: 'none',
                width: '100%',
                height: '100%',
            }} title="rendered-html" sandbox="allow-scripts"/>
              </div>)}
          </react_tabs_1.TabPanel>

          <react_tabs_1.TabPanel style={{ height: '100%', padding: '0' }}>
            {loadingState === 'error' ? (renderErrorState()) : loadingState !== 'ready' ? (renderLoadingSpinner()) : (<div style={{ height: '100%', position: 'relative' }}>
                <react_1.default height="100%" defaultLanguage="html" value={code} onChange={handleCodeChange} theme="vs-dark" options={{
                minimap: { enabled: false },
                fontSize: 14,
                wordWrap: 'on',
                formatOnPaste: true,
                formatOnType: true,
            }}/>
                {saveMessage && (<div style={{
                    position: 'absolute',
                    bottom: '10px',
                    right: '10px',
                    background: 'rgba(0,0,0,0.7)',
                    color: 'white',
                    padding: '5px 10px',
                    borderRadius: '4px',
                    fontSize: '12px',
                }}>
                    {saveMessage}
                  </div>)}
              </div>)}
          </react_tabs_1.TabPanel>

          <react_tabs_1.TabPanel style={{
            height: '100%',
            padding: '1rem',
            overflow: 'auto',
            boxSizing: 'border-box',
        }}>
            {renderSpecContent()}
          </react_tabs_1.TabPanel>
        </div>
      </react_tabs_1.Tabs>

      <style>{`
        .selected-tab {
          background: light-dark(#f0f0f0, #fff);
          color: light-dark(#000, var(--color-background));
          font-weight: bold;
        }

        .react-tabs {
          width: 100%;
        }

        .react-tabs__tab-panel {
          border-top: 1px solid light-dark(#000, #fff);
        }

        .loading-spinner {
          animation: spin 1s ease-in-out infinite;
          border: 3px solid rgba(0, 0, 0, 0.1);
          border-radius: 50%;
          border-top-color: var(--color-accent);
          height: 60px;
          width: 60px;
        }

        @keyframes spin {
          to {
            transform: rotate(360deg);
          }
        }
      `}</style>
    </div>);
});
//# sourceMappingURL=ContentContainer.js.map