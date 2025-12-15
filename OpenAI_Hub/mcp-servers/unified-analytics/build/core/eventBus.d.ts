/// <reference types="node" />
import EventEmitter from 'events';
export declare class EventBus extends EventEmitter {
    constructor();
    /**
     * Emit a metric event with data
     */
    emitMetric(name: string, data: any): void;
    /**
     * Listen for specific metric events
     */
    onMetric(name: string, handler: (data: any) => void): void;
}
