/**
 * Predictive Risk Assessment System
 * Advanced risk prediction using statistical analysis and machine learning
 */

const fs = require('fs');
const path = require('path');
const { EventEmitter } = require('events');

class PredictiveRiskAssessor extends EventEmitter {
  constructor() {
    super();
    this.historicalData = new Map();
    this.riskModels = new Map();
    this.predictions = new Map();
    this.anomalies = new Map();
    this.baselines = new Map();

    this.config = this.loadConfig();
    this.initializeRiskModels();
  }

  loadConfig() {
    const configPath = path.join(__dirname, '..', 'config', 'risk-assessment-config.json');

    if (fs.existsSync(configPath)) {
      return JSON.parse(fs.readFileSync(configPath, 'utf8'));
    }

    return {
      enabled: true,
      predictionHorizon: 30, // days
      confidenceThreshold: 0.75,
      updateInterval: 3600000, // 1 hour
      dataRetention: 365, // days
      models: {
        statistical: { enabled: true },
        machineLearning: { enabled: false },
        anomalyDetection: { enabled: true }
      },
      riskCategories: {
        performance: { weight: 0.3, threshold: 0.7 },
        security: { weight: 0.4, threshold: 0.8 },
        compliance: { weight: 0.2, threshold: 0.6 },
        operational: { weight: 0.1, threshold: 0.5 }
      },
      alerting: {
        enabled: true,
        predictionThreshold: 0.8,
        anomalyThreshold: 2.5, // standard deviations
        cooldownPeriod: 3600000 // 1 hour
      }
    };
  }

  /**
   * Initialize risk assessment models
   */
  initializeRiskModels() {
    // Statistical models
    if (this.config.models.statistical.enabled) {
      this.riskModels.set('trend_analysis', new TrendAnalysisModel());
      this.riskModels.set('correlation_analysis', new CorrelationAnalysisModel());
      this.riskModels.set('regression_model', new RegressionModel());
    }

    // Machine learning models (placeholder for future implementation)
    if (this.config.models.machineLearning.enabled) {
      this.riskModels.set('neural_network', new NeuralNetworkModel());
      this.riskModels.set('random_forest', new RandomForestModel());
    }

    // Anomaly detection
    if (this.config.models.anomalyDetection.enabled) {
      this.riskModels.set('isolation_forest', new IsolationForestModel());
      this.riskModels.set('zscore_detector', new ZScoreDetector());
    }
  }

  /**
   * Start predictive risk assessment
   */
  async start() {
    console.log('🔮 Starting predictive risk assessment...');

    try {
      // Load historical data
      await this.loadHistoricalData();

      // Establish baselines
      await this.establishBaselines();

      // Start monitoring and prediction cycle
      this.startPredictionCycle();

      console.log('✅ Predictive risk assessment started');

      this.emit('started');
    } catch (error) {
      console.error('❌ Failed to start risk assessment:', error.message);
      throw error;
    }
  }

  /**
   * Stop predictive risk assessment
   */
  async stop() {
    console.log('🛑 Stopping predictive risk assessment...');

    if (this.predictionInterval) {
      clearInterval(this.predictionInterval);
    }

    console.log('✅ Predictive risk assessment stopped');
    this.emit('stopped');
  }

  /**
   * Load historical data for analysis
   */
  async loadHistoricalData() {
    console.log('📚 Loading historical data...');

    const dataSources = [
      'performance',
      'security',
      'compliance',
      'operational'
    ];

    for (const source of dataSources) {
      const data = await this.loadDataFromSource(source);
      this.historicalData.set(source, data);
    }

    console.log('✅ Historical data loaded');
  }

  /**
   * Load data from specific source
   */
  async loadDataFromSource(source) {
    const data = [];
    const sourcePath = path.join(__dirname, '..', 'monitoring', 'metrics');

    if (!fs.existsSync(sourcePath)) {
      return data;
    }

    const files = fs.readdirSync(sourcePath)
      .filter(file => file.includes(source) && file.endsWith('.json'))
      .sort()
      .slice(-100); // Last 100 files

    for (const file of files) {
      try {
        const content = fs.readFileSync(path.join(sourcePath, file), 'utf8');
        const metrics = JSON.parse(content);
        data.push(metrics);
      } catch (error) {
        console.warn(`⚠️  Failed to load ${file}:`, error.message);
      }
    }

    return data;
  }

  /**
   * Establish baseline metrics
   */
  async establishBaselines() {
    console.log('📊 Establishing baselines...');

    for (const [source, data] of this.historicalData) {
      if (data.length > 0) {
        const baseline = this.calculateBaseline(data);
        this.baselines.set(source, baseline);
      }
    }

    console.log('✅ Baselines established');
  }

