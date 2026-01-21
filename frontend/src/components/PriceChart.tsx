import { useEffect, useState } from 'react';
import { useWebSocket } from '../hooks/useWebSocket';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';

export function PriceChart({ marketId }: { marketId: string }) {
    const [data, setData] = useState<{ time: string, price: number }[]>([]);

    // Connect to WS
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/api/ws`;
    const { lastMessage } = useWebSocket(wsUrl);

    useEffect(() => {
        if (!lastMessage || lastMessage.type !== 'PRICE_UPDATE') return;
        if (lastMessage.data.market_id !== marketId) return;

        const newPoint = {
            time: new Date().toLocaleTimeString(),
            price: lastMessage.data.price
        };

        setData(prev => {
            const newData = [...prev, newPoint];
            if (newData.length > 50) newData.shift(); // Keep last 50 points
            return newData;
        });
    }, [lastMessage, marketId]);

    if (data.length === 0) return <div className="card">Waiting for market data...</div>;

    const min = Math.min(...data.map(d => d.price));
    const max = Math.max(...data.map(d => d.price));
    const domain = [min * 0.999, max * 1.001];

    return (
        <div className="card" style={{ height: '400px' }}>
            <h2>{marketId} Price</h2>
            <ResponsiveContainer width="100%" height="90%">
                <LineChart data={data}>
                    <XAxis dataKey="time" hide />
                    <YAxis domain={domain} />
                    <Tooltip />
                    <Line type="monotone" dataKey="price" stroke="#8884d8" dot={false} isAnimationActive={false} />
                    {/* Placeholder for Anchor/Grid levels if we fetched them from status */}
                </LineChart>
            </ResponsiveContainer>
        </div>
    );
}
