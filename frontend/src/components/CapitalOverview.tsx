import { useEffect, useState } from 'react';
import { api, CapitalSummary } from '../api';

export function CapitalOverview() {
    const [summary, setSummary] = useState<CapitalSummary | null>(null);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const fetchData = async () => {
            try {
                const data = await api.getCapitalSummary();
                setSummary(data);
                setError(null);
            } catch (e) {
                console.error(e);
                setError('Failed to load');
            }
        };
        fetchData();
        const interval = setInterval(fetchData, 10000);
        return () => clearInterval(interval);
    }, []);

    if (error) return <div className="card compact-card">Capital: {error}</div>;
    if (!summary) return <div className="card compact-card">Loading capital...</div>;

    const isPositive = summary.net_change_usd >= 0;
    const deployedPct = summary.starting_capital > 0
        ? (summary.deployed_capital / summary.starting_capital * 100)
        : 0;

    return (
        <div className="card compact-card capital-overview">
            <h3>💰 Capital Overview</h3>

            {/* Main Stats Row */}
            <div className="capital-stats">
                <div className="stat-box">
                    <label>Starting</label>
                    <span className="value">${summary.starting_capital.toLocaleString()}</span>
                </div>
                <div className="stat-box">
                    <label>Current</label>
                    <span className="value">${summary.current_capital.toLocaleString()}</span>
                </div>
                <div className="stat-box highlight">
                    <label>Net Change</label>
                    <span className={`value ${isPositive ? 'positive' : 'negative'}`}>
                        {isPositive ? '+' : ''}{summary.net_change_pct.toFixed(2)}%
                    </span>
                    <span className={`subvalue ${isPositive ? 'positive' : 'negative'}`}>
                        {isPositive ? '+' : ''}${summary.net_change_usd.toFixed(2)}
                    </span>
                </div>
            </div>

            {/* Capital Allocation Bar */}
            <div className="allocation-section">
                <div className="allocation-labels">
                    <span>Deployed: ${summary.deployed_capital.toFixed(0)}</span>
                    <span>Available: ${summary.available_capital.toFixed(0)}</span>
                </div>
                <div className="allocation-bar">
                    <div
                        className="deployed-fill"
                        style={{ width: `${Math.min(deployedPct, 100)}%` }}
                    />
                </div>
                <div className="allocation-pct">
                    {deployedPct.toFixed(0)}% deployed
                </div>
            </div>

            {/* Unrealized P&L */}
            {summary.unrealized_pnl !== 0 && (
                <div className="unrealized">
                    Unrealized P&L: <span className={summary.unrealized_pnl >= 0 ? 'positive' : 'negative'}>
                        {summary.unrealized_pnl >= 0 ? '+' : ''}${summary.unrealized_pnl.toFixed(2)}
                    </span>
                    <span className="hint"> (if all lots sold now)</span>
                </div>
            )}

            <style>{`
                .capital-overview h3 {
                    margin: 0 0 0.75rem 0;
                    font-size: 1rem;
                    color: var(--text-secondary);
                }
                .capital-stats {
                    display: flex;
                    gap: 1rem;
                    margin-bottom: 0.75rem;
                }
                .stat-box {
                    flex: 1;
                    text-align: center;
                }
                .stat-box label {
                    display: block;
                    font-size: 0.75rem;
                    color: var(--text-secondary);
                    margin-bottom: 0.25rem;
                }
                .stat-box .value {
                    display: block;
                    font-size: 1.1rem;
                    font-weight: 600;
                }
                .stat-box .subvalue {
                    display: block;
                    font-size: 0.8rem;
                }
                .stat-box.highlight {
                    background: rgba(255,255,255,0.05);
                    border-radius: 8px;
                    padding: 0.5rem;
                }
                .positive { color: #22c55e; }
                .negative { color: #ef4444; }
                
                .allocation-section {
                    margin-top: 0.5rem;
                    padding-top: 0.5rem;
                    border-top: 1px solid var(--border);
                }
                .allocation-labels {
                    display: flex;
                    justify-content: space-between;
                    font-size: 0.75rem;
                    color: var(--text-secondary);
                    margin-bottom: 0.25rem;
                }
                .allocation-bar {
                    height: 8px;
                    background: rgba(255,255,255,0.1);
                    border-radius: 4px;
                    overflow: hidden;
                }
                .deployed-fill {
                    height: 100%;
                    background: linear-gradient(90deg, #3b82f6, #8b5cf6);
                    border-radius: 4px;
                    transition: width 0.3s ease;
                }
                .allocation-pct {
                    font-size: 0.7rem;
                    color: var(--text-secondary);
                    text-align: center;
                    margin-top: 0.25rem;
                }
                
                .unrealized {
                    margin-top: 0.5rem;
                    font-size: 0.8rem;
                    color: var(--text-secondary);
                    text-align: center;
                }
                .unrealized .hint {
                    font-size: 0.7rem;
                    opacity: 0.7;
                }

                .compact-card {
                    padding: 0.75rem 1rem;
                }
            `}</style>
        </div>
    );
}
