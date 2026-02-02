import { useEffect, useState } from 'react';
import { useWebSocket } from '../hooks/useWebSocket';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine, CartesianGrid } from 'recharts';

export function PriceChart({ marketId }: { marketId: string }) {
    const [data, setData] = useState<{ time: string, price: number }[]>([]);
    const [anchor, setAnchor] = useState<number | null>(null);
    const [gridTop, setGridTop] = useState<number | null>(null);

    // Connect to WS
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/api/ws`;
    const { lastMessage } = useWebSocket(wsUrl);

    useEffect(() => {
        if (!lastMessage || lastMessage.type !== 'PRICE_UPDATE') return;
        if (lastMessage.data.market_id !== marketId) return;

        const newPoint = {
            time: new Date().toLocaleTimeString('en-US', { hour12: false }), // HH:mm:ss
            price: lastMessage.data.price
        };

        if (lastMessage.data.anchor) setAnchor(lastMessage.data.anchor);
        if (lastMessage.data.grid_top) setGridTop(lastMessage.data.grid_top);

        setData(prev => {
            const newData = [...prev, newPoint];
            if (newData.length > 100) newData.shift(); // Keep last 100 points
            return newData;
        });
    }, [lastMessage, marketId]);

    if (data.length === 0) return <div className="card" style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>Waiting for data...</div>;

    return (
        <div className="card" style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
            <h2 style={{ margin: '0 0 0.5rem 0' }}>{marketId} Price</h2>
            <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={data}>
                    <defs>
                        <linearGradient id="colorPrice" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#8884d8" stopOpacity={0.3} />
                            <stop offset="95%" stopColor="#8884d8" stopOpacity={0} />
                        </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" opacity={0.1} />
                    <XAxis
                        dataKey="time"
                        minTickGap={30}
                        tick={{ fill: '#aaa', fontSize: 12 }}
                    />
                    <YAxis
                        domain={['auto', 'auto']}
                        tickFormatter={(val) => `$${val.toLocaleString()}`}
                        tick={{ fill: '#aaa', fontSize: 12 }}
                        width={80}
                    />
                    <Tooltip
                        contentStyle={{ backgroundColor: '#222', borderColor: '#444' }}
                        labelStyle={{ color: '#fff' }}
                        formatter={(val: number | string | Array<number | string> | undefined) => {
                            if (typeof val === 'number') return [`$${val.toLocaleString()}`, 'Price'];
                            if (val === undefined) return ['', 'Price'];
                            return [val, 'Price'];
                        }}
                    />
                    <Area
                        type="monotone"
                        dataKey="price"
                        stroke="#8884d8"
                        fillOpacity={1}
                        fill="url(#colorPrice)"
                        isAnimationActive={false}
                    />
                    {anchor && (
                        <ReferenceLine y={anchor} stroke="red" strokeDasharray="3 3" label={{ position: 'insideTopRight', value: 'Anchor', fill: 'red' }} />
                    )}
                    {gridTop && (
                        <ReferenceLine y={gridTop} stroke="orange" strokeDasharray="3 3" label={{ position: 'insideTopRight', value: 'Grid Top', fill: 'orange' }} />
                    )}
                </AreaChart>
            </ResponsiveContainer>
        </div>
    );
}