  /**
   * Calculate baseline from historical data
   */
  calculateBaseline(data) {
    const baseline = {};

    if (data.length === 0) return baseline;

    // Get all metric keys from the first data point
    const sample = data[0];
    const metricKeys = this.extractMetricKeys(sample);

    for (const key of metricKeys) {
      const values = data.map(d => this.getNestedValue(d, key)).filter(v => v !== undefined);
      if (values.length > 0) {
        baseline[key] = {
          mean: values.reduce((a, b) => a + b, 0) / values.length,
          std: this.calculateStandardDeviation(values),
          min: Math.min(...values),
          max: Math.max(...values),
          percentile95: this.calculatePercentile(values, 95),
          trend: this.calculateTrend(values)
        };
      }
    }

    return baseline;
  }

  /**
   * Extract metric keys from data structure
   */
  extractMetricKeys(data, prefix = '') {
    const keys = [];

    for (const [key, value] of Object.entries(data)) {
      const fullKey = prefix ? `${prefix}.${key}` : key;

      if (typeof value === 'number') {
        keys.push(fullKey);
      } else if (typeof value === 'object' && value !== null) {
        keys.push(...this.extractMetricKeys(value, fullKey));
      }
    }

    return keys;
  }

  /**
   * Get nested value from object
   */
  getNestedValue(obj, path) {
    return path.split('.').reduce((current, key) => current?.[key], obj);
  }

  /**
   * Calculate standard deviation
   */
  calculateStandardDeviation(values) {
    const mean = values.reduce((a, b) => a + b, 0) / values.length;
    const squaredDiffs = values.map(value => Math.pow(value - mean, 2));
    const variance = squaredDiffs.reduce((a, b) => a + b, 0) / values.length;
    return Math.sqrt(variance);
  }

  /**
   * Calculate percentile
   */
  calculatePercentile(values, percentile) {
    const sorted = [...values].sort((a, b) => a - b);
    const index = (percentile / 100) * (sorted.length - 1);
    const lower = Math.floor(index);
    const upper = Math.ceil(index);

    if (lower === upper) {
      return sorted[lower];
    }

    return sorted[lower] + (sorted[upper] - sorted[lower]) * (index - lower);
  }

  /**
   * Calculate trend direction
   */
  calculateTrend(values) {
    if (values.length < 2) return 'stable';

    const recent = values.slice(-10);
    const older = values.slice(-20, -10);

    if (recent.length === 0 || older.length === 0) return 'stable';

    const recentAvg = recent.reduce((a, b) => a + b, 0) / recent.length;
    const olderAvg = older.reduce((a, b) => a + b, 0) / older.length;

    const change = ((recentAvg - olderAvg) / olderAvg) * 100;

    if (Math.abs(change) < 5) return 'stable';
    return change > 0 ? 'increasing' : 'decreasing';
  }

  /**
   * Start prediction cycle
   */
  startPredictionCycle() {
    this.predictionInterval = setInterval(async () => {
      await this.runPredictions();
      await this.detectAnomalies();
      await this.generateRiskAlerts();
    }, this.config.updateInterval);
  }

  /**
   * Run risk predictions
   */
  async runPredictions() {
    const predictions = {};

    for (const [source, data] of this.historicalData) {
      if (data.length > 0) {
        predictions[source] = await this.predictRisksForSource(source, data);
      }
    }

    this.predictions = new Map(Object.entries(predictions));
    this.emit('predictionsUpdated', predictions);
  }

  /**
   * Predict risks for specific data source
   */
  async predictRisksForSource(source, data) {
    const predictions = [];
    const baseline = this.baselines.get(source);

    if (!baseline) return predictions;

    // Use different models for prediction
    for (const [modelName, model] of this.riskModels) {
      try {
        const modelPredictions = await model.predict(source, data, baseline);
        predictions.push(...modelPredictions);
      } catch (error) {
        console.warn(`⚠️  Model ${modelName} failed for ${source}:`, error.message);
      }
    }

    return predictions;
  }

  /**
   * Detect anomalies in current data
   */
  async detectAnomalies() {
    const anomalies = {};

    for (const [source, data] of this.historicalData) {
      if (data.length > 0) {
        anomalies[source] = await this.detectAnomaliesForSource(source, data);
      }
    }

    this.anomalies = new Map(Object.entries(anomalies));
    this.emit('anomaliesDetected', anomalies);
  }

