/**
 * Database Integration and Monitoring System
 * Comprehensive database monitoring, optimization, and management
 */

const { Pool } = require('pg');
const { MongoClient } = require('mongodb');
const redis = require('redis');
const { EventEmitter } = require('events');
const fs = require('fs');
const path = require('path');

class DatabaseMonitor extends EventEmitter {
  constructor() {
    super();
    this.connections = new Map();
    this.metrics = new Map();
    this.alerts = new Map();
    this.isMonitoring = false;

    this.config = this.loadConfig();
  }

  loadConfig() {
    const configPath = path.join(__dirname, '..', 'config', 'database-config.json');

    if (fs.existsSync(configPath)) {
      return JSON.parse(fs.readFileSync(configPath, 'utf8'));
    }

    return {
      enabled: true,
      monitoring: {
        interval: 30000, // 30 seconds
        retentionPeriod: 86400000, // 24 hours
        slowQueryThreshold: 1000, // 1 second
        connectionPoolThreshold: 80 // 80% utilization
      },
      databases: {
        postgresql: {
          enabled: true,
          connectionString: process.env.DATABASE_URL || 'postgresql://user:pass@localhost:5432/db',
          poolSize: 10,
          idleTimeoutMillis: 30000,
          connectionTimeoutMillis: 2000
        },
        mongodb: {
          enabled: false,
          url: process.env.MONGODB_URL || 'mongodb://localhost:27017',
          database: 'firebase_dev',
          poolSize: 10,
          serverSelectionTimeoutMS: 5000
        },
        redis: {
          enabled: true,
          url: process.env.REDIS_URL || 'redis://localhost:6379',
          password: process.env.REDIS_PASSWORD,
          retryDelayOnFailover: 100,
          maxRetriesPerRequest: 3
        }
      },
      alerts: {
        enabled: true,
        cooldownPeriod: 300000, // 5 minutes
        thresholds: {
          connectionPoolUtilization: 80,
          slowQueriesPerMinute: 10,
          failedConnectionsPerMinute: 5,
          memoryUsage: 85,
          diskUsage: 90
        }
      },
      optimization: {
        enabled: true,
        autoVacuum: true,
        indexOptimization: true,
        queryOptimization: true,
        cacheOptimization: true
      }
    };
  }

  /**
   * Initialize database connections and monitoring
   */
  async initialize() {
    console.log('🗄️ Initializing Database Monitor...');

    try {
      // Initialize PostgreSQL connection
      if (this.config.databases.postgresql.enabled) {
        await this.initializePostgreSQL();
      }

      // Initialize MongoDB connection
      if (this.config.databases.mongodb.enabled) {
        await this.initializeMongoDB();
      }

      // Initialize Redis connection
      if (this.config.databases.redis.enabled) {
        await this.initializeRedis();
      }

      console.log('✅ Database Monitor initialized');
      this.emit('initialized');
    } catch (error) {
      console.error('❌ Failed to initialize Database Monitor:', error.message);
      throw error;
    }
  }

