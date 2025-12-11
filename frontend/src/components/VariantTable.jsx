import React from 'react';
import Badge from './Badge';


const VariantTable = ({ variants, onVariantClick, currentPage = 1, totalPages = 1, onPageChange, totalVariants }) => {
    // Internal pagination removed in favor of server-side pagination

    const handlePageChange = (newPage) => {
        if (newPage >= 1 && newPage <= totalPages && onPageChange) {
            onPageChange(newPage);
        }
    };

    return (
        <div className="space-y-4">
            <div className="overflow-x-auto custom-scroll border border-slate-200 rounded-xl max-h-[600px]">
                <table className="min-w-full divide-y divide-slate-200">
                    <thead className="bg-slate-50 sticky top-0 z-10 shadow-sm">
                        <tr>
                            {['Variant ID', 'RSID', 'Gene', 'Position', 'Change', 'Type', 'Consequence', 'AF', 'ClinVar'].map(h => (
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
                                        {v.vid ? v.vid.replace(/-/g, ':') : ''}
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
                                    {(v.all_consequences || []).slice(0, 1).join('').replace(/_/g, ' ').replace(/3 prime/g, "3'")}
                                </td>
                                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-slate-700">
                                    {v.gnomad_af ? Number(v.gnomad_af).toFixed(4) : <span className="text-slate-300">-</span>}
                                </td>
                                <td className="px-6 py-4 whitespace-nowrap text-sm">
                                    <Badge type="clinical">{v.clinvar_significance || '-'}</Badge>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            {totalPages > 1 && (
                <div className="flex items-center justify-between px-4 py-3 bg-white border border-slate-200 rounded-lg shadow-sm">
                    <div className="text-sm text-slate-600">
                        Page <span className="font-medium">{currentPage}</span> of <span className="font-medium">{totalPages}</span>
                        {totalVariants > 0 && <span> ({totalVariants} total variants)</span>}
                    </div>
                    <div className="flex items-center gap-2">
                        <button
                            onClick={() => handlePageChange(currentPage - 1)}
                            disabled={currentPage === 1}
                            className={`px-3 py-1 text-sm font-medium rounded-md border transition-colors ${currentPage === 1 ? 'bg-slate-50 text-slate-400 border-slate-200 cursor-not-allowed' : 'bg-white text-slate-700 border-slate-300 hover:bg-slate-50'}`}
                        >
                            Previous
                        </button>
                        <div className="flex items-center gap-1">
                            {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                                let pageNum;
                                if (totalPages <= 5) {
                                    pageNum = i + 1;
                                } else if (currentPage <= 3) {
                                    pageNum = i + 1;
                                } else if (currentPage >= totalPages - 2) {
                                    pageNum = totalPages - 4 + i;
                                } else {
                                    pageNum = currentPage - 2 + i;
                                }

                                return (
                                    <button
                                        key={pageNum}
                                        onClick={() => handlePageChange(pageNum)}
                                        className={`w-8 h-8 flex items-center justify-center rounded-md text-sm font-medium transition-colors ${currentPage === pageNum ? 'bg-brand-600 text-white' : 'text-slate-600 hover:bg-slate-100'}`}
                                    >
                                        {pageNum}
                                    </button>
                                );
                            })}
                        </div>
                        <button
                            onClick={() => handlePageChange(currentPage + 1)}
                            disabled={currentPage === totalPages}
                            className={`px-3 py-1 text-sm font-medium rounded-md border transition-colors ${currentPage === totalPages ? 'bg-slate-50 text-slate-400 border-slate-200 cursor-not-allowed' : 'bg-white text-slate-700 border-slate-300 hover:bg-slate-50'}`}
                        >
                            Next
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
};

export default VariantTable;
