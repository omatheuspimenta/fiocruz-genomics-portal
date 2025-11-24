import React from 'react';
import * as LucideIcons from 'lucide-react';

const Icon = ({ name, size = 20, className = "" }) => {
    // Convert kebab-case to PascalCase (e.g., "alert-circle" -> "AlertCircle")
    const pascalName = name
        .split('-')
        .map(w => w.charAt(0).toUpperCase() + w.slice(1))
        .join('');

    const IconComp = LucideIcons[pascalName];

    if (!IconComp) {
        console.warn(`Icon "${name}" not found`);
        return <span className="text-xs text-gray-400">{name}</span>;
    }

    return <IconComp size={size} className={className} />;
};

export default Icon;