  /**
   * Initialize PostgreSQL connection and monitoring
   */
  async initializePostgreSQL() {
    try {
      const pool = new Pool({
        connectionString: this.config.databases.postgresql.connectionString,
        max: this.config.databases.postgresql.poolSize,
        idleTimeoutMillis: this.config.databases.postgresql.idleTimeoutMillis,
        connectionTimeoutMillis: this.config.databases.postgresql.connectionTimeoutMillis
      });

      // Test connection
      const client = await pool.connect();
      await client.query('SELECT 1');
      client.release();

      this.connections.set('postgresql', pool);

      // Set up monitoring queries
      this.postgresQueries = {
        connectionStats: `
          SELECT
            count(*) as total_connections,
            count(*) filter (where state = 'active') as active_connections,
            count(*) filter (where state = 'idle') as idle_connections,
            count(*) filter (where state = 'idle in transaction') as idle_in_transaction
          FROM pg_stat_activity
          WHERE datname = current_database()
        `,
        slowQueries: `
          SELECT
            query,
            calls,
            total_time,
            mean_time,
            rows
          FROM pg_stat_statements
          WHERE mean_time > $1
          ORDER BY mean_time DESC
          LIMIT 10
        `,
        tableStats: `
          SELECT
            schemaname,
            tablename,
            n_tup_ins,
            n_tup_upd,
            n_tup_del,
            n_live_tup,
            n_dead_tup,
            last_vacuum,
            last_autovacuum,
            last_analyze,
            last_autoanalyze
          FROM pg_stat_user_tables
          ORDER BY n_live_tup DESC
        `,
        indexStats: `
          SELECT
            schemaname,
            tablename,
            indexname,
            idx_scan,
            idx_tup_read,
            idx_tup_fetch
          FROM pg_stat_user_indexes
          ORDER BY idx_scan DESC
        `
      };

      console.log('✅ PostgreSQL connection established');
    } catch (error) {
      console.error('❌ Failed to connect to PostgreSQL:', error.message);
      throw error;
    }
  }

  /**
   * Initialize MongoDB connection and monitoring
   */
  async initializeMongoDB() {
    try {
      const client = new MongoClient(this.config.databases.mongodb.url, {
        maxPoolSize: this.config.databases.mongodb.poolSize,
        serverSelectionTimeoutMS: this.config.databases.mongodb.serverSelectionTimeoutMS
      });

      await client.connect();
      const db = client.db(this.config.databases.mongodb.database);

      this.connections.set('mongodb', { client, db });

      console.log('✅ MongoDB connection established');
    } catch (error) {
      console.error('❌ Failed to connect to MongoDB:', error.message);
      throw error;
    }
  }

  /**
   * Initialize Redis connection and monitoring
   */
  async initializeRedis() {
    try {
      const client = redis.createClient({
        url: this.config.databases.redis.url,
        password: this.config.databases.redis.password,
        retryDelayOnFailover: this.config.databases.redis.retryDelayOnFailover,
        maxRetriesPerRequest: this.config.databases.redis.maxRetriesPerRequest
      });

      await client.connect();
      this.connections.set('redis', client);

      console.log('✅ Redis connection established');
    } catch (error) {
      console.error('❌ Failed to connect to Redis:', error.message);
      throw error;
    }
  }

  /**
   * Start database monitoring
   */
  async startMonitoring() {
    if (this.isMonitoring) {
      console.log('📊 Database monitoring is already running');
      return;
    }

    console.log('📊 Starting database monitoring...');

    this.monitoringInterval = setInterval(async () => {
      await this.collectMetrics();
      await this.checkAlerts();
      await this.optimizeDatabases();
    }, this.config.monitoring.interval);

    this.isMonitoring = true;
    console.log('✅ Database monitoring started');

    this.emit('monitoringStarted');
  }

  /**
   * Stop database monitoring
   */
  async stopMonitoring() {
    if (!this.isMonitoring) {
      console.log('📊 Database monitoring is not running');
      return;
    }

    console.log('🛑 Stopping database monitoring...');

    if (this.monitoringInterval) {
      clearInterval(this.monitoringInterval);
    }

    // Close connections
    for (const [name, connection] of this.connections) {
      if (name === 'postgresql') {
        await connection.end();
      } else if (name === 'mongodb') {
        await connection.client.close();
      } else if (name === 'redis') {
        await connection.quit();
      }
    }

    this.isMonitoring = false;
    console.log('✅ Database monitoring stopped');

    this.emit('monitoringStopped');
  }

  /**
   * Collect metrics from all databases
   */
  async collectMetrics() {
    const timestamp = Date.now();
    const metrics = {};

    // PostgreSQL metrics
    if (this.connections.has('postgresql')) {
      metrics.postgresql = await this.collectPostgreSQLMetrics();
    }

    // MongoDB metrics
    if (this.connections.has('mongodb')) {
      metrics.mongodb = await this.collectMongoDBMetrics();
    }

    // Redis metrics
    if (this.connections.has('redis')) {
      metrics.redis = await this.collectRedisMetrics();
    }

    // Store metrics with timestamp
    this.metrics.set(timestamp, metrics);

    // Clean up old metrics
    this.cleanupOldMetrics();

    this.emit('metricsCollected', { timestamp, metrics });
  }

