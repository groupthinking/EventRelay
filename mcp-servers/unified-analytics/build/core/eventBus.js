import EventEmitter from 'events';
export class EventBus extends EventEmitter {
    constructor() {
        super();
        this.setMaxListeners(20); // Increase default limit for our many metric events
    }
    /**
     * Emit a metric event with data
     */
    emitMetric(name, data) {
        this.emit(`metric:${name}`, data);
    }
    /**
     * Listen for specific metric events
     */
    onMetric(name, handler) {
        this.on(`metric:${name}`, handler);
    }
}
//# sourceMappingURL=eventBus.js.map