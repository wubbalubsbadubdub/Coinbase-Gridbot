export interface Market {
    id: string;
    enabled: boolean;
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
    id: string;
    market_id: string;
    buy_price: number;
    size: number;
    sell_order_id?: string;
    status: string;
}

export const api = {
    getMarkets: async (): Promise<Market[]> => {
        const res = await fetch('/api/markets/');
        return res.json();
    },

    updateMarket: async (id: string, data: Partial<Market>): Promise<Market> => {
        const res = await fetch(`/api/markets/${id}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        });
        return res.json();
    },

    getBotStatus: async (): Promise<BotStatus> => {
        const res = await fetch('/api/bot/status');
        return res.json();
    },
    getOrders: async (): Promise<Order[]> => {
        const res = await fetch('/api/orders/?status=OPEN');
        return res.json();
    },
    cancelOrder: async (id: string): Promise<void> => {
        await fetch(`/api/orders/${id}`, { method: 'DELETE' });
    },
    getLots: async (): Promise<Lot[]> => {
        const res = await fetch('/api/lots/');
        return res.json();
    },
    getConfig: async (): Promise<any> => {
        const res = await fetch('/api/config/');
        return res.json();
    },
    updateConfig: async (data: any): Promise<any> => {
        const res = await fetch('/api/config/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        return res.json();
    },
    emergencyStop: async (): Promise<void> => {
        await fetch('/api/control/cancel_all', { method: 'POST' });
    },
    getHistory: async (): Promise<any[]> => {
        const res = await fetch('/api/history/fills');
        return res.json();
    }
};