  /**
   * Collect PostgreSQL metrics
   */
  async collectPostgreSQLMetrics() {
    const pool = this.connections.get('postgresql');
    const client = await pool.connect();

    try {
      const metrics = {};

      // Connection statistics
      const connectionResult = await client.query(this.postgresQueries.connectionStats);
      metrics.connections = connectionResult.rows[0];

      // Slow queries
      const slowQueryResult = await client.query(this.postgresQueries.slowQueries, [
        this.config.monitoring.slowQueryThreshold
      ]);
      metrics.slowQueries = slowQueryResult.rows;

      // Table statistics
      const tableResult = await client.query(this.postgresQueries.tableStats);
      metrics.tables = tableResult.rows;

      // Index statistics
      const indexResult = await client.query(this.postgresQueries.indexStats);
      metrics.indexes = indexResult.rows;

      // Database size
      const sizeResult = await client.query(`
        SELECT
          pg_size_pretty(pg_database_size(current_database())) as size,
          pg_database_size(current_database()) as size_bytes
      `);
      metrics.databaseSize = sizeResult.rows[0];

      return metrics;
    } catch (error) {
      console.error('❌ Failed to collect PostgreSQL metrics:', error.message);
      return { error: error.message };
    } finally {
      client.release();
    }
  }

  /**
   * Collect MongoDB metrics
   */
  async collectMongoDBMetrics() {
    const { db } = this.connections.get('mongodb');

    try {
      const metrics = {};

      // Database statistics
      const dbStats = await db.stats();
      metrics.databaseStats = dbStats;

      // Collection statistics
      const collections = await db.listCollections().toArray();
      metrics.collections = [];

      for (const collection of collections) {
        const stats = await db.collection(collection.name).stats();
        metrics.collections.push({
          name: collection.name,
          count: stats.count,
          size: stats.size,
          avgObjSize: stats.avgObjSize,
          storageSize: stats.storageSize,
          indexes: stats.nindexes,
          indexSize: stats.totalIndexSize
        });
      }

      // Server status
      const serverStatus = await db.admin().serverStatus();
      metrics.serverStatus = {
        connections: serverStatus.connections,
        opcounters: serverStatus.opcounters,
        mem: serverStatus.mem,
        uptime: serverStatus.uptime
      };

      return metrics;
    } catch (error) {
      console.error('❌ Failed to collect MongoDB metrics:', error.message);
      return { error: error.message };
    }
  }

  /**
   * Collect Redis metrics
   */
  async collectRedisMetrics() {
    const client = this.connections.get('redis');

    try {
      const metrics = {};

      // Memory information
      const memoryInfo = await client.info('memory');
      metrics.memory = this.parseRedisInfo(memoryInfo);

      // CPU information
      const cpuInfo = await client.info('cpu');
      metrics.cpu = this.parseRedisInfo(cpuInfo);

      // Keyspace information
      const keyspaceInfo = await client.info('keyspace');
      metrics.keyspace = this.parseRedisInfo(keyspaceInfo);

      // Connection statistics
      const statsInfo = await client.info('stats');
      metrics.stats = this.parseRedisInfo(statsInfo);

      // Connected clients
      metrics.clients = await client.clientList();

      return metrics;
    } catch (error) {
      console.error('❌ Failed to collect Redis metrics:', error.message);
      return { error: error.message };
    }
  }

  /**
   * Parse Redis INFO command output
   */
  parseRedisInfo(infoString) {
    const lines = infoString.split('\r\n');
    const result = {};

    for (const line of lines) {
      if (line.includes(':')) {
        const [key, value] = line.split(':');
        result[key] = value;
      }
    }

    return result;
  }

