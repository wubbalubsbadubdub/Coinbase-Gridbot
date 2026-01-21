import { useState } from 'react';
import { BotStatusPanel } from './components/BotStatus';
import { MarketList } from './components/MarketList';
import { OrderManager } from './components/OrderManager';
import { Settings } from './components/Settings';
import { PriceChart } from './components/PriceChart';
import { api } from './api';

function App() {
    const [view, setView] = useState<'dashboard' | 'settings'>('dashboard');

    const handleStop = async () => {
        if (confirm("EMERGENCY STOP: Are you sure you want to PAUSE the bot and CANCEL ALL OPEN ORDERS?")) {
            try {
                await api.emergencyStop();
                alert("Bot Stopped and Orders Canceled.");
            } catch (e) {
                alert("Failed to trigger stop.");
            }
        }
    };

    return (
        <div className="container">
            <header className="app-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h1>Coinbase Gridbot</h1>
                <div style={{ display: 'flex', gap: '1rem' }}>
                    <button onClick={() => setView('dashboard')} disabled={view === 'dashboard'}>Dashboard</button>
                    <button onClick={() => setView('settings')} disabled={view === 'settings'}>Settings</button>
                    <button onClick={handleStop} style={{ background: 'var(--danger)', fontWeight: 'bold' }}>STOP ALL</button>
                </div>
            </header>

            {view === 'dashboard' ? (
                <>
                    <div className="dashboard-grid">
                        <BotStatusPanel />
                        <MarketList />
                    </div>

                    <div style={{ marginTop: '2rem' }}>
                        <PriceChart marketId="BTC-USD" />
                    </div>

                    <div style={{ marginTop: '2rem' }}>
                        <OrderManager />
                    </div>
                </>
            ) : (
                <div style={{ marginTop: '2rem' }}>
                    <Settings />
                </div>
            )}
        </div>
    )
}

export default App;
