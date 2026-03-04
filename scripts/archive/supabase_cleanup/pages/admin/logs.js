import { useState, useEffect } from 'react';
import Head from 'next/head';

export default function LogsAdmin() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filters, setFilters] = useState({
    limit: 50,
    offset: 0,
    operation: '',
    from: '',
    to: '',
    user: ''
  });

  // Load logs when the component mounts or filters change
  useEffect(() => {
    const fetchLogs = async () => {
      setLoading(true);
      try {
        // Build query string from filters
        const queryParams = new URLSearchParams();
        Object.entries(filters).forEach(([key, value]) => {
          if (value) queryParams.append(key, value);
        });
        
        const response = await fetch(`/api/admin/logs?${queryParams.toString()}`);
        if (!response.ok) {
          throw new Error(`Error fetching logs: ${response.statusText}`);
        }
        const data = await response.json();
        setLogs(data.logs);
        setError(null);
      } catch (err) {
        console.error('Failed to fetch logs:', err);
        setError(err.message);
        setLogs([]);
      } finally {
        setLoading(false);
      }
    };

    fetchLogs();
  }, [filters]);

  // Handle filter changes
  const handleFilterChange = (e) => {
    const { name, value } = e.target;
    setFilters(prev => ({
      ...prev,
      [name]: value
    }));
  };

  // Format timestamp to human-readable date
  const formatDate = (timestamp) => {
    if (!timestamp) return 'N/A';
    return new Date(timestamp * 1000).toLocaleString();
  };

  // Handle pagination
  const handlePrevPage = () => {
    if (filters.offset - filters.limit >= 0) {
      setFilters(prev => ({
        ...prev,
        offset: prev.offset - prev.limit
      }));
    }
  };

  const handleNextPage = () => {
    setFilters(prev => ({
      ...prev,
      offset: prev.offset + prev.limit
    }));
  };

  return (
    <div className="container">
      <Head>
        <title>MCP Logs Admin</title>
        <meta name="description" content="Admin panel for viewing MCP logs" />
      </Head>

      <main>
        <h1 className="title">MCP Logs Admin</h1>

        <div className="filters">
          <div className="filter-row">
            <div className="filter-group">
              <label htmlFor="operation">Operation:</label>
              <input
                type="text"
                id="operation"
                name="operation"
                value={filters.operation}
                onChange={handleFilterChange}
                placeholder="Filter by operation"
              />
            </div>

            <div className="filter-group">
              <label htmlFor="user">User:</label>
              <input
                type="text"
                id="user"
                name="user"
                value={filters.user}
                onChange={handleFilterChange}
                placeholder="Filter by user"
              />
            </div>
          </div>

          <div className="filter-row">
            <div className="filter-group">
              <label htmlFor="from">From:</label>
              <input
                type="datetime-local"
                id="from"
                name="from"
                value={filters.from}
                onChange={(e) => {
                  // Convert datetime-local to timestamp
                  const date = new Date(e.target.value);
                  const timestamp = Math.floor(date.getTime() / 1000);
                  setFilters(prev => ({
                    ...prev,
                    from: timestamp || ''
                  }));
                }}
              />
            </div>

            <div className="filter-group">
              <label htmlFor="to">To:</label>
              <input
                type="datetime-local"
                id="to"
                name="to"
                value={filters.to}
                onChange={(e) => {
                  // Convert datetime-local to timestamp
                  const date = new Date(e.target.value);
                  const timestamp = Math.floor(date.getTime() / 1000);
                  setFilters(prev => ({
                    ...prev,
                    to: timestamp || ''
                  }));
                }}
              />
            </div>

            <div className="filter-group">
              <label htmlFor="limit">Limit:</label>
              <select
                id="limit"
                name="limit"
                value={filters.limit}
                onChange={handleFilterChange}
              >
                <option value="10">10</option>
                <option value="25">25</option>
                <option value="50">50</option>
                <option value="100">100</option>
              </select>
            </div>
          </div>

          <button 
            className="sync-button"
            onClick={async () => {
              try {
                setLoading(true);
                const response = await fetch('/api/sync', {
                  method: 'POST'
                });
                const data = await response.json();
                alert(`Synced ${data.count} logs to Supabase`);
                // Refresh logs
                setFilters(prev => ({ ...prev }));
              } catch (err) {
                console.error('Failed to sync logs:', err);
                alert(`Failed to sync logs: ${err.message}`);
              } finally {
                setLoading(false);
              }
            }}
          >
            Sync Memory Logs to Supabase
          </button>
        </div>

        {error && (
          <div className="error-message">
            Error: {error}
          </div>
        )}

        {loading ? (
          <div className="loading">Loading logs...</div>
        ) : (
          <>
            <div className="logs-table-container">
              <table className="logs-table">
                <thead>
                  <tr>
                    <th>Timestamp</th>
                    <th>Context ID</th>
                    <th>Operation</th>
                    <th>User</th>
                    <th>Status</th>
                    <th>Details</th>
                  </tr>
                </thead>
                <tbody>
                  {logs.length === 0 ? (
                    <tr>
                      <td colSpan="6" className="no-logs">No logs found</td>
                    </tr>
                  ) : (
                    logs.map((log) => (
                      <tr key={log.id}>
                        <td>{formatDate(log.timestamp)}</td>
                        <td>{log.context_id}</td>
                        <td>{log.operation}</td>
                        <td>{log.user_id}</td>
                        <td>{log.status}</td>
                        <td>
                          <button
                            className="details-button"
                            onClick={() => {
                              alert(JSON.stringify({
                                parameters: log.parameters,
                                result: log.result
                              }, null, 2));
                            }}
                          >
                            View
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            <div className="pagination">
              <button
                onClick={handlePrevPage}
                disabled={filters.offset === 0}
              >
                Previous
              </button>
              <span>
                Page {Math.floor(filters.offset / filters.limit) + 1}
              </span>
              <button
                onClick={handleNextPage}
                disabled={logs.length < filters.limit}
              >
                Next
              </button>
            </div>
          </>
        )}
      </main>

      <style jsx>{`
        .container {
          min-height: 100vh;
          padding: 0 0.5rem;
          display: flex;
          flex-direction: column;
          align-items: center;
        }

        main {
          padding: 2rem 0;
          flex: 1;
          display: flex;
          flex-direction: column;
          width: 100%;
          max-width: 1200px;
        }

        .title {
          margin: 0;
          line-height: 1.15;
          font-size: 2rem;
          margin-bottom: 2rem;
        }

        .filters {
          background-color: #f9f9f9;
          padding: 1rem;
          border-radius: 5px;
          margin-bottom: 2rem;
          width: 100%;
        }

        .filter-row {
          display: flex;
          gap: 1rem;
          margin-bottom: 1rem;
        }

        .filter-group {
          display: flex;
          flex-direction: column;
          flex: 1;
        }

        .filter-group label {
          margin-bottom: 0.5rem;
          font-weight: bold;
        }

        .filter-group input,
        .filter-group select {
          padding: 0.5rem;
          border: 1px solid #ddd;
          border-radius: 4px;
        }

        .sync-button {
          padding: 0.5rem 1rem;
          background-color: #4a9;
          color: white;
          border: none;
          border-radius: 4px;
          cursor: pointer;
          margin-top: 1rem;
        }

        .error-message {
          color: #e53e3e;
          margin-bottom: 1rem;
          padding: 0.5rem;
          background-color: #fff5f5;
          border: 1px solid #fed7d7;
          border-radius: 4px;
          width: 100%;
        }

        .loading {
          text-align: center;
          margin: 2rem 0;
          font-style: italic;
          color: #666;
        }

        .logs-table-container {
          width: 100%;
          overflow-x: auto;
        }

        .logs-table {
          width: 100%;
          border-collapse: collapse;
        }

        .logs-table th,
        .logs-table td {
          border: 1px solid #ddd;
          padding: 0.5rem;
          text-align: left;
        }

        .logs-table th {
          background-color: #f2f2f2;
          font-weight: bold;
        }

        .logs-table tr:nth-child(even) {
          background-color: #f9f9f9;
        }

        .logs-table tr:hover {
          background-color: #f2f2f2;
        }

        .no-logs {
          text-align: center;
          font-style: italic;
          color: #666;
        }

        .details-button {
          padding: 0.25rem 0.5rem;
          background-color: #0070f3;
          color: white;
          border: none;
          border-radius: 4px;
          cursor: pointer;
        }

        .pagination {
          display: flex;
          justify-content: center;
          gap: 1rem;
          margin-top: 1rem;
          align-items: center;
        }

        .pagination button {
          padding: 0.5rem 1rem;
          background-color: #0070f3;
          color: white;
          border: none;
          border-radius: 4px;
          cursor: pointer;
        }

        .pagination button:disabled {
          background-color: #ccc;
          cursor: not-allowed;
        }
      `}</style>
    </div>
  );
} 