  /**
   * Check for database alerts
   */
  async checkAlerts() {
    const latestMetrics = Array.from(this.metrics.values()).pop();
    if (!latestMetrics) return;

    // PostgreSQL alerts
    if (latestMetrics.postgresql) {
      await this.checkPostgreSQLAlerts(latestMetrics.postgresql);
    }

    // MongoDB alerts
    if (latestMetrics.mongodb) {
      await this.checkMongoDBAlerts(latestMetrics.mongodb);
    }

    // Redis alerts
    if (latestMetrics.redis) {
      await this.checkRedisAlerts(latestMetrics.redis);
    }
  }

  /**
   * Check PostgreSQL alerts
   */
  async checkPostgreSQLAlerts(metrics) {
    if (metrics.error) return;

    // Connection pool utilization
    const totalConnections = parseInt(metrics.connections.total_connections) || 0;
    const activeConnections = parseInt(metrics.connections.active_connections) || 0;
    const utilization = (activeConnections / this.config.databases.postgresql.poolSize) * 100;

    if (utilization > this.config.alerts.thresholds.connectionPoolUtilization) {
      this.createAlert('postgresql', 'high_connection_utilization',
        `Connection pool utilization is ${utilization.toFixed(1)}%`);
    }

    // Slow queries
    if (metrics.slowQueries && metrics.slowQueries.length > this.config.alerts.thresholds.slowQueriesPerMinute) {
      this.createAlert('postgresql', 'high_slow_queries',
        `Found ${metrics.slowQueries.length} slow queries`);
    }
  }

  /**
   * Check MongoDB alerts
   */
  async checkMongoDBAlerts(metrics) {
    if (metrics.error) return;

    // Memory usage
    if (metrics.serverStatus?.mem) {
      const memoryUsage = (metrics.serverStatus.mem.resident / metrics.serverStatus.mem.limit) * 100;
      if (memoryUsage > this.config.alerts.thresholds.memoryUsage) {
        this.createAlert('mongodb', 'high_memory_usage',
          `Memory usage is ${memoryUsage.toFixed(1)}%`);
      }
    }
  }

  /**
   * Check Redis alerts
   */
  async checkRedisAlerts(metrics) {
    if (metrics.error) return;

    // Memory usage
    if (metrics.memory?.used_memory && metrics.memory?.maxmemory) {
      const memoryUsage = (parseInt(metrics.memory.used_memory) / parseInt(metrics.memory.maxmemory)) * 100;
      if (memoryUsage > this.config.alerts.thresholds.memoryUsage) {
        this.createAlert('redis', 'high_memory_usage',
          `Memory usage is ${memoryUsage.toFixed(1)}%`);
      }
    }

    // Connected clients
    if (metrics.clients && metrics.clients.length > 1000) {
      this.createAlert('redis', 'high_client_connections',
        `High number of connected clients: ${metrics.clients.length}`);
    }
  }

  /**
   * Create database alert
   */
  createAlert(database, type, message) {
    const alertId = `${database}_${type}_${Date.now()}`;
    const alertKey = `${database}_${type}`;

    // Check for alert cooldown
    const lastAlert = this.alerts.get(alertKey);
    if (lastAlert && (Date.now() - lastAlert.timestamp) < this.config.alerts.cooldownPeriod) {
      return;
    }

    const alert = {
      id: alertId,
      database,
      type,
      message,
      timestamp: Date.now(),
      acknowledged: false,
      resolved: false
    };

    this.alerts.set(alertKey, alert);
    console.log(`🚨 DATABASE ALERT: ${message}`);

    this.emit('alert', alert);
  }

  /**
   * Optimize databases
   */
  async optimizeDatabases() {
    if (!this.config.optimization.enabled) return;

    // PostgreSQL optimization
    if (this.connections.has('postgresql')) {
      await this.optimizePostgreSQL();
    }

    // MongoDB optimization
    if (this.connections.has('mongodb')) {
      await this.optimizeMongoDB();
    }

    // Redis optimization
    if (this.connections.has('redis')) {
      await this.optimizeRedis();
    }
  }

