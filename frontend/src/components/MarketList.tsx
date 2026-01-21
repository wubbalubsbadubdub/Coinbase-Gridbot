import { useEffect, useState } from 'react';
import { api, Market } from '../api';
import { useWebSocket } from '../hooks/useWebSocket';

interface MarketWithPrice extends Market {
    price?: number;
}

export function MarketList() {
    const [markets, setMarkets] = useState<MarketWithPrice[]>([]);
    const [loading, setLoading] = useState(true);

    // Connect to WebSocket
    // In Dev: proxy handles /api -> backend. WS needs explicit path.
    // Vite proxy is configured for headers, but protocol might need adjustment.
    // Try relative path if proxy supports it, else absolute.
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/api/ws`;
    const { lastMessage, isConnected } = useWebSocket(wsUrl);

    const fetchMarkets = async () => {
        try {
            const data = await api.getMarkets();
            setMarkets(prev => {
                // Merge existing prices with new list to avoid flickering if needed
                // But simplified: just map new data.
                // We want to preserve prices if we have them.
                const priceMap = new Map(prev.map(m => [m.id, m.price]));
                return data.map((m: Market) => ({ ...m, price: priceMap.get(m.id) }));
            });
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchMarkets();
        // Keep polling for Enable/Disable status sync, but maybe less frequent?
        const interval = setInterval(fetchMarkets, 10000);
        return () => clearInterval(interval);
    }, []);

    // Handle WS Messages
    useEffect(() => {
        if (lastMessage && lastMessage.type === 'PRICE_UPDATE') {
            const { market_id, price } = lastMessage.data;
            setMarkets(prev => prev.map(m =>
                m.id === market_id ? { ...m, price: price } : m
            ));
        }
    }, [lastMessage]);

    const toggleMarket = async (id: string, currentStatus: boolean) => {
        try {
            await api.updateMarket(id, { enabled: !currentStatus });
            fetchMarkets();
        } catch (err) {
            alert("Failed to update market");
        }
    };

    if (loading) return <div>Loading Markets...</div>;

    return (
        <div className="card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h2>Markets</h2>
                {isConnected && <span className="badge success">Live</span>}
            </div>
            <table className="market-table">
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Price</th>
                        <th>Ranking</th>
                        <th>Status</th>
                        <th>Action</th>
                    </tr>
                </thead>
                <tbody>
                    {markets.map((m) => (
                        <tr key={m.id}>
                            <td>{m.id}</td>
                            <td>{m.price ? `$${m.price.toFixed(2)}` : '-'}</td>
                            <td>{m.ranking}</td>
                            <td>
                                <span className={m.enabled ? 'badge success' : 'badge warning'}>
                                    {m.enabled ? 'Active' : 'Disabled'}
                                </span>
                            </td>
                            <td>
                                <button onClick={() => toggleMarket(m.id, m.enabled)}>
                                    {m.enabled ? 'Stop' : 'Start'}
                                </button>
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}
