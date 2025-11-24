import React, { useState } from 'react';
import Header from './components/Header';
import SearchHero from './components/SearchHero';
import StatCard from './components/StatCard';
import Icon from './components/Icon';
import VariantTable from './components/VariantTable';
import FrequencyPie from './components/Charts/FrequencyPie';
import PopulationBar from './components/Charts/PopulationBar';
import VariantTypeBar from './components/Charts/VariantTypeBar';
import QualityHistogram from './components/Charts/QualityHistogram';
import ConservationScatter from './components/Charts/ConservationScatter';
import ConservationBar from './components/Charts/ConservationBar';
import { useSearch } from './hooks/useSearch';

function App() {
    const {
        rawData, filteredVariants, loading, error,
        filters, setFilters, handleSearch, stats
    } = useSearch();

    const [activeTab, setActiveTab] = useState('frequency');
    const [showFilters, setShowFilters] = useState(false);

    const handleDownload = () => {
        if (!filteredVariants.length) return;
        const keys = Array.from(new Set(filteredVariants.flatMap(Object.keys)));
        const csvContent = [
            keys.join(","),
            ...filteredVariants.map(row => keys.map(k => {
                let val = row[k];
                if (val === null || val === undefined) return "";
                if (typeof val === 'object') return `"${JSON.stringify(val).replace(/"/g, '""')}"`;
                return `"${String(val).replace(/"/g, '""')}"`;
            }).join(","))
        ].join("\n");

        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement("a");
        link.href = URL.createObjectURL(blob);
        link.download = `variants_export.csv`;
        link.click();
    };

    return (
        <div className="min-h-screen flex flex-col bg-slate-50 text-slate-900 font-sans">
            <Header />
            <SearchHero onSearch={handleSearch} loading={loading} />

            <main className="flex-1 max-w-7xl w-full mx-auto px-4 py-8">
                {error && (
                    <div className="bg-red-50 border border-red-200 text-red-800 p-4 rounded-lg flex items-center gap-3 mb-8 animate-fade-in shadow-sm">
                        <Icon name="alert-triangle" />
                        <p className="font-medium">{error}</p>
                    </div>
                )}

                {rawData && (
                    <div className="space-y-6 animate-fade-in">
                        {stats && (
                            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
                                <StatCard title="Total Variants" value={stats.count.toLocaleString()} icon="layers" />
                                <StatCard title="Variant Types" value={stats.uniqueTypes} icon="git-branch" />
                                <StatCard title="Mean AF" value={stats.meanAF.toExponential(1)} icon="activity" subtext="Global gnomAD" />
                                <StatCard title="Max AF" value={stats.maxAF.toFixed(3)} icon="trending-up" />
                                <StatCard title="ClinVar" value={stats.clinvarCount} icon="clipboard-check" color="text-purple-600" />
                                <StatCard title="Coverage" value={stats.coverage} icon="pie-chart" color="text-slate-600" />
                            </div>
                        )}

                        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
                            <div className="p-4 border-b border-slate-100 bg-slate-50/50 flex flex-col md:flex-row md:items-center justify-between gap-4">
                                <div className="flex gap-1 bg-slate-200/60 p-1 rounded-lg overflow-x-auto no-scrollbar">
                                    {[
                                        { id: 'frequency', label: 'Frequency', icon: 'bar-chart-2' },
                                        { id: 'populations', label: 'Populations', icon: 'globe' },
                                        { id: 'conservation', label: 'Conservation', icon: 'shield' },
                                        { id: 'variantTypes', label: 'Types', icon: 'dna' },
                                        { id: 'quality', label: 'Quality', icon: 'check-circle' },
                                        { id: 'table', label: 'Data Table', icon: 'table' }
                                    ].map(tab => (
                                        <button
                                            key={tab.id}
                                            onClick={() => setActiveTab(tab.id)}
                                            className={`px-3 py-1.5 text-sm font-medium rounded-md flex items-center gap-2 transition-all whitespace-nowrap ${activeTab === tab.id ? 'bg-white text-brand-700 shadow-sm' : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/50'}`}
                                        >
                                            <Icon name={tab.icon} size={14} /> {tab.label}
                                        </button>
                                    ))}
                                </div>
                                <div className="flex items-center gap-2">
                                    <button
                                        onClick={() => setShowFilters(!showFilters)}
                                        className={`px-4 py-2 text-sm font-medium rounded-lg border flex items-center gap-2 transition-colors ${showFilters ? 'bg-brand-50 border-brand-200 text-brand-700' : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50'}`}
                                    >
                                        <Icon name="filter" size={16} /> Filters
                                    </button>
                                    <button onClick={handleDownload} disabled={!filteredVariants.length} className={`px-4 py-2 text-sm font-medium text-white rounded-lg flex items-center gap-2 shadow-sm ${!filteredVariants.length ? 'bg-slate-300 cursor-not-allowed' : 'bg-emerald-600 hover:bg-emerald-700'}`}>
                                        <Icon name="download" size={16} /> Export
                                    </button>
                                </div>
                            </div>

                            {showFilters && (
                                <div className="p-6 bg-slate-50 border-b border-slate-200 grid grid-cols-1 md:grid-cols-3 gap-6 animate-fade-in">
                                    <div className="space-y-2">
                                        <label className="text-xs font-bold text-slate-500 uppercase">Frequency (AF) Range</label>
                                        <div className="flex items-center gap-2">
                                            <input type="range" min="0" max="0.1" step="0.0001" value={filters.minAF} onChange={e => setFilters({ ...filters, minAF: parseFloat(e.target.value) })} className="flex-1" />
                                            <span className="text-xs font-mono bg-white border px-2 py-1 rounded">{filters.minAF.toFixed(4)}</span>
                                        </div>
                                    </div>
                                    {['consequence', 'variantType', 'clinvar'].map(f => (
                                        <div key={f} className="space-y-2">
                                            <label className="text-xs font-bold text-slate-500 uppercase">{f.replace(/([A-Z])/g, ' $1').trim()}</label>
                                            <input
                                                type="text"
                                                placeholder="Filter..."
                                                value={filters[f]}
                                                onChange={e => setFilters({ ...filters, [f]: e.target.value })}
                                                className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-brand-500 outline-none"
                                            />
                                        </div>
                                    ))}
                                </div>
                            )}

                            <div className="p-6 min-h-[500px]">
                                {filteredVariants.length === 0 ? (
                                    <div className="text-center py-24 animate-fade-in">
                                        <div className="inline-block p-4 bg-slate-100 rounded-full mb-4 text-slate-400">
                                            <Icon name="search-x" size={48} />
                                        </div>
                                        <h2 className="text-xl font-semibold text-slate-700">No variants found</h2>
                                        <p className="text-slate-500 mt-2">Try adjusting filters or your search query.</p>
                                    </div>
                                ) : (
                                    stats && (
                                        <>
                                            {activeTab === 'frequency' && (
                                                <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 animate-fade-in h-[450px]">
                                                    <div className="lg:col-span-2 bg-white border border-slate-100 rounded-xl p-4 shadow-sm">
                                                        <h4 className="text-sm font-bold text-slate-700 mb-4">Allele Frequency Distribution</h4>
                                                        <FrequencyPie data={stats.pieData} />
                                                    </div>
                                                    <div className="bg-brand-50/50 border border-brand-100 rounded-xl p-6">
                                                        <h4 className="text-sm font-bold text-brand-900 uppercase mb-4">Quick Insights</h4>
                                                        <ul className="space-y-4 text-sm text-brand-800">
                                                            <li className="flex gap-3">
                                                                <Icon name="info" size={18} className="text-brand-500 shrink-0" />
                                                                <span>The majority of variants ({stats.pieData[0]?.value}) fall into the <strong>{stats.pieData[0]?.name}</strong> category.</span>
                                                            </li>
                                                            <li className="flex gap-3">
                                                                <Icon name="alert-circle" size={18} className="text-purple-500 shrink-0" />
                                                                <span><strong>{stats.clinvarCount}</strong> variants have clinical significance reported in ClinVar.</span>
                                                            </li>
                                                            <li className="flex gap-3">
                                                                <Icon name="trending-up" size={18} className="text-emerald-500 shrink-0" />
                                                                <span>Max Allele Frequency observed is <strong>{(stats.maxAF * 100).toFixed(2)}%</strong>.</span>
                                                            </li>
                                                        </ul>
                                                    </div>
                                                </div>
                                            )}

                                            {activeTab === 'populations' && (
                                                <div className="h-[450px] bg-white border border-slate-100 rounded-xl p-6 shadow-sm animate-fade-in">
                                                    <h4 className="text-sm font-bold text-slate-700 mb-6">Global Population Frequencies (Mean AF)</h4>
                                                    <PopulationBar data={stats.popData} />
                                                </div>
                                            )}

                                            {activeTab === 'variantTypes' && (
                                                <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 animate-fade-in h-[450px]">
                                                    <div className="lg:col-span-2 bg-white border border-slate-100 rounded-xl p-6 shadow-sm">
                                                        <h4 className="text-sm font-bold text-slate-700 mb-2">Variant Type Distribution</h4>
                                                        <VariantTypeBar data={stats.variantTypeData} />
                                                    </div>
                                                    <div className="bg-emerald-50/50 border border-emerald-100 rounded-xl p-6 overflow-y-auto custom-scroll">
                                                        <h4 className="text-sm font-bold text-emerald-900 uppercase mb-4">Breakdown</h4>
                                                        <div className="space-y-3">
                                                            {stats.variantTypeData.map((type, i) => (
                                                                <div key={i} className="flex justify-between items-center bg-white p-3 rounded-lg shadow-sm">
                                                                    <span className="text-sm text-slate-600 font-medium">{type.name}</span>
                                                                    <span className="text-sm font-bold text-emerald-600">{type.value}</span>
                                                                </div>
                                                            ))}
                                                        </div>
                                                    </div>
                                                </div>
                                            )}

                                            {activeTab === 'quality' && (
                                                <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 animate-fade-in h-[450px]">
                                                    <div className="bg-white border border-slate-100 rounded-xl p-6 shadow-sm">
                                                        <h4 className="text-sm font-bold text-slate-700 mb-4">Quality Score Histogram</h4>
                                                        <QualityHistogram data={stats.qualityDist} />
                                                    </div>
                                                    <div className="bg-amber-50/50 border border-amber-100 rounded-xl p-6">
                                                        <h4 className="text-sm font-bold text-amber-900 uppercase mb-4">Quality Analysis</h4>
                                                        <p className="text-sm text-slate-600 mb-4">
                                                            Quality scores indicate the confidence in the variant call. Higher scores (right side) generally indicate higher confidence and better sequencing depth.
                                                        </p>
                                                        <div className="space-y-2">
                                                            {stats.qualityDist.map((d, i) => (
                                                                <div key={i} className="flex items-center gap-2">
                                                                    <div className="w-24 text-xs font-bold text-slate-500">{d.name}</div>
                                                                    <div className="flex-1 h-2 bg-slate-200 rounded-full overflow-hidden">
                                                                        <div className="h-full bg-amber-400" style={{ width: `${stats.count > 0 ? (d.value / stats.count) * 100 : 0}%` }}></div>
                                                                    </div>
                                                                    <div className="w-12 text-xs text-right font-mono">{d.value}</div>
                                                                </div>
                                                            ))}
                                                        </div>
                                                    </div>
                                                </div>
                                            )}

                                            {activeTab === 'conservation' && (
                                                <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 animate-fade-in h-[450px]">
                                                    <div className="bg-white border border-slate-100 rounded-xl p-6 shadow-sm">
                                                        <h4 className="text-sm font-bold text-slate-700 mb-2">PhyloP vs Allele Frequency</h4>
                                                        <ConservationScatter data={stats.scatterData} />
                                                    </div>
                                                    <div className="bg-white border border-slate-100 rounded-xl p-6 shadow-sm">
                                                        <h4 className="text-sm font-bold text-slate-700 mb-2">Conservation Score Averages</h4>
                                                        <ConservationBar data={stats.conservationData} />
                                                    </div>
                                                </div>
                                            )}

                                            {activeTab === 'table' && (
                                                <div className="animate-fade-in">
                                                    <VariantTable
                                                        variants={filteredVariants}
                                                        onVariantClick={(vid) => handleSearch('variant', vid)}
                                                    />
                                                    <div className="mt-4 text-right text-xs text-slate-400">
                                                        Showing {filteredVariants.length} variants
                                                    </div>
                                                </div>
                                            )}
                                        </>
                                    )
                                )}
                            </div>
                        </div>
                    </div>
                )}
            </main>
        </div>
    );
}

export default App;