  /**
   * Optimize PostgreSQL
   */
  async optimizePostgreSQL() {
    const pool = this.connections.get('postgresql');
    const client = await pool.connect();

    try {
      // Analyze tables for query optimization
      await client.query('ANALYZE');

      // Vacuum tables if needed
      if (this.config.optimization.autoVacuum) {
        const result = await client.query(`
          SELECT schemaname, tablename
          FROM pg_stat_user_tables
          WHERE last_vacuum IS NULL OR last_vacuum < now() - interval '1 day'
          LIMIT 5
        `);

        for (const row of result.rows) {
          await client.query(`VACUUM ANALYZE "${row.schemaname}"."${row.tablename}"`);
          console.log(`🧹 Vacuumed ${row.schemaname}.${row.tablename}`);
        }
      }

    } catch (error) {
      console.error('❌ PostgreSQL optimization failed:', error.message);
    } finally {
      client.release();
    }
  }

  /**
   * Optimize MongoDB
   */
  async optimizeMongoDB() {
    const { db } = this.connections.get('mongodb');

    try {
      // Compact collections if needed
      const collections = await db.listCollections().toArray();

      for (const collection of collections) {
        const stats = await db.collection(collection.name).stats();

        // Check if collection needs compaction
        if (stats.size > 1000000 && (stats.size / stats.storageSize) > 2) {
          await db.command({ compact: collection.name });
          console.log(`🧹 Compacted MongoDB collection: ${collection.name}`);
        }
      }

    } catch (error) {
      console.error('❌ MongoDB optimization failed:', error.message);
    }
  }

  /**
   * Optimize Redis
   */
  async optimizeRedis() {
    const client = this.connections.get('redis');

    try {
      // Clean up expired keys
      const expiredKeys = await client.unlink('*', 'EX');
      if (expiredKeys > 0) {
        console.log(`🧹 Cleaned up ${expiredKeys} expired Redis keys`);
      }

    } catch (error) {
      console.error('❌ Redis optimization failed:', error.message);
    }
  }

  /**
   * Clean up old metrics
   */
  cleanupOldMetrics() {
    const cutoff = Date.now() - this.config.monitoring.retentionPeriod;
    const oldKeys = Array.from(this.metrics.keys()).filter(timestamp => timestamp < cutoff);

    oldKeys.forEach(key => this.metrics.delete(key));

    if (oldKeys.length > 0) {
      console.log(`🧹 Cleaned up ${oldKeys.length} old metrics`);
    }
  }

  /**
   * Generate database health report
   */
  async generateHealthReport() {
    const report = {
      timestamp: new Date().toISOString(),
      databases: {},
      alerts: Array.from(this.alerts.values()),
      recommendations: []
    };

    // PostgreSQL report
    if (this.connections.has('postgresql')) {
      const latestMetrics = Array.from(this.metrics.values()).pop()?.postgresql;
      if (latestMetrics) {
        report.databases.postgresql = {
          status: 'healthy',
          connections: latestMetrics.connections,
          slowQueries: latestMetrics.slowQueries?.length || 0,
          databaseSize: latestMetrics.databaseSize
        };
      }
    }

    // MongoDB report
    if (this.connections.has('mongodb')) {
      const latestMetrics = Array.from(this.metrics.values()).pop()?.mongodb;
      if (latestMetrics) {
        report.databases.mongodb = {
          status: 'healthy',
          collections: latestMetrics.collections?.length || 0,
          serverStatus: latestMetrics.serverStatus
        };
      }
    }

    // Redis report
    if (this.connections.has('redis')) {
      const latestMetrics = Array.from(this.metrics.values()).pop()?.redis;
      if (latestMetrics) {
        report.databases.redis = {
          status: 'healthy',
          memory: latestMetrics.memory,
          clients: latestMetrics.clients?.length || 0
        };
      }
    }

    // Generate recommendations
    report.recommendations = await this.generateRecommendations(report);

    return report;
  }

