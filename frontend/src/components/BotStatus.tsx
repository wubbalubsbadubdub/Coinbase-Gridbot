import { useEffect, useState } from 'react';
import { api, BotStatus } from '../api';

export function BotStatusPanel() {
    const [status, setStatus] = useState<BotStatus | null>(null);

    useEffect(() => {
        const fetchStatus = async () => {
            try {
                const data = await api.getBotStatus();
                setStatus(data);
            } catch (err) {
                console.error(err);
            }
        };
        fetchStatus();
        const interval = setInterval(fetchStatus, 5000);
        return () => clearInterval(interval);
    }, []);

    if (!status) return <div>Loading Status...</div>;

    return (
        <div className="card status-panel">
            <h2>Bot Status</h2>
            <div className="status-grid">
                <div className="stat">
                    <label>Environment</label>
                    <span>{status.env}</span>
                </div>
                <div className="stat">
                    <label>Exchange</label>
                    <span>{status.exchange_type}</span>
                </div>
                <div className="stat">
                    <label>Trading Mode</label>
                    <span className={status.live_trading ? 'badge success' : (status.paper_mode ? 'badge warning' : 'badge error')}>
                        {status.live_trading ? 'LIVE' : (status.paper_mode ? 'PAPER TRADING' : 'OFF')}
                    </span>
                </div>
                <div className="stat">
                    <label>Engine</label>
                    <span className={status.running ? 'badge success' : 'badge error'}>
                        {status.running ? 'RUNNING' : 'STOPPED'}
                    </span>
                </div>
                <div className="stat">
                    <label>Active Markets</label>
                    <span>{status.active_markets}</span>
                </div>
            </div>
        </div>
    );
}
