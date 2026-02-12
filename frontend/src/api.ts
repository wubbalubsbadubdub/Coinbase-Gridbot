export interface Market {
    id: string;
    enabled: boolean;
    is_favorite: boolean;
    ranking: number;
    settings?: any;
}

export interface BotStatus {
    env: string;
    live_trading: boolean;
    exchange_type: string;
    paper_mode: boolean;
    running: boolean;
    active_markets: number;
}

export interface Order {
    id: string;
    market_id: string;
    side: string;
    price: number;
    size: number;
    status: string;
    created_at?: string;
}

export interface Lot {
    id: number;
    market_id: string;
    buy_order_id: string;
    buy_price: number;
    buy_size: number;
    buy_time?: string;
    sell_order_id?: string;
    sell_price?: number;
    status: string;
    realized_pnl: number;
}

// Shared error handler — throws a clear error if the backend returns a non-OK status
async function handleResponse<T>(res: Response): Promise<T> {
    if (!res.ok) {
        let detail = res.statusText;
        try {
            const body = await res.json();
            detail = body.detail || JSON.stringify(body);
        } catch { /* body wasn't JSON */ }
        throw new Error(`API ${res.status}: ${detail}`);
    }
    return res.json();
}

export const api = {
    getMarkets: async (favoritesOnly = false): Promise<Market[]> => {
        const url = favoritesOnly ? '/api/markets/?favorites_only=true' : '/api/markets/';
        const res = await fetch(url);
        return handleResponse<Market[]>(res);
    },

    getAllPairs: async (): Promise<any[]> => {
        const res = await fetch('/api/markets/all-pairs');
        return handleResponse<any[]>(res);
    },

    toggleFavorite: async (id: string): Promise<any> => {
        const res = await fetch(`/api/markets/${id}/favorite`, { method: 'POST' });
        return handleResponse<any>(res);
    },

    startMarket: async (id: string): Promise<any> => {
        const res = await fetch(`/api/markets/${id}/start`, { method: 'POST' });
        return handleResponse<any>(res);
    },

    stopMarket: async (id: string): Promise<any> => {
        const res = await fetch(`/api/markets/${id}/stop`, { method: 'POST' });
        return handleResponse<any>(res);
    },

    updateMarket: async (id: string, data: Partial<Market>): Promise<Market> => {
        const res = await fetch(`/api/markets/${id}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        });
        return handleResponse<Market>(res);
    },

    getBotStatus: async (): Promise<BotStatus> => {
        const res = await fetch('/api/bot/status');
        return handleResponse<BotStatus>(res);
    },
    getOrders: async (limit = 30, skip = 0): Promise<Order[]> => {
        const res = await fetch(`/api/orders/?status=OPEN&limit=${limit}&skip=${skip}`);
        return handleResponse<Order[]>(res);
    },
    cancelOrder: async (id: string): Promise<void> => {
        const res = await fetch(`/api/orders/${id}`, { method: 'DELETE' });
        if (!res.ok) {
            const body = await res.json().catch(() => ({}));
            throw new Error(`API ${res.status}: ${body.detail || res.statusText}`);
        }
    },
    getLots: async (limit = 30, skip = 0): Promise<Lot[]> => {
        const res = await fetch(`/api/lots/?limit=${limit}&skip=${skip}`);
        return handleResponse<Lot[]>(res);
    },
    getConfig: async (): Promise<any> => {
        const res = await fetch('/api/config/');
        return handleResponse<any>(res);
    },
    updateConfig: async (data: any): Promise<any> => {
        const res = await fetch('/api/config/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        return handleResponse<any>(res);
    },
    emergencyStop: async (): Promise<void> => {
        const res = await fetch('/api/control/cancel_all', { method: 'POST' });
        if (!res.ok) {
            throw new Error(`Emergency stop failed: ${res.status}`);
        }
    },
    getHistory: async (limit = 30, skip = 0): Promise<any[]> => {
        const res = await fetch(`/api/history/fills?limit=${limit}&skip=${skip}`);
        return handleResponse<any[]>(res);
    },

    // Stats API
    getCapitalSummary: async (): Promise<CapitalSummary> => {
        const res = await fetch('/api/stats/capital-summary');
        return handleResponse<CapitalSummary>(res);
    },
    getPnLBreakdown: async (): Promise<PnLBreakdown> => {
        const res = await fetch('/api/stats/pnl-breakdown');
        return handleResponse<PnLBreakdown>(res);
    },
    getPnLHistory: async (days: number = 30): Promise<PnLHistory> => {
        const res = await fetch(`/api/stats/pnl-history?days=${days}`);
        return handleResponse<PnLHistory>(res);
    }
};

// Stats Types
export interface CapitalSummary {
    starting_capital: number;
    current_capital: number;
    net_change_usd: number;
    net_change_pct: number;
    deployed_capital: number;
    available_capital: number;
    unrealized_pnl: number;
}

export interface PnLBreakdown {
    today_pnl: number;
    today_pct: number;
    week_pnl: number;
    week_pct: number;
    month_pnl: number;
    month_pct: number;
    year_pnl: number;
    year_pct: number;
    lifetime_pnl: number;
    lifetime_pct: number;
}

export interface DailyPnLPoint {
    date: string;
    pnl: number;
    cumulative: number;
}

export interface PnLHistory {
    daily_pnl: DailyPnLPoint[];
}
