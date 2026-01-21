import { useEffect, useState } from 'react';
import { api } from '../api';
import { InfoTooltip } from './InfoTooltip';

export function Settings() {
    const [config, setConfig] = useState<any>({ grid_step_pct: 0.0033, budget: 1000 });
    const [status, setStatus] = useState<string>('');

    useEffect(() => {
        api.getConfig().then(setConfig).catch(console.error);
    }, []);

    const handleSave = async () => {
        try {
            await api.updateConfig({
                grid_step_pct: parseFloat(config.grid_step_pct),
                budget: parseFloat(config.budget),
                max_open_orders: parseInt(config.max_open_orders),
                staging_band_depth_pct: parseFloat(config.staging_band_depth_pct),
                profit_mode: config.profit_mode,
                buffer_enabled: config.buffer_enabled,
                buffer_pct: parseFloat(config.buffer_pct)
            });
            setStatus('Saved!');
            setTimeout(() => setStatus(''), 2000);
        } catch (err) {
            setStatus('Error saving');
        }
    };

    return (
        <div className="card">
            <h2>Bot Configuration</h2>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', maxWidth: '400px' }}>
                <div>
                    <label>
                        Grid Step %
                        <InfoTooltip text="The percentage distance between each buy/sell grid level. (e.g. 0.005 = 0.5%)" />
                    </label>
                    <input
                        type="number" step="0.0001"
                        value={config.grid_step_pct}
                        onChange={e => setConfig({ ...config, grid_step_pct: e.target.value })}
                    />
                </div>
                <div>
                    <label>
                        Budget (USD)
                        <InfoTooltip text="Total amount of USD the bot is allowed to use for this market." />
                    </label>
                    <input
                        type="number"
                        value={config.budget || ''}
                        onChange={e => setConfig({ ...config, budget: e.target.value })}
                    />
                </div>
                <div>
                    <label>
                        Max Open Orders
                        <InfoTooltip text="Safety limit. The bot will stop placing new orders if open orders exceed this count." />
                    </label>
                    <input
                        type="number"
                        value={config.max_open_orders || ''}
                        onChange={e => setConfig({ ...config, max_open_orders: e.target.value })}
                    />
                </div>

                <hr style={{ margin: '1rem 0', borderColor: '#333' }} />
                <h3>Advanced Strategy</h3>

                <div>
                    <label>
                        Staging Band Depth %
                        <InfoTooltip text="How far below the current price to keep 'active' buy orders. Saves API limits." />
                    </label>
                    <input
                        type="number" step="0.001"
                        value={config.staging_band_depth_pct || ''}
                        onChange={e => setConfig({ ...config, staging_band_depth_pct: e.target.value })}
                    />
                </div>

                <div>
                    <label>
                        Profit Mode
                        <InfoTooltip text="STEP: Reinvest profit into position size. CUSTOM: Currently same as Step (placeholder)." />
                    </label>
                    <select
                        value={config.profit_mode || 'STEP'}
                        onChange={e => setConfig({ ...config, profit_mode: e.target.value })}
                        style={{ width: '100%', padding: '8px', background: '#333', color: 'white', border: '1px solid #555' }}
                    >
                        <option value="STEP">Step (Re-invest)</option>
                        <option value="CUSTOM">Custom Target</option>
                    </select>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <input
                        type="checkbox"
                        checked={config.buffer_enabled || false}
                        onChange={e => setConfig({ ...config, buffer_enabled: e.target.checked })}
                    />
                    <label>
                        Enable Buffer
                        <InfoTooltip text="Prevents buying the absolute top. If enabled, the bot waits for price to drop by 'Buffer %' from the High before placing the first grid level. (GridTop = AnchorHigh * (1 - buffer_pct))" />
                    </label>
                </div>

                {config.buffer_enabled && (
                    <div>
                        <label>Buffer %</label>
                        <input
                            type="number" step="0.001"
                            value={config.buffer_pct || ''}
                            onChange={e => setConfig({ ...config, buffer_pct: e.target.value })}
                        />
                    </div>
                )}

                <button onClick={handleSave} className="primary">
                    Save Changes
                </button>
                {status && <span>{status}</span>}
            </div>
        </div>
    );
}
