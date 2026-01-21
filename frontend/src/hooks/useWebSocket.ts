import { useEffect, useRef, useState } from 'react';

type WebSocketMessage = {
    type: string;
    data: any;
};

export const useWebSocket = (url: string) => {
    const [isConnected, setIsConnected] = useState(false);
    const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
    const wsRef = useRef<WebSocket | null>(null);

    useEffect(() => {
        // Handle reconnection logic with a simple timeout if needed, 
        // but for now simple connect
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
                    setLastMessage(parsed);
                } catch (e) {
                    console.error('Failed to parse WS message:', event.data);
                }
            };

            socket.onclose = () => {
                console.log('WebSocket Disconnected');
                setIsConnected(false);
                // Simple reconnect
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
