/**
 * Formats a number as a currency string (USD) with dynamic decimal precision.
 * Logic based on standard crypto exchange display patterns (Coinbase, etc).
 * 
 * @param price The price to format
 * @param forceDecimals Optional: force a specific number of decimals
 * @returns Formatted string (e.g., "$1,234.56", "$0.0912")
 */
export function formatCurrency(price: number | undefined | null, forceDecimals?: number): string {
    if (price === undefined || price === null) return '-';

    // If strict decimals requested
    if (forceDecimals !== undefined) {
        return `$${price.toLocaleString('en-US', { minimumFractionDigits: forceDecimals, maximumFractionDigits: forceDecimals })}`;
    }

    // Dynamic precision based on magnitude
    if (price >= 1000) {
        // Large values: 2 decimals (e.g. $65,000.00)
        return `$${price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    } else if (price >= 1) {
        // Medium values: 2 decimals
        return `$${price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    } else if (price >= 0.0001) {
        // Sub-dollar (e.g. $0.09143, $0.00122): 5 decimals
        return `$${price.toLocaleString('en-US', { minimumFractionDigits: 5, maximumFractionDigits: 5 })}`;
    } else if (price === 0) {
        return '$0.00';
    } else {
        // Micro-values: 8 decimals
        return `$${price.toLocaleString('en-US', { minimumFractionDigits: 8, maximumFractionDigits: 8 })}`;
    }
}

/**
 * Formats a crypto amount (size) with appropriate precision.
 * 
 * @param amount The amount to format
 * @returns Formatted string (e.g., "0.1234", "1,000.00")
 */
export function formatCryptoAmount(amount: number | undefined | null): string {
    if (amount === undefined || amount === null) return '-';

    if (amount >= 100) {
        // Large amounts: 2 decimals (e.g. 1,082.59)
        return amount.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    } else if (amount >= 1) {
        // Normal amounts: 4 decimals (e.g. 1.2345)
        return amount.toLocaleString('en-US', { minimumFractionDigits: 4, maximumFractionDigits: 4 });
    } else {
        // Small amounts: 6 decimals max, remove trailing zeros
        // using parseFloat(fixed) strips trailing zeros
        return parseFloat(amount.toFixed(6)).toString();
    }
}