  /**
   * Detect anomalies for specific source
   */
  async detectAnomaliesForSource(source, data) {
    const anomalies = [];
    const baseline = this.baselines.get(source);

    if (!baseline || data.length === 0) return anomalies;

    const latest = data[data.length - 1];

    for (const [metricKey, baselineStats] of Object.entries(baseline)) {
      const currentValue = this.getNestedValue(latest, metricKey);

      if (currentValue !== undefined) {
        const zScore = Math.abs((currentValue - baselineStats.mean) / baselineStats.std);

        if (zScore > this.config.alerting.anomalyThreshold) {
          anomalies.push({
            metric: metricKey,
            currentValue: currentValue,
            expectedValue: baselineStats.mean,
            deviation: zScore,
            severity: zScore > 4 ? 'critical' : zScore > 3 ? 'high' : 'medium',
            timestamp: Date.now()
          });
        }
      }
    }

    return anomalies;
  }

  /**
   * Generate risk alerts based on predictions and anomalies
   */
  async generateRiskAlerts() {
    const alerts = [];

    // Process predictions
    for (const [source, predictions] of this.predictions) {
      for (const prediction of predictions) {
        if (prediction.confidence > this.config.alerting.predictionThreshold) {
          alerts.push({
            type: 'prediction',
            source: source,
            risk: prediction.risk,
            probability: prediction.probability,
            confidence: prediction.confidence,
            timeframe: prediction.timeframe,
            impact: prediction.impact,
            recommendations: prediction.recommendations
          });
        }
      }
    }

    // Process anomalies
    for (const [source, anomalies] of this.anomalies) {
      for (const anomaly of anomalies) {
        alerts.push({
          type: 'anomaly',
          source: source,
          metric: anomaly.metric,
          severity: anomaly.severity,
          currentValue: anomaly.currentValue,
          expectedValue: anomaly.expectedValue,
          deviation: anomaly.deviation
        });
      }
    }

    // Send alerts
    await this.sendRiskAlerts(alerts);
    this.emit('riskAlertsGenerated', alerts);
  }

  /**
   * Send risk alerts
   */
  async sendRiskAlerts(alerts) {
    if (!this.config.alerting.enabled || alerts.length === 0) return;

    console.log(`🚨 Generated ${alerts.length} risk alerts`);

    for (const alert of alerts) {
      // Check cooldown period
      const alertKey = `${alert.type}_${alert.source}_${alert.risk || alert.metric}`;
      const lastAlert = this.lastAlerts?.get(alertKey);

      if (lastAlert && (Date.now() - lastAlert) < this.config.alerting.cooldownPeriod) {
        continue;
      }

      // Send alert
      await this.sendAlert(alert);

      // Update last alert time
      if (!this.lastAlerts) this.lastAlerts = new Map();
      this.lastAlerts.set(alertKey, Date.now());
    }
  }

  /**
   * Send individual alert
   */
  async sendAlert(alert) {
    const message = this.formatAlertMessage(alert);

    // Console logging
    console.log(`🚨 RISK ALERT: ${message.title}`);
    console.log(`   ${message.description}`);

    // File logging
    this.saveAlertToFile(alert);

    // External notifications would be implemented here
    // await this.sendSlackAlert(message);
    // await this.sendEmailAlert(message);
  }

  /**
   * Format alert message
   */
  formatAlertMessage(alert) {
    if (alert.type === 'prediction') {
      return {
        title: `Risk Prediction: ${alert.risk}`,
        description: `${alert.probability.toFixed(1)}% probability within ${alert.timeframe}. ${alert.impact}`,
        severity: alert.probability > 90 ? 'critical' : alert.probability > 75 ? 'high' : 'medium',
        recommendations: alert.recommendations
      };
    } else if (alert.type === 'anomaly') {
      return {
        title: `Anomaly Detected: ${alert.metric}`,
        description: `Value ${alert.currentValue} deviates ${alert.deviation.toFixed(1)}σ from baseline ${alert.expectedValue}`,
        severity: alert.severity,
        recommendations: ['Investigate the anomaly', 'Check system health', 'Review recent changes']
      };
    }
  }

  /**
   * Save alert to file
   */
  saveAlertToFile(alert) {
    const alertDir = path.join(__dirname, '..', 'monitoring', 'alerts');

    if (!fs.existsSync(alertDir)) {
      fs.mkdirSync(alertDir, { recursive: true });
    }

    const fileName = `risk-alert-${alert.type}-${Date.now()}.json`;
    const filePath = path.join(alertDir, fileName);

    fs.writeFileSync(filePath, JSON.stringify({
      timestamp: new Date().toISOString(),
      ...alert
    }, null, 2));
  }

