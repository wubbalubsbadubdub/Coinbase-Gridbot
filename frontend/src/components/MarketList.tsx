import { useEffect, useState } from 'react';
import { api, Market } from '../api';
import { useWebSocket } from '../hooks/useWebSocket';

interface MarketWithPrice extends Market {
    price?: number;
}

export function MarketList({
    favoritesOnly = false,
    onSelectMarket
}: {
    favoritesOnly?: boolean,
    onSelectMarket?: (id: string) => void
}) {
    const [markets, setMarkets] = useState<MarketWithPrice[]>([]);
    const [loading, setLoading] = useState(true);

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/api/ws`;
    const { lastMessage, isConnected } = useWebSocket(wsUrl);

    const fetchMarkets = async () => {
        try {
            // If favoritesOnly, backend filters. But we also need to know if ANY market is running?
            // Actually, for this list we just want the favorites.
            const data = await api.getMarkets(favoritesOnly);
            setMarkets(prev => {
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
        const interval = setInterval(fetchMarkets, 5000);
        return () => clearInterval(interval);
    }, [favoritesOnly]);

    useEffect(() => {
        if (lastMessage && lastMessage.type === 'PRICE_UPDATE') {
            const { market_id, price } = lastMessage.data;
            setMarkets(prev => prev.map(m =>
                m.id === market_id ? { ...m, price: price } : m
            ));
        }
    }, [lastMessage]);

    const handleStartStop = async (e: React.MouseEvent, id: string, isEnabled: boolean) => {
        e.stopPropagation(); // prevent row click
        try {
            if (isEnabled) {
                await api.stopMarket(id);
            } else {
                await api.startMarket(id);
            }
            fetchMarkets();
        } catch (err) {
            alert("Failed to update market status");
        }
    };

    const handleUnfavorite = async (e: React.MouseEvent, id: string) => {
        e.stopPropagation();
        if (confirm(`Remove ${id} from favorites?`)) {
            await api.toggleFavorite(id);
            fetchMarkets();
        }
    };

    if (loading) return <div>Loading...</div>;

    return (
        <div className="card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h2>{favoritesOnly ? 'Favorite Markets' : 'All Markets'}</h2>
                {isConnected && <span className="badge success">Live</span>}
            </div>
            <table className="market-table">
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Price</th>
                        <th>Status</th>
                        <th>Action</th>
                    </tr>
                </thead>
                <tbody>
                    {markets.map((m) => (
                        <tr
                            key={m.id}
                            onClick={() => onSelectMarket && onSelectMarket(m.id)}
                            style={{ cursor: 'pointer', background: m.enabled ? '#3df2' : 'transparent' }}
                        >
                            <td>
                                {m.id}
                                {favoritesOnly && (
                                    <button
                                        onClick={(e) => handleUnfavorite(e, m.id)}
                                        style={{ marginLeft: '8px', padding: '2px 5px', fontSize: '0.8rem', background: 'transparent', border: 'none', color: '#666' }}
                                        title="Remove Favorite"
                                    >
                                        ★
                                    </button>
                                )}
                            </td>
                            <td>{m.price ? `$${m.price.toFixed(2)}` : '-'}</td>
                            <td>
                                <span className={m.enabled ? 'badge success' : 'badge warning'}>
                                    {m.enabled ? 'RUNNING' : 'Idle'}
                                </span>
                            </td>
                            <td>
                                <button
                                    onClick={(e) => handleStartStop(e, m.id, m.enabled)}
                                    className={m.enabled ? 'danger' : 'success'}
                                >
                                    {m.enabled ? 'Stop' : 'Start'}
                                </button>
                            </td>
                        </tr>
                    ))}
                    {markets.length === 0 && (
                        <tr>
                            <td colSpan={4} style={{ textAlign: 'center', color: '#888' }}>
                                No favorites yet. Search above to add one!
                            </td>
                        </tr>
                    )}
                </tbody>
            </table>
        </div>
    );
}
