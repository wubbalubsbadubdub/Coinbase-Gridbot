import { useEffect, useState } from 'react';
import { api, Order, Lot } from '../api';

export function OrderManager() {
    const [activeTab, setActiveTab] = useState<'orders' | 'lots' | 'history'>('orders');
    const [orders, setOrders] = useState<Order[]>([]);
    const [lots, setLots] = useState<Lot[]>([]);
    const [history, setHistory] = useState<any[]>([]);
    const [loading, setLoading] = useState(false);

    const fetchData = async () => {
        setLoading(true);
        try {
            const [o, l, h] = await Promise.all([
                api.getOrders(),
                api.getLots(),
                api.getHistory()
            ]);
            setOrders(o);
            setLots(l);
            setHistory(h);
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
        const interval = setInterval(fetchData, 5000);
        return () => clearInterval(interval);
    }, []);

    const handleCancel = async (id: string) => {
        if (confirm('Cancel Order?')) {
            try {
                await api.cancelOrder(id);
                fetchData();
            } catch (err) {
                alert("Failed to cancel order");
            }
        }
    };

    return (
        <div className="card">
            <div className="tabs">
                <button className={activeTab === 'orders' ? 'active' : ''} onClick={() => setActiveTab('orders')}>Open Orders</button>
                <button className={activeTab === 'lots' ? 'active' : ''} onClick={() => setActiveTab('lots')}>Active Lots</button>
                <button className={activeTab === 'history' ? 'active' : ''} onClick={() => setActiveTab('history')}>History</button>
            </div>

            <div className="tab-content">
                {loading && <div style={{ opacity: 0.5 }}>Refreshing...</div>}

                {activeTab === 'orders' && (
                    <table className="order-table">
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>Side</th>
                                <th>Price</th>
                                <th>Size</th>
                                <th>Action</th>
                            </tr>
                        </thead>
                        <tbody>
                            {orders.length === 0 ? (
                                <tr><td colSpan={5}>No Open Orders</td></tr>
                            ) : (
                                orders.map(o => (
                                    <tr key={o.id}>
                                        <td title={o.id}>{o.id.slice(0, 8)}...</td>
                                        <td><span className={`badge ${o.side === 'BUY' ? 'success' : 'error'}`}>{o.side}</span></td>
                                        <td>${o.price.toFixed(2)}</td>
                                        <td>{o.size}</td>
                                        <td><button onClick={() => handleCancel(o.id)}>Cancel</button></td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                )}

                {activeTab === 'lots' && (
                    <table className="order-table">
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>Market</th>
                                <th>Entry Price</th>
                                <th>Size</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody>
                            {lots.length === 0 ? (
                                <tr><td colSpan={5}>No Active Lots</td></tr>
                            ) : (
                                lots.map(l => (
                                    <tr key={l.id}>
                                        <td title={l.id}>{l.id.substring(0, 8)}...</td>
                                        <td>{l.market_id}</td>
                                        <td>${l.buy_price.toFixed(2)}</td>
                                        <td>{l.size}</td>
                                        <td><span className="badge success">{l.status}</span></td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                )}

                {activeTab === 'history' && (
                    <table className="order-table">
                        <thead>
                            <tr>
                                <th>Time</th>
                                <th>Side</th>
                                <th>Price</th>
                                <th>Size</th>
                                <th>Fee</th>
                            </tr>
                        </thead>
                        <tbody>
                            {history.length === 0 ? (
                                <tr><td colSpan={5}>No Trade History</td></tr>
                            ) : (
                                history.map(h => (
                                    <tr key={h.id}>
                                        <td>{new Date(h.timestamp).toLocaleTimeString()}</td>
                                        <td className={h.side === 'BUY' ? 'text-success' : 'text-danger'}>{h.side}</td>
                                        <td>{h.price}</td>
                                        <td>{h.size}</td>
                                        <td>{h.fee}</td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                )}
            </div>
            <style>{`
                .tabs {
                    display: flex;
                    gap: 1rem;
                    margin-bottom: 1rem;
                    border-bottom: 1px solid var(--border);
                }
                .tab-header button {
                    background: transparent;
                    color: var(--text-secondary);
                    border-radius: 0;
                    padding: 0.5rem 1rem;
                }
                .tab-header button.active {
                    color: var(--accent);
                    border-bottom: 2px solid var(--accent);
                }
                .tab-header button:hover {
                    color: var(--text-primary);
                }
            `}</style>
        </div>
    );
}