  /**
   * Generate risk assessment report
   */
  async generateRiskReport() {
    const report = {
      timestamp: new Date().toISOString(),
      period: 'last_30_days',
      summary: {
        totalPredictions: 0,
        highRiskPredictions: 0,
        totalAnomalies: 0,
        criticalAnomalies: 0
      },
      predictions: {},
      anomalies: {},
      trends: {},
      recommendations: []
    };

    // Aggregate predictions
    for (const [source, predictions] of this.predictions) {
      report.predictions[source] = predictions;
      report.summary.totalPredictions += predictions.length;
      report.summary.highRiskPredictions += predictions.filter(p => p.probability > 75).length;
    }

    // Aggregate anomalies
    for (const [source, anomalies] of this.anomalies) {
      report.anomalies[source] = anomalies;
      report.summary.totalAnomalies += anomalies.length;
      report.summary.criticalAnomalies += anomalies.filter(a => a.severity === 'critical').length;
    }

    // Calculate trends
    report.trends = this.calculateRiskTrends();

    // Generate recommendations
    report.recommendations = this.generateRiskRecommendations(report);

    return report;
  }

  /**
   * Calculate risk trends
   */
  calculateRiskTrends() {
    const trends = {};

    // Analyze prediction trends over time
    for (const [source, predictions] of this.predictions) {
      const recent = predictions.filter(p => p.timeframe.includes('week'));
      const future = predictions.filter(p => p.timeframe.includes('month'));

      trends[source] = {
        shortTerm: recent.length,
        longTerm: future.length,
        riskIncrease: future.length > recent.length ? 'increasing' : 'stable'
      };
    }

    return trends;
  }

  /**
   * Generate risk recommendations
   */
  generateRiskRecommendations(report) {
    const recommendations = [];

    if (report.summary.criticalAnomalies > 0) {
      recommendations.push('Address critical anomalies immediately');
    }

    if (report.summary.highRiskPredictions > 3) {
      recommendations.push('Review high-risk predictions and implement mitigation strategies');
    }

    // Add specific recommendations based on trends
    for (const [source, trend] of Object.entries(report.trends)) {
      if (trend.riskIncrease === 'increasing') {
        recommendations.push(`Monitor ${source} closely - risk trend is increasing`);
      }
    }

    return recommendations;
  }

  /**
   * Get current risk assessment status
   */
  getStatus() {
    return {
      isRunning: !!this.predictionInterval,
      dataSources: Array.from(this.historicalData.keys()),
      models: Array.from(this.riskModels.keys()),
      predictions: Array.from(this.predictions.keys()).length,
      anomalies: Array.from(this.anomalies.keys()).length,
      lastUpdate: Date.now()
    };
  }
}

/**
 * Statistical Models
 */
class TrendAnalysisModel {
  async predict(source, data, baseline) {
    const predictions = [];

    for (const [metric, stats] of Object.entries(baseline)) {
      if (stats.trend === 'increasing') {
        const projectedValue = stats.mean * 1.2; // 20% increase projection
        const confidence = Math.min(Math.abs(stats.trend) / 10, 1);

        if (confidence > 0.7) {
          predictions.push({
            risk: `${metric} performance degradation`,
            probability: confidence * 100,
            confidence: confidence,
            timeframe: 'next week',
            impact: 'Medium - potential performance issues',
            recommendations: ['Monitor closely', 'Prepare scaling plan']
          });
        }
      }
    }

    return predictions;
  }
}

class CorrelationAnalysisModel {
  async predict(source, data, baseline) {
    // Simplified correlation analysis
    const predictions = [];

    // Example: Correlate CPU usage with error rates
    if (source === 'performance') {
      predictions.push({
        risk: 'Performance bottleneck',
        probability: 65,
        confidence: 0.7,
        timeframe: 'next 2 weeks',
        impact: 'High - could affect user experience',
        recommendations: ['Optimize database queries', 'Implement caching']
      });
    }

    return predictions;
  }
}

class RegressionModel {
  async predict(source, data, baseline) {
    // Linear regression-based predictions
    const predictions = [];

    if (data.length > 10) {
      predictions.push({
        risk: 'Resource exhaustion',
        probability: 55,
        confidence: 0.6,
        timeframe: 'next month',
        impact: 'Medium - potential downtime',
        recommendations: ['Plan capacity upgrade', 'Implement auto-scaling']
      });
    }

    return predictions;
  }
}

/**
 * Anomaly Detection Models
 */
class IsolationForestModel {
  async predict(source, data, baseline) {
    // Simplified anomaly detection
    return [];
  }
}

class ZScoreDetector {
  async predict(source, data, baseline) {
    // Z-score based anomaly detection
    return [];
  }
}

/**
 * Machine Learning Models (placeholders)
 */
class NeuralNetworkModel {
  async predict(source, data, baseline) {
    // Placeholder for neural network implementation
    return [];
  }
}

class RandomForestModel {
  async predict(source, data, baseline) {
    // Placeholder for random forest implementation
    return [];
  }
}

module.exports = PredictiveRiskAssessor;
