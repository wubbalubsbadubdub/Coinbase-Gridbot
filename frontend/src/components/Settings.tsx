import { useEffect, useState } from 'react';
import { api } from '../api';
import { InfoTooltip } from './InfoTooltip';

export function Settings() {
    const [config, setConfig] = useState<any>({ grid_step_pct: 0.0033, budget: 1000 });
    const [status, setStatus] = useState<string>('');

    useEffect(() => {
        api.getConfig().then(data => {
            setConfig({
                ...data,
                grid_step_pct: data.grid_step_pct ? (data.grid_step_pct * 100).toFixed(2) : '',
                staging_band_depth_pct: data.staging_band_depth_pct ? (data.staging_band_depth_pct * 100).toFixed(2) : '',
                buffer_pct: data.buffer_pct ? (data.buffer_pct * 100).toFixed(2) : '',
                custom_profit_pct: data.custom_profit_pct ? (data.custom_profit_pct * 100).toFixed(2) : '',
            });
        }).catch(console.error);
    }, []);

    const handleSave = async () => {
        try {
            await api.updateConfig({
                grid_step_pct: parseFloat(config.grid_step_pct) / 100,
                budget: parseFloat(config.budget),
                max_open_orders: parseInt(config.max_open_orders),
                staging_band_depth_pct: parseFloat(config.staging_band_depth_pct) / 100,
                profit_mode: config.profit_mode,
                buffer_enabled: config.buffer_enabled,
                buffer_pct: parseFloat(config.buffer_pct || 0) / 100,
                custom_profit_pct: parseFloat(config.custom_profit_pct || 0) / 100,
                monthly_profit_target_usd: parseFloat(config.monthly_profit_target_usd || 0),
                sizing_mode: config.sizing_mode,
                fixed_usd_per_trade: parseFloat(config.fixed_usd_per_trade || 10),
                capital_pct_per_trade: parseFloat(config.capital_pct_per_trade || 1)
            });
            setStatus('Saved!');
            setTimeout(() => setStatus(''), 2000);
        } catch (err) {
            setStatus('Error saving');
        }
    };

    return (
        <div className="card settings-panel">
            <h2>Bot Configuration</h2>

            {/* Grid of input fields - 2 columns on desktop */}
            <div className="settings-grid">
                <div className="field">
                    <label>Grid Step (%) <InfoTooltip text="Distance between grid levels" /></label>
                    <input type="number" step="0.01" value={config.grid_step_pct ?? ''}
                        onChange={e => setConfig({ ...config, grid_step_pct: e.target.value })} />
                </div>
                <div className="field">
                    <label>Budget (USD) <InfoTooltip text="Total capital for trading" /></label>
                    <input type="number" value={config.budget || ''}
                        onChange={e => setConfig({ ...config, budget: e.target.value })} />
                </div>
                <div className="field">
                    <label>Max Orders <InfoTooltip text="Safety limit for open orders" /></label>
                    <input type="number" value={config.max_open_orders || ''}
                        onChange={e => setConfig({ ...config, max_open_orders: e.target.value })} />
                </div>
                <div className="field">
                    <label>Staging Band (%) <InfoTooltip text="How far below price to keep orders" /></label>
                    <input type="number" step="0.1" value={config.staging_band_depth_pct ?? ''}
                        onChange={e => setConfig({ ...config, staging_band_depth_pct: e.target.value })} />
                </div>
            </div>

            <div className="section-divider" />
            <h3>Strategy & Sizing</h3>

            <div className="settings-grid">
                <div className="field">
                    <label>Profit Mode <InfoTooltip text="How profits are handled" /></label>
                    <select value={config.profit_mode || 'STEP'}
                        onChange={e => setConfig({ ...config, profit_mode: e.target.value })}>
                        <option value="STEP">Step (Fixed)</option>
                        <option value="STEP_REINVEST">Reinvest</option>
                        <option value="CUSTOM">Custom</option>
                        <option value="SMART_REINVEST">Smart Reinvest</option>
                    </select>
                </div>
                <div className="field">
                    <label>Sizing Mode <InfoTooltip text="How order size is calculated" /></label>
                    <select value={config.sizing_mode || 'BUDGET_SPLIT'}
                        onChange={e => setConfig({ ...config, sizing_mode: e.target.value })}>
                        <option value="BUDGET_SPLIT">Budget ÷ Orders</option>
                        <option value="FIXED_USD">Fixed USD</option>
                        <option value="CAPITAL_PCT">% of Capital</option>
                    </select>
                </div>

                {config.profit_mode === 'CUSTOM' && (
                    <div className="field">
                        <label>Custom Profit (%)</label>
                        <input type="number" step="0.1" value={config.custom_profit_pct ?? ''}
                            onChange={e => setConfig({ ...config, custom_profit_pct: e.target.value })} />
                    </div>
                )}
                {config.profit_mode === 'SMART_REINVEST' && (
                    <div className="field">
                        <label>Monthly Target ($)</label>
                        <input type="number" value={config.monthly_profit_target_usd || ''}
                            onChange={e => setConfig({ ...config, monthly_profit_target_usd: e.target.value })} />
                    </div>
                )}
                {config.sizing_mode === 'FIXED_USD' && (
                    <div className="field">
                        <label>USD per Trade</label>
                        <input type="number" step="1" value={config.fixed_usd_per_trade || ''}
                            onChange={e => setConfig({ ...config, fixed_usd_per_trade: e.target.value })} />
                    </div>
                )}
                {config.sizing_mode === 'CAPITAL_PCT' && (
                    <div className="field">
                        <label>% per Trade</label>
                        <input type="number" step="0.1" value={config.capital_pct_per_trade || ''}
                            onChange={e => setConfig({ ...config, capital_pct_per_trade: e.target.value })} />
                    </div>
                )}
            </div>

            <div className="section-divider" />
            <h3>Buffer</h3>

            <div className="buffer-row">
                <label className="checkbox-label">
                    <input type="checkbox" checked={config.buffer_enabled || false}
                        onChange={e => setConfig({ ...config, buffer_enabled: e.target.checked })} />
                    Enable Buffer <InfoTooltip text="Wait for price to drop before buying" />
                </label>
                {config.buffer_enabled && (
                    <input type="number" step="0.1" className="buffer-input"
                        value={config.buffer_pct ?? ''} placeholder="%"
                        onChange={e => setConfig({ ...config, buffer_pct: e.target.value })} />
                )}
            </div>

            <div className="save-row">
                <button onClick={handleSave} className="primary">Save Changes</button>
                {status && <span className="status-msg">{status}</span>}
            </div>

            <style>{`
                .settings-panel h2 { margin: 0 0 0.75rem 0; font-size: 1.25rem; }
                .settings-panel h3 { margin: 0 0 0.5rem 0; font-size: 0.9rem; color: var(--text-secondary); }
                
                .settings-grid {
                    display: grid;
                    grid-template-columns: repeat(2, 1fr);
                    gap: 0.5rem 1rem;
                }
                @media (max-width: 500px) {
                    .settings-grid { grid-template-columns: 1fr; }
                }
                
                .field { display: flex; flex-direction: column; gap: 0.2rem; }
                .field label { font-size: 0.75rem; color: var(--text-secondary); display: flex; align-items: center; gap: 0.25rem; }
                .field input, .field select {
                    padding: 0.4rem 0.5rem;
                    border-radius: 4px;
                    border: 1px solid var(--border);
                    background: #1e1e2e;
                    color: white;
                    font-size: 0.9rem;
                }
                .field select option {
                    background: #1e1e2e;
                    color: white;
                    padding: 0.5rem;
                }
                
                .section-divider {
                    height: 1px;
                    background: var(--border);
                    margin: 0.75rem 0 0.5rem 0;
                }
                
                .buffer-row {
                    display: flex;
                    align-items: center;
                    gap: 1rem;
                }
                .checkbox-label {
                    display: flex;
                    align-items: center;
                    gap: 0.4rem;
                    font-size: 0.85rem;
                }
                .buffer-input { width: 70px; padding: 0.3rem 0.5rem; }
                
                .save-row {
                    display: flex;
                    align-items: center;
                    gap: 1rem;
                    margin-top: 1rem;
                }
                .status-msg { font-size: 0.85rem; color: #22c55e; }
            `}</style>
        </div>
    );
}
