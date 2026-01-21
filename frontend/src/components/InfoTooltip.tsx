import { useState } from 'react';

interface InfoTooltipProps {
    text: string;
}

export function InfoTooltip({ text }: InfoTooltipProps) {
    const [isVisible, setIsVisible] = useState(false);

    return (
        <span
            className="info-tooltip-container"
            onMouseEnter={() => setIsVisible(true)}
            onMouseLeave={() => setIsVisible(false)}
            onClick={() => setIsVisible(!isVisible)}
            style={{ position: 'relative', display: 'inline-block', marginLeft: '6px', cursor: 'pointer' }}
        >
            <span style={{
                background: '#444',
                borderRadius: '50%',
                width: '18px',
                height: '18px',
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '12px',
                fontWeight: 'bold',
                color: '#aaa',
                border: '1px solid #666'
            }}>i</span>

            {isVisible && (
                <div style={{
                    position: 'absolute',
                    bottom: '125%',
                    left: '50%',
                    transform: 'translateX(-50%)',
                    background: '#222',
                    color: '#fff',
                    padding: '8px 12px',
                    borderRadius: '4px',
                    fontSize: '0.85rem',
                    width: '200px',
                    zIndex: 100,
                    boxShadow: '0 4px 6px rgba(0,0,0,0.3)',
                    border: '1px solid #444',
                    textAlign: 'center',
                    lineHeight: '1.4'
                }}>
                    {text}
                    <div style={{
                        position: 'absolute',
                        top: '100%',
                        left: '50%',
                        marginLeft: '-5px',
                        borderWidth: '5px',
                        borderStyle: 'solid',
                        borderColor: '#222 transparent transparent transparent'
                    }}></div>
                </div>
            )}
        </span>
    );
}
