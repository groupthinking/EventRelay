import EventEmitter from 'events';

export class EventBus extends EventEmitter {
  constructor() {
    super();
    this.setMaxListeners(20); // Increase default limit for our many metric events
  }

  /**
   * Emit a metric event with data
   */
  emitMetric(name: string, data: any) {
    this.emit(`metric:${name}`, data);
  }

  /**
   * Listen for specific metric events
   */
  onMetric(name: string, handler: (data: any) => void) {
    this.on(`metric:${name}`, handler);
  }
}
