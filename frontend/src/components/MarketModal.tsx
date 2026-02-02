import { useEffect, useState } from 'react';
import { api } from '../api';

interface ModalMarket {
    id: string;
    price?: number;
    is_favorite: boolean;
}

interface MarketModalProps {
    isOpen: boolean;
    onClose: () => void;
    onMarketSelected: (marketId: string) => void;
}

export function MarketModal({ isOpen, onClose, onMarketSelected }: MarketModalProps) {
    const [activeTab, setActiveTab] = useState<'all' | 'favorites'>('all');
    const [searchQuery, setSearchQuery] = useState('');
    const [allMarkets, setAllMarkets] = useState<ModalMarket[]>([]);
    const [favoriteIds, setFavoriteIds] = useState<Set<string>>(new Set());
    const [loading, setLoading] = useState(true);

    // Fetch all markets and favorites when modal opens
    useEffect(() => {
        if (!isOpen) return;

        const fetchData = async () => {
            setLoading(true);
            try {
                // Get all available pairs from exchange
                const pairs = await api.getAllPairs();

                // Get user's favorites (markets in DB)
                const dbMarkets = await api.getMarkets(false);
                const favIds = new Set(dbMarkets.filter(m => m.is_favorite).map(m => m.id));

                // Merge: all pairs with favorite status
                const marketsWithFavorites = pairs.map((p: any) => ({
                    id: p.product_id || p.id,
                    price: p.price ? parseFloat(p.price) : undefined,
                    is_favorite: favIds.has(p.product_id || p.id),
                    enabled: false
                }));

                setAllMarkets(marketsWithFavorites);
                setFavoriteIds(favIds);
            } catch (err) {
                console.error('Failed to fetch markets:', err);
            } finally {
                setLoading(false);
            }
        };

        fetchData();
    }, [isOpen]);

    const handleToggleFavorite = async (e: React.MouseEvent, marketId: string) => {
        e.stopPropagation();
        try {
            await api.toggleFavorite(marketId);

            // Update local state
            setFavoriteIds(prev => {
                const next = new Set(prev);
                if (next.has(marketId)) {
                    next.delete(marketId);
                } else {
                    next.add(marketId);
                }
                return next;
            });

            setAllMarkets(prev => prev.map(m =>
                m.id === marketId ? { ...m, is_favorite: !m.is_favorite } : m
            ));
        } catch (err) {
            console.error('Failed to toggle favorite:', err);
        }
    };

    const handleSelectMarket = async (marketId: string) => {
        // Add to favorites if not already
        if (!favoriteIds.has(marketId)) {
            try {
                await api.toggleFavorite(marketId);
            } catch (err) {
                console.error('Failed to add favorite:', err);
            }
        }
        onMarketSelected(marketId);
        onClose();
    };

    // Filter markets based on search and active tab
    const filteredMarkets = allMarkets.filter(m => {
        const matchesSearch = m.id.toLowerCase().includes(searchQuery.toLowerCase());
        const matchesTab = activeTab === 'all' || favoriteIds.has(m.id);
        return matchesSearch && matchesTab;
    });

    if (!isOpen) return null;

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="modal-content" onClick={e => e.stopPropagation()}>
                {/* Header */}
                <div className="modal-header">
                    <button className="back-button" onClick={onClose}>
                        ←
                    </button>
                    <input
                        type="text"
                        className="modal-search"
                        placeholder="Search for a market..."
                        value={searchQuery}
                        onChange={e => setSearchQuery(e.target.value)}
                        autoFocus
                    />
                </div>

                {/* Tabs */}
                <div className="modal-tabs">
                    <button
                        className={activeTab === 'all' ? 'active' : ''}
                        onClick={() => setActiveTab('all')}
                    >
                        All Markets
                    </button>
                    <button
                        className={activeTab === 'favorites' ? 'active' : ''}
                        onClick={() => setActiveTab('favorites')}
                    >
                        Favorites
                    </button>
                </div>

                {/* Market List */}
                <div className="modal-list">
                    {loading ? (
                        <div className="modal-loading">Loading markets...</div>
                    ) : filteredMarkets.length === 0 ? (
                        <div className="modal-empty">
                            {activeTab === 'favorites'
                                ? 'No favorites yet. Add some from All Markets!'
                                : 'No markets found.'}
                        </div>
                    ) : (
                        filteredMarkets.map(market => (
                            <div
                                key={market.id}
                                className="market-row"
                                onClick={() => handleSelectMarket(market.id)}
                            >
                                <div className="market-info">
                                    <span className="market-name">{market.id}</span>
                                </div>
                                <div className="market-right">
                                    <span className="market-price">
                                        {market.price ? `$${market.price.toLocaleString()}` : '-'}
                                    </span>
                                    <button
                                        className={`star-button ${favoriteIds.has(market.id) ? 'favorited' : ''}`}
                                        onClick={(e) => handleToggleFavorite(e, market.id)}
                                        title={favoriteIds.has(market.id) ? 'Remove from favorites' : 'Add to favorites'}
                                    >
                                        {favoriteIds.has(market.id) ? '★' : '☆'}
                                    </button>
                                </div>
                            </div>
                        ))
                    )}
                </div>
            </div>
        </div>
    );
}
