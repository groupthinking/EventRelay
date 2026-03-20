import { ButtonHTMLAttributes, HTMLAttributes } from 'react';
declare const SUGGESTED_TOPICS: {
    id: string;
    label: string;
    icon: string;
    gradient: string;
    borderColor: string;
    textColor: string;
    query: string;
}[];
type TopicChipBaseProps = Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'onSelect'>;
export interface TopicChipProps extends TopicChipBaseProps {
    topic: typeof SUGGESTED_TOPICS[0];
    onSelect?: (query: string) => void;
}
declare const TopicChip: import("react").ForwardRefExoticComponent<TopicChipProps & import("react").RefAttributes<HTMLButtonElement>>;
export interface SuggestedPromptsProps extends HTMLAttributes<HTMLDivElement> {
    onSelectTopic?: (query: string) => void;
    title?: string;
}
declare const SuggestedPrompts: import("react").ForwardRefExoticComponent<SuggestedPromptsProps & import("react").RefAttributes<HTMLDivElement>>;
export { SuggestedPrompts, TopicChip, SUGGESTED_TOPICS };
