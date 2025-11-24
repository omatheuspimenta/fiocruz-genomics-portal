import React from 'react';

const Badge = ({ children, type = 'default' }) => {
    const styles = {
        default: "bg-slate-100 text-slate-700 border-slate-200",
        success: "bg-emerald-50 text-emerald-700 border-emerald-200",
        warning: "bg-amber-50 text-amber-700 border-amber-200",
        danger: "bg-rose-50 text-rose-700 border-rose-200",
        info: "bg-blue-50 text-blue-700 border-blue-200",
        purple: "bg-purple-50 text-purple-700 border-purple-200"
    };

    let style = styles.default;
    const text = String(children || "").toLowerCase();

    if (type === 'clinical') {
        if (text.includes('pathogenic')) style = styles.danger;
        else if (text.includes('benign')) style = styles.success;
        else if (text.includes('uncertain')) style = styles.warning;
    } else if (type === 'type') {
        if (text === 'snv') style = styles.info;
        else style = styles.purple;
    }

    return (
        <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase border tracking-wide ${style}`}>
            {children || '-'}
        </span>
    );
};

export default Badge;
