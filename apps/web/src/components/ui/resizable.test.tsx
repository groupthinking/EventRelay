import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from './resizable';

describe('Resizable primitives', () => {
  it.each(['horizontal', 'vertical'] as const)(
    'renders a %s group with the installed panel API',
    (orientation) => {
      const html = renderToStaticMarkup(
        <ResizablePanelGroup orientation={orientation} className="custom-group">
          <ResizablePanel id="chat" defaultSize="40%">Chat</ResizablePanel>
          <ResizableHandle id="resize" withHandle className="custom-handle" />
          <ResizablePanel id="preview" defaultSize="60%">Preview</ResizablePanel>
        </ResizablePanelGroup>,
      );

      expect(html).toContain('Chat');
      expect(html).toContain('Preview');
      expect(html).toContain('data-group');
      expect(html).toContain('data-panel');
      expect(html).toContain('data-separator');
      expect(html).toContain('role="separator"');
      expect(html).toContain('tabindex="0"');
      expect(html).toContain(`flex-direction:${orientation === 'vertical' ? 'column' : 'row'}`);
      expect(html).toContain(`aria-orientation="${orientation === 'vertical' ? 'horizontal' : 'vertical'}"`);
      expect(html).not.toContain('data-panel-group-direction');
      expect(html).toContain('custom-group');
      expect(html).toContain('custom-handle');
      expect(html).toContain('<svg');
    },
  );

  it('renders a plain separator without a grip by default', () => {
    const html = renderToStaticMarkup(
      <ResizablePanelGroup>
        <ResizablePanel>Chat</ResizablePanel>
        <ResizableHandle />
        <ResizablePanel>Preview</ResizablePanel>
      </ResizablePanelGroup>,
    );

    expect(html).toContain('role="separator"');
    expect(html).not.toContain('<svg');
  });
});
