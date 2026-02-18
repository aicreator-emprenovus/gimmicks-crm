/**
 * Format currency for Ecuador style: $1.234,56
 */
export const formatCurrency = (value) => {
    if (value === null || value === undefined || isNaN(value)) return '$0,00';
    const formatted = Number(value).toFixed(2);
    const [intPart, decPart] = formatted.split('.');
    const formattedInt = intPart.replace(/\B(?=(\d{3})+(?!\d))/g, '.');
    return `$${formattedInt},${decPart}`;
};
