import { useEffect, useRef, useState } from 'react';

type WebSocketMessage = {
    type: string;
    data: any;
};

export const useWebSocket = (url: string) => {
    const [isConnected, setIsConnected] = useState(false);
    const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);

    // Throttling state
    const lastMessageRef = useRef<WebSocketMessage | null>(null);
    const wsRef = useRef<WebSocket | null>(null);

    useEffect(() => {
        // Simple Throttle: Flush latest message every 200ms (5fps)
        const interval = setInterval(() => {
            if (lastMessageRef.current) {
                setLastMessage(lastMessageRef.current);
                // Optional: Clear ref if you only want to update on CHANGE? 
                // But here we just want to ensure UI eventually matches Ref.
                // React setState is smart enough to skip if equality check passes, 
                // but objects are new references every time.
                // So let's rely on React's batching or just acceptable 5fps re-render.
                // To be stricter: 
                // if (lastMessageRef.current !== lastMessage) ... but lastMessage is state.
            }
        }, 200);

        return () => clearInterval(interval);
    }, []);

    useEffect(() => {
        const connect = () => {
            const socket = new WebSocket(url);
            wsRef.current = socket;

            socket.onopen = () => {
                console.log('WebSocket Connected');
                setIsConnected(true);
            };

            socket.onmessage = (event) => {
                try {
                    const parsed = JSON.parse(event.data);
                    // Update Ref immediately, but State later
                    lastMessageRef.current = parsed;
                } catch (e) {
                    console.error('Failed to parse WS message:', event.data);
                }
            };

            socket.onclose = () => {
                console.log('WebSocket Disconnected');
                setIsConnected(false);
                setTimeout(connect, 3000);
            };

            socket.onerror = (error) => {
                console.error('WebSocket Error:', error);
            };
        };

        connect();

        return () => {
            if (wsRef.current) {
                wsRef.current.close();
            }
        };
    }, [url]);

    return { isConnected, lastMessage };
};
