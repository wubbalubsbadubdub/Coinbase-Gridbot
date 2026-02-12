import { useEffect, useState } from 'react';
import { api, PnLBreakdown, PnLHistory } from '../api';

export function PnLBreakdownPanel() {
    const [breakdown, setBreakdown] = useState<PnLBreakdown | null>(null);
    const [history, setHistory] = useState<PnLHistory | null>(null);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const fetchData = async () => {
            try {
                const [bd, hist] = await Promise.all([
                    api.getPnLBreakdown(),
                    api.getPnLHistory(14) // Last 14 days for sparkline
                ]);
                setBreakdown(bd);
                setHistory(hist);
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

    if (error) return <div className="card compact-card">P&L: {error}</div>;
    if (!breakdown) return <div className="card compact-card">Loading P&L...</div>;

    const periods = [
        { label: 'Today', pnl: breakdown.today_pnl, pct: breakdown.today_pct },
        { label: 'Week', pnl: breakdown.week_pnl, pct: breakdown.week_pct },
        { label: 'Month', pnl: breakdown.month_pnl, pct: breakdown.month_pct },
        { label: 'Year', pnl: breakdown.year_pnl, pct: breakdown.year_pct },
        { label: 'Lifetime', pnl: breakdown.lifetime_pnl, pct: breakdown.lifetime_pct },
    ];

    return (
        <div className="card compact-card pnl-breakdown">
            <h3>📈 P&L Breakdown</h3>

            {/* Sparkline Chart */}
            {history && history.daily_pnl.length > 1 && (
                <div className="sparkline-container">
                    <Sparkline data={history.daily_pnl} />
                </div>
            )}

            {/* Period Stats */}
            <div className="pnl-periods">
                {periods.map(p => (
                    <div key={p.label} className="period-box">
                        <label>{p.label}</label>
                        <span className={`value ${p.pnl >= 0 ? 'positive' : 'negative'}`}>
                            {p.pnl >= 0 ? '+' : ''}${formatNumber(p.pnl)}
                        </span>
                        <span className={`pct ${p.pct >= 0 ? 'positive' : 'negative'}`}>
                            {p.pct >= 0 ? '+' : ''}{p.pct.toFixed(2)}%
                        </span>
                    </div>
                ))}
            </div>

            <style>{`
                .pnl-breakdown h3 {
                    margin: 0 0 0.5rem 0;
                    font-size: 1rem;
                    color: var(--text-secondary);
                }
                .sparkline-container {
                    margin-bottom: 0.75rem;
                    padding: 0.25rem 0;
                }
                .pnl-periods {
                    display: flex;
                    gap: 0.25rem;
                }
                .period-box {
                    flex: 1;
                    text-align: center;
                    padding: 0.5rem 0.25rem;
                    background: rgba(255,255,255,0.03);
                    border-radius: 6px;
                    min-width: 0;
                }
                .period-box label {
                    display: block;
                    font-size: 0.65rem;
                    color: var(--text-secondary);
                    margin-bottom: 0.2rem;
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                }
                .period-box .value {
                    display: block;
                    font-size: 0.9rem;
                    font-weight: 600;
                }
                .period-box .pct {
                    display: block;
                    font-size: 0.7rem;
                    opacity: 0.8;
                }
                .positive { color: #22c55e; }
                .negative { color: #ef4444; }
                
                .compact-card {
                    padding: 0.75rem 1rem;
                }
            `}</style>
        </div>
    );
}

// Helper to format large numbers
function formatNumber(n: number): string {
    const abs = Math.abs(n);
    if (abs >= 1000000) return (n / 1000000).toFixed(1) + 'M';
    if (abs >= 1000) return (n / 1000).toFixed(1) + 'k';
    return n.toFixed(2);
}

// Mini Sparkline component using SVG
function Sparkline({ data }: { data: { pnl: number; cumulative: number }[] }) {
    if (data.length < 2) return null;

    const width = 280;
    const height = 40;
    const padding = 2;

    // Use cumulative values for the chart
    const values = data.map(d => d.cumulative);
    const min = Math.min(...values);
    const max = Math.max(...values);
    const range = max - min || 1;

    // Generate path
    const points = values.map((v, i) => {
        const x = padding + (i / (values.length - 1)) * (width - padding * 2);
        const y = height - padding - ((v - min) / range) * (height - padding * 2);
        return `${x},${y}`;
    });

    const pathD = `M ${points.join(' L ')}`;

    // Determine color based on trend
    const isPositive = values[values.length - 1] >= values[0];
    const lineColor = isPositive ? '#22c55e' : '#ef4444';
    const fillColor = isPositive ? 'rgba(34, 197, 94, 0.1)' : 'rgba(239, 68, 68, 0.1)';

    // Area fill path
    const areaD = `${pathD} L ${width - padding},${height - padding} L ${padding},${height - padding} Z`;

    return (
        <svg width="100%" height={height} viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none">
            <path d={areaD} fill={fillColor} />
            <path d={pathD} fill="none" stroke={lineColor} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
    );
}
