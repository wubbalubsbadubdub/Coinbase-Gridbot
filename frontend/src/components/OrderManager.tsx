import { useEffect, useState, useMemo } from 'react';
import { api, Order, Lot } from '../api';
import { formatCurrency, formatCryptoAmount } from '../utils/formatNumber';

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

// Sortable header component
function SortableHeader({
    label,
    sortKey,
    currentSort,
    onSort
}: {
    label: string;
    sortKey: string;
    currentSort: { key: string; direction: 'asc' | 'desc' };
    onSort: (key: string) => void;
}) {
    const isActive = currentSort.key === sortKey;
    return (
        <th
            className="sortable-header"
            onClick={() => onSort(sortKey)}
            style={{ cursor: 'pointer', userSelect: 'none' }}
        >
            {label}
            <span className="sort-indicator">
                {isActive ? (currentSort.direction === 'asc' ? ' ▲' : ' ▼') : ' ○'}
            </span>
        </th>
    );
}

export function OrderManager() {
    const [activeTab, setActiveTab] = useState<'orders' | 'lots' | 'history'>('orders');
    // Pagination State: track current page for each tab
    const [page, setPage] = useState<{ orders: number; lots: number; history: number }>({ orders: 0, lots: 0, history: 0 });
    const PAGE_SIZE = 30;

    const [orders, setOrders] = useState<Order[]>([]);
    const [lots, setLots] = useState<Lot[]>([]);
    const [history, setHistory] = useState<any[]>([]);
    const [loading, setLoading] = useState(false);
    const [toast, setToast] = useState<string | null>(null);

    // Sort states for each tab
    const [orderSort, setOrderSort] = useState<{ key: string; direction: 'asc' | 'desc' }>({ key: 'price', direction: 'desc' });
    const [lotSort, setLotSort] = useState<{ key: string; direction: 'asc' | 'desc' }>({ key: 'buy_price', direction: 'desc' });
    const [historySort, setHistorySort] = useState<{ key: string; direction: 'asc' | 'desc' }>({ key: 'timestamp', direction: 'desc' });

    const showToast = (msg: string) => {
        setToast(msg);
        setTimeout(() => setToast(null), 2000);
    };

    const fetchData = async (targetTab?: string) => {
        const tab = targetTab || activeTab;
        const currentSkip = page[tab as keyof typeof page] * PAGE_SIZE;

        // Optimize: Only fetch data for the active tab (or if forcing refresh)
        // Actually, to keep simple, let's just fetch active tab data
        setLoading(true);
        try {
            if (tab === 'orders') {
                const o = await api.getOrders(PAGE_SIZE, currentSkip);
                setOrders(o);
            } else if (tab === 'lots') {
                const l = await api.getLots(PAGE_SIZE, currentSkip);
                setLots(l);
            } else if (tab === 'history') {
                const h = await api.getHistory(PAGE_SIZE, currentSkip);
                setHistory(h);
            }
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    // Initial load & Tab switch
    useEffect(() => {
        fetchData();
    }, [activeTab, page]);

    // Polling - Only poll if on Page 0 (to avoid shifting rows while browsing history)
    useEffect(() => {
        const interval = setInterval(() => {
            if (page[activeTab] === 0) {
                fetchData();
            }
        }, 5000);
        return () => clearInterval(interval);
    }, [activeTab, page]);

    const handleNext = () => {
        // Simple check: if current data length < PAGE_SIZE, we are definitely at end.
        // (If == PAGE_SIZE, there *might* be more, or might be empty next page. We allow click).
        let currentCount = 0;
        if (activeTab === 'orders') currentCount = orders.length;
        if (activeTab === 'lots') currentCount = lots.length;
        if (activeTab === 'history') currentCount = history.length;

        if (currentCount < PAGE_SIZE) return;

        setPage(prev => ({ ...prev, [activeTab]: prev[activeTab] + 1 }));
    };

    const handlePrev = () => {
        if (page[activeTab] > 0) {
            setPage(prev => ({ ...prev, [activeTab]: prev[activeTab] - 1 }));
        }
    };

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

    // Toggle sort direction or change sort key
    const handleSort = (setSort: React.Dispatch<React.SetStateAction<{ key: string; direction: 'asc' | 'desc' }>>, key: string) => {
        setSort(prev => ({
            key,
            direction: prev.key === key && prev.direction === 'desc' ? 'asc' : 'desc'
        }));
    };

    // Sorted orders
    const sortedOrders = useMemo(() => {
        return [...orders].sort((a, b) => {
            let aVal: any, bVal: any;
            if (orderSort.key === 'side') {
                aVal = a.side;
                bVal = b.side;
            } else if (orderSort.key === 'price') {
                aVal = a.price;
                bVal = b.price;
            } else {
                aVal = a[orderSort.key as keyof Order];
                bVal = b[orderSort.key as keyof Order];
            }

            if (typeof aVal === 'string' && typeof bVal === 'string') {
                return orderSort.direction === 'asc'
                    ? aVal.localeCompare(bVal)
                    : bVal.localeCompare(aVal);
            }
            return orderSort.direction === 'asc'
                ? (aVal - bVal)
                : (bVal - aVal);
        });
    }, [orders, orderSort]);

    // Sorted lots
    const sortedLots = useMemo(() => {
        return [...lots].sort((a, b) => {
            let aVal: any, bVal: any;
            if (lotSort.key === 'buy_price') {
                aVal = a.buy_price;
                bVal = b.buy_price;
            } else if (lotSort.key === 'id') {
                aVal = a.id;
                bVal = b.id;
            } else {
                aVal = a[lotSort.key as keyof Lot];
                bVal = b[lotSort.key as keyof Lot];
            }

            return lotSort.direction === 'asc'
                ? (aVal - bVal)
                : (bVal - aVal);
        });
    }, [lots, lotSort]);

    // Sorted history
    const sortedHistory = useMemo(() => {
        return [...history].sort((a, b) => {
            let aVal: any, bVal: any;
            if (historySort.key === 'timestamp') {
                aVal = new Date(a.timestamp).getTime();
                bVal = new Date(b.timestamp).getTime();
            } else if (historySort.key === 'side') {
                aVal = a.side;
                bVal = b.side;
            } else if (historySort.key === 'price') {
                aVal = a.price;
                bVal = b.price;
            } else {
                aVal = a[historySort.key];
                bVal = b[historySort.key];
            }

            if (typeof aVal === 'string' && typeof bVal === 'string') {
                return historySort.direction === 'asc'
                    ? aVal.localeCompare(bVal)
                    : bVal.localeCompare(aVal);
            }
            return historySort.direction === 'asc'
                ? (aVal - bVal)
                : (bVal - aVal);
        });
    }, [history, historySort]);

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
                                <SortableHeader
                                    label="Side"
                                    sortKey="side"
                                    currentSort={orderSort}
                                    onSort={(key) => handleSort(setOrderSort, key)}
                                />
                                <SortableHeader
                                    label="Price"
                                    sortKey="price"
                                    currentSort={orderSort}
                                    onSort={(key) => handleSort(setOrderSort, key)}
                                />
                                <th>Size</th>
                                <th>Action</th>
                            </tr>
                        </thead>
                        <tbody>
                            {sortedOrders.length === 0 ? (
                                <tr><td colSpan={5}>No Open Orders</td></tr>
                            ) : (
                                sortedOrders.map(o => (
                                    <tr key={o.id}>
                                        <td><CopyableId id={o.id} showToast={showToast} /></td>
                                        <td><span className={`badge ${o.side === 'BUY' ? 'success' : 'error'}`}>{o.side}</span></td>
                                        <td>{formatCurrency(o.price)}</td>
                                        <td>{formatCryptoAmount(o.size)}</td>
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
                                <SortableHeader
                                    label="Lot #"
                                    sortKey="id"
                                    currentSort={lotSort}
                                    onSort={(key) => handleSort(setLotSort, key)}
                                />
                                <th>Buy Order ID</th>
                                <th>Market</th>
                                <SortableHeader
                                    label="Entry Price"
                                    sortKey="buy_price"
                                    currentSort={lotSort}
                                    onSort={(key) => handleSort(setLotSort, key)}
                                />
                                <th>Size</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody>
                            {sortedLots.length === 0 ? (
                                <tr><td colSpan={6}>No Active Lots</td></tr>
                            ) : (
                                sortedLots.map(l => (
                                    <tr key={l.id}>
                                        <td>{l.id}</td>
                                        <td><CopyableId id={l.buy_order_id} showToast={showToast} /></td>
                                        <td>{l.market_id}</td>
                                        <td>{formatCurrency(l.buy_price)}</td>
                                        <td>{formatCryptoAmount(l.buy_size)}</td>
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
                                <SortableHeader
                                    label="Time"
                                    sortKey="timestamp"
                                    currentSort={historySort}
                                    onSort={(key) => handleSort(setHistorySort, key)}
                                />
                                <SortableHeader
                                    label="Side"
                                    sortKey="side"
                                    currentSort={historySort}
                                    onSort={(key) => handleSort(setHistorySort, key)}
                                />
                                <SortableHeader
                                    label="Price"
                                    sortKey="price"
                                    currentSort={historySort}
                                    onSort={(key) => handleSort(setHistorySort, key)}
                                />
                                <th>Size</th>
                                <th>Fee</th>
                            </tr>
                        </thead>
                        <tbody>
                            {sortedHistory.length === 0 ? (
                                <tr><td colSpan={6}>No Trade History</td></tr>
                            ) : (
                                sortedHistory.map(h => (
                                    <tr key={h.id}>
                                        <td><CopyableId id={h.order_id} showToast={showToast} /></td>
                                        <td>{new Date(h.timestamp.includes('Z') || h.timestamp.includes('+') ? h.timestamp : h.timestamp + 'Z').toLocaleTimeString()}</td>
                                        <td className={h.side === 'BUY' ? 'text-success' : 'text-danger'}>{h.side}</td>
                                        <td>{formatCurrency(h.price)}</td>
                                        <td>{formatCryptoAmount(h.size)}</td>
                                        <td>{formatCurrency(h.fee)}</td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                )}
            </div>

            {/* Pagination Controls */}
            <div className="pagination">
                <button
                    onClick={handlePrev}
                    disabled={page[activeTab] === 0}
                    className="nav-btn"
                >
                    Previous
                </button>
                <span className="page-indicator">
                    Page {page[activeTab] + 1}
                </span>
                <button
                    onClick={handleNext}
                    disabled={(activeTab === 'orders' ? orders : activeTab === 'lots' ? lots : history).length < PAGE_SIZE}
                    className="nav-btn"
                >
                    Next
                </button>
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

                /* Sortable header styles */
                .sortable-header {
                    cursor: pointer;
                    user-select: none;
                    transition: background 0.15s ease;
                }
                .sortable-header:hover {
                    background: rgba(59, 130, 246, 0.15);
                }
                .sort-indicator {
                    font-size: 10px;
                    opacity: 0.7;
                    margin-left: 4px;
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

                /* Pagination Styles */
                .pagination {
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    gap: 1rem;
                    padding: 1rem;
                    border-top: 1px solid var(--border);
                }
                .nav-btn {
                    padding: 0.5rem 1rem;
                    border: 1px solid var(--border);
                    background: transparent;
                    color: var(--text-primary);
                    border-radius: 6px;
                    cursor: pointer;
                    transition: all 0.2s;
                }
                .nav-btn:hover:not(:disabled) {
                    background: var(--surface-hover);
                    border-color: var(--accent);
                }
                .nav-btn:disabled {
                    opacity: 0.5;
                    cursor: not-allowed;
                }
                .page-indicator {
                    color: var(--text-secondary);
                    font-size: 0.9rem;
                    font-weight: 500;
                }
            `}</style>
        </div>
    );
}