  /**
   * Generate optimization recommendations
   */
  async generateRecommendations(report) {
    const recommendations = [];

    // PostgreSQL recommendations
    if (report.databases.postgresql) {
      const pg = report.databases.postgresql;

      if (pg.slowQueries > 5) {
        recommendations.push('PostgreSQL: Review and optimize slow queries');
      }

      if (pg.connections?.active_connections > this.config.databases.postgresql.poolSize * 0.8) {
        recommendations.push('PostgreSQL: Consider increasing connection pool size');
      }
    }

    // MongoDB recommendations
    if (report.databases.mongodb) {
      const mongo = report.databases.mongodb;

      if (mongo.collections > 50) {
        recommendations.push('MongoDB: Consider sharding for high collection count');
      }
    }

    // Redis recommendations
    if (report.databases.redis) {
      const redis = report.databases.redis;

      if (redis.clients > 500) {
        recommendations.push('Redis: High client connections - consider connection pooling');
      }
    }

    return recommendations;
  }

  /**
   * Execute database maintenance tasks
   */
  async executeMaintenance(task) {
    switch (task) {
      case 'vacuum':
        await this.executePostgreSQLVacuum();
        break;
      case 'analyze':
        await this.executePostgreSQLAnalyze();
        break;
      case 'backup':
        await this.executeBackup();
        break;
      default:
        throw new Error(`Unknown maintenance task: ${task}`);
    }
  }

  /**
   * Execute PostgreSQL vacuum
   */
  async executePostgreSQLVacuum() {
    if (!this.connections.has('postgresql')) {
      throw new Error('PostgreSQL connection not available');
    }

    const pool = this.connections.get('postgresql');
    const client = await pool.connect();

    try {
      await client.query('VACUUM FULL');
      console.log('✅ PostgreSQL vacuum completed');
    } catch (error) {
      console.error('❌ PostgreSQL vacuum failed:', error.message);
      throw error;
    } finally {
      client.release();
    }
  }

  /**
   * Execute PostgreSQL analyze
   */
  async executePostgreSQLAnalyze() {
    if (!this.connections.has('postgresql')) {
      throw new Error('PostgreSQL connection not available');
    }

    const pool = this.connections.get('postgresql');
    const client = await pool.connect();

    try {
      await client.query('ANALYZE');
      console.log('✅ PostgreSQL analyze completed');
    } catch (error) {
      console.error('❌ PostgreSQL analyze failed:', error.message);
      throw error;
    } finally {
      client.release();
    }
  }

  /**
   * Execute database backup
   */
  async executeBackup() {
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const backupDir = path.join(__dirname, '..', 'backups');

    if (!fs.existsSync(backupDir)) {
      fs.mkdirSync(backupDir, { recursive: true });
    }

    // PostgreSQL backup
    if (this.connections.has('postgresql')) {
      const pgBackupFile = path.join(backupDir, `postgresql-${timestamp}.sql`);
      // In a real implementation, this would use pg_dump
      console.log(`📦 PostgreSQL backup would be created: ${pgBackupFile}`);
    }

    // MongoDB backup
    if (this.connections.has('mongodb')) {
      const mongoBackupDir = path.join(backupDir, `mongodb-${timestamp}`);
      // In a real implementation, this would use mongodump
      console.log(`📦 MongoDB backup would be created: ${mongoBackupDir}`);
    }

    console.log('✅ Database backup completed');
  }

  /**
   * Get current database status
   */
  getStatus() {
    return {
      isMonitoring: this.isMonitoring,
      connections: Array.from(this.connections.keys()),
      metricsCount: this.metrics.size,
      alertsCount: this.alerts.size,
      lastUpdate: Array.from(this.metrics.keys()).pop()
    };
  }
}

module.exports = DatabaseMonitor;
