import React from 'react';
import Badge from './Badge';

const VariantTable = ({ variants, onVariantClick }) => {
    return (
        <div className="overflow-x-auto custom-scroll border border-slate-200 rounded-xl max-h-[600px]">
            <table className="min-w-full divide-y divide-slate-200">
                <thead className="bg-slate-50 sticky top-0 z-10 shadow-sm">
                    <tr>
                        {['Variant ID', 'RSID', 'Gene', 'Position', 'Change', 'Type', 'Consequence', 'AF', 'Clinical', 'Qual'].map(h => (
                            <th key={h} className="px-6 py-3 text-left text-xs font-bold text-slate-500 uppercase tracking-wider">{h}</th>
                        ))}
                    </tr>
                </thead>
                <tbody className="bg-white divide-y divide-slate-200">
                    {variants.map((v, idx) => (
                        <tr key={idx} className="hover:bg-blue-50/30 transition-colors group">
                            <td className="px-6 py-4 whitespace-nowrap text-sm font-mono font-medium">
                                <button
                                    onClick={() => onVariantClick(v.vid)}
                                    className="text-brand-600 hover:text-brand-800 hover:underline focus:outline-none text-left"
                                >
                                    {v.vid}
                                </button>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-500">{v.rsid || '-'}</td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-600">
                                {v.gene || (Array.isArray(v.genes) ? v.genes.join(', ') : '-') || '-'}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-600">{v.position}</td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-slate-700">{v.ref} <span className="text-slate-300">→</span> {v.alt}</td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm">
                                <Badge type="type">{v.variant_type}</Badge>
                            </td>
                            <td className="px-6 py-4 text-sm text-slate-700 max-w-xs truncate" title={(v.all_consequences || []).join(', ')}>
                                {(v.all_consequences || []).slice(0, 1).join('').replace(/_/g, ' ')}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-slate-700">
                                {v.gnomad_af ? v.gnomad_af.toExponential(2) : <span className="text-slate-300">-</span>}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm">
                                <Badge type="clinical">{v.clinvar_significance || '-'}</Badge>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-500 font-mono">
                                {v.quality ? v.quality.toFixed(1) : '-'}
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
};

export default VariantTable;
