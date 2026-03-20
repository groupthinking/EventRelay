/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
*/
import React from 'react';
interface ContentContainerProps {
    contentBasis: string;
    preSeededSpec?: string;
    preSeededCode?: string;
    onLoadingStateChange?: (isLoading: boolean) => void;
}
declare const _default: React.ForwardRefExoticComponent<ContentContainerProps & React.RefAttributes<unknown>>;
export default _default;
