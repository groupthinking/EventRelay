/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
*/
import { Example } from '@/lib/types';
import { type Dispatch, type SetStateAction } from 'react';
export interface Data {
    examples: Example[];
    setExamples: Dispatch<SetStateAction<Example[]>>;
    defaultExample: Example;
    isLoading: boolean;
}
export declare const DataContext: import("react").Context<Data>;
