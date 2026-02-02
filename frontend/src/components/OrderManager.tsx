import { useEffect, useState } from 'react';
import { api, Order, Lot } from '../api';

// Reusable component for copyable IDs
function CopyableId({ id, showToast }: { id: string; showToast: (msg: string) => void }) {
    const handleCopy = async () => {
        try {
            await navigator.clipboard.writeText(id);
            showToast('✓ Copied!');
        } catch (err) {
            // Fallback for older browsers/mobile
            const textArea = document.createElement('textarea');
            textArea.value = id;
            document.body.appendChild(textArea);
            textArea.select();
            document.execCommand('copy');
            document.body.removeChild(textArea);
            showToast('✓ Copied!');
        }
    };

    return (
        <span className="copyable-id" onClick={handleCopy} title={`Tap to copy: ${id}`}>
            {id.slice(0, 8)}...
        </span>
    );
}

export function OrderManager() {
    const [activeTab, setActiveTab] = useState<'orders' | 'lots' | 'history'>('orders');
    const [orders, setOrders] = useState<Order[]>([]);
    const [lots, setLots] = useState<Lot[]>([]);
    const [history, setHistory] = useState<any[]>([]);
    const [loading, setLoading] = useState(false);
    const [toast, setToast] = useState<string | null>(null);

    const showToast = (msg: string) => {
        setToast(msg);
        setTimeout(() => setToast(null), 2000);
    };

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
                {loading && <span className="loading-spinner" title="Refreshing...">⟳</span>}
            </div>

            <div className="tab-content">

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
                                        <td><CopyableId id={o.id} showToast={showToast} /></td>
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
                                <th>Lot #</th>
                                <th>Buy Order ID</th>
                                <th>Market</th>
                                <th>Entry Price</th>
                                <th>Size</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody>
                            {lots.length === 0 ? (
                                <tr><td colSpan={6}>No Active Lots</td></tr>
                            ) : (
                                lots.map(l => (
                                    <tr key={l.id}>
                                        <td>{l.id}</td>
                                        <td><CopyableId id={l.buy_order_id} showToast={showToast} /></td>
                                        <td>{l.market_id}</td>
                                        <td>${l.buy_price.toFixed(2)}</td>
                                        <td>{l.buy_size}</td>
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
                                <th>Order ID</th>
                                <th>Time</th>
                                <th>Side</th>
                                <th>Price</th>
                                <th>Size</th>
                                <th>Fee</th>
                            </tr>
                        </thead>
                        <tbody>
                            {history.length === 0 ? (
                                <tr><td colSpan={6}>No Trade History</td></tr>
                            ) : (
                                history.map(h => (
                                    <tr key={h.id}>
                                        <td><CopyableId id={h.order_id} showToast={showToast} /></td>
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

            {/* Toast notification */}
            {toast && (
                <div className="toast">{toast}</div>
            )}

            <style>{`
                .tabs {
                    display: flex;
                    gap: 0.5rem;
                    margin-bottom: 1rem;
                    border-bottom: 1px solid var(--border);
                    padding-bottom: 0;
                }
                .tabs button {
                    background: transparent;
                    color: var(--text-secondary);
                    border-radius: 8px 8px 0 0;
                    padding: 0.5rem 1rem;
                    border-bottom: 2px solid transparent;
                    margin-bottom: -1px;
                }
                .tabs button.active {
                    color: var(--accent);
                    border-bottom: 2px solid var(--accent);
                    background: rgba(59, 130, 246, 0.1);
                }
                .tabs button:hover {
                    color: var(--text-primary);
                }

                /* Loading spinner */
                .loading-spinner {
                    margin-left: auto;
                    font-size: 18px;
                    color: var(--accent);
                    animation: spin 1s linear infinite;
                }
                @keyframes spin {
                    from { transform: rotate(0deg); }
                    to { transform: rotate(360deg); }
                }

                /* Copyable ID styles - mobile friendly */
                .copyable-id {
                    cursor: pointer;
                    color: var(--accent);
                    padding: 8px 4px;
                    margin: -8px -4px;
                    border-radius: 4px;
                    display: inline-block;
                    min-width: 44px;
                    min-height: 44px;
                    line-height: 28px;
                }
                .copyable-id:hover {
                    background: rgba(59, 130, 246, 0.15);
                }
                .copyable-id:active {
                    background: rgba(59, 130, 246, 0.3);
                }

                /* Toast notification */
                .toast {
                    position: fixed;
                    bottom: 80px;
                    left: 50%;
                    transform: translateX(-50%);
                    background: #22c55e;
                    color: white;
                    padding: 12px 24px;
                    border-radius: 8px;
                    font-weight: 600;
                    font-size: 14px;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
                    z-index: 1000;
                    animation: fadeInOut 2s ease-in-out;
                }
                @keyframes fadeInOut {
                    0% { opacity: 0; transform: translateX(-50%) translateY(10px); }
                    15% { opacity: 1; transform: translateX(-50%) translateY(0); }
                    85% { opacity: 1; transform: translateX(-50%) translateY(0); }
                    100% { opacity: 0; transform: translateX(-50%) translateY(-10px); }
                }
            `}</style>
        </div>
    );
}
