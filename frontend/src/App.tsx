import { useState, useEffect } from 'react';
import { BotStatusPanel } from './components/BotStatus';
import { MarketList } from './components/MarketList';
import { OrderManager } from './components/OrderManager';
import { Settings } from './components/Settings';
import { PriceChart, ChartState } from './components/PriceChart';
import { MarketModal } from './components/MarketModal';
import { CapitalOverview } from './components/CapitalOverview';
import { PnLBreakdownPanel } from './components/PnLBreakdown';
import { api } from './api';

function App() {
    const [view, setView] = useState<'dashboard' | 'settings'>('dashboard');
    const [selectedMarket, setSelectedMarket] = useState<string>('BTC-USD');
    const [runningMarket, setRunningMarket] = useState<string | null>(null);
    const [isMarketModalOpen, setIsMarketModalOpen] = useState(false);

    // Chart state lifted here so it persists across navigation
    const [chartState, setChartState] = useState<ChartState>({
        data: [],
        anchor: null,
        gridTop: null
    });

    // Poll for running market (Highlander rule means max 1)
    useEffect(() => {
        const checkRunning = async () => {
            try {
                const all = await api.getMarkets();
                const running = all.find(m => m.enabled);
                setRunningMarket(running ? running.id : null);
            } catch (e) {
                console.error(e);
            }
        };
        checkRunning();
        const interval = setInterval(checkRunning, 5000);
        return () => clearInterval(interval);
    }, []);

    const activeViewMarket = runningMarket || selectedMarket;

    // Reset chart when market changes
    useEffect(() => {
        setChartState({ data: [], anchor: null, gridTop: null });
    }, [activeViewMarket]);

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

    const handleMarketSelected = (marketId: string) => {
        setSelectedMarket(marketId);
    };

    return (
        <div className="container">
            <header className="app-header">
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                    <h1>Gridbot</h1>
                    {runningMarket && <span className="badge success">RUNNING: {runningMarket}</span>}
                </div>
                <div className="header-buttons">
                    <button onClick={() => setView('dashboard')} disabled={view === 'dashboard'}>Dashboard</button>
                    <button onClick={() => setView('settings')} disabled={view === 'settings'}>Settings</button>
                    <button onClick={handleStop} style={{ background: 'var(--danger)', fontWeight: 'bold' }}>STOP ALL</button>
                </div>
            </header>

            {view === 'dashboard' ? (
                <>
                    <div className="dashboard-layout">
                        <div className="dashboard-sidebar">
                            <button
                                className="search-trigger"
                                onClick={() => setIsMarketModalOpen(true)}
                            >
                                Search Markets (e.g. SOL-USD)...
                            </button>
                            <MarketList
                                favoritesOnly={true}
                                onSelectMarket={setSelectedMarket}
                            />
                        </div>
                        <div className="dashboard-main">
                            <BotStatusPanel />

                            <div className="stats-row">
                                <CapitalOverview />
                                <PnLBreakdownPanel />
                            </div>

                            <div className="chart-wrapper">
                                <PriceChart
                                    marketId={activeViewMarket}
                                    chartState={chartState}
                                    onChartStateChange={setChartState}
                                />
                            </div>
                        </div>
                    </div>

                    <div style={{ marginTop: '1rem' }}>
                        <OrderManager />
                    </div>
                </>
            ) : (
                <div style={{ marginTop: '2rem' }}>
                    <Settings />
                </div>
            )}

            <MarketModal
                isOpen={isMarketModalOpen}
                onClose={() => setIsMarketModalOpen(false)}
                onMarketSelected={handleMarketSelected}
            />
        </div>
    )
}

export default App;
