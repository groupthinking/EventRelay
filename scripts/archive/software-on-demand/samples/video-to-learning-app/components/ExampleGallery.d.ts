/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
*/
import { Example } from '@/lib/types';
interface ExampleGalleryProps {
    title?: string;
    selectedExample: Example | null;
    onSelectExample: (example: Example) => void;
}
export default function ExampleGallery({ title, selectedExample, onSelectExample, }: ExampleGalleryProps): import("react").JSX.Element;
export {};
