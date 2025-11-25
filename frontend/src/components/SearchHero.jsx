import React, { useState } from 'react';
import Icon from './Icon';

const SearchHero = ({ onSearch, loading }) => {
    const [searchType, setSearchType] = useState('gene');
    const [query, setQuery] = useState('');

    const handleSubmit = (e) => {
        e.preventDefault();
        if (query) onSearch(searchType, query);
    };

    return (
        <div className="bg-white border-b border-slate-200 shadow-sm py-8">
            <div className="max-w-3xl mx-auto px-4">
                <form onSubmit={handleSubmit} className="space-y-4">
                    <div className="flex justify-center gap-6 mb-2">
                        {['gene', 'variant', 'region'].map(type => (
                            <label key={type} className="flex items-center cursor-pointer group select-none">
                                <input
                                    type="radio" name="searchType"
                                    checked={searchType === type}
                                    onChange={() => setSearchType(type)}
                                    className="w-4 h-4 accent-brand-600 cursor-pointer"
                                />
                                <span className={`ml-2 font-medium text-sm capitalize transition-colors ${searchType === type ? 'text-brand-700 font-bold' : 'text-slate-500'}`}>
                                    {type}
                                </span>
                            </label>
                        ))}
                    </div>
                    <div className="flex shadow-lg shadow-slate-200/50 rounded-xl overflow-hidden border border-slate-200 transition-all focus-within:ring-4 ring-brand-500/10 ring-offset-1">
                        <input
                            type="text"
                            className="flex-1 px-6 py-4 outline-none text-lg text-slate-700 placeholder-slate-300"
                            placeholder={
                            searchType === "gene"
                                ? "Enter a gene name (e.g., TP53)"
                                : searchType === "variant"
                                ? "Enter a variant (e.g., 17:7670699-C-A or rs121912664)"
                                : "Enter a genomic region: chr:start-end (e.g., 17:7670000-7671000)"
                            }
                            value={query}
                            onChange={(e) => setQuery(e.target.value)}
                        />
                        <button type="submit" disabled={loading} className="bg-brand-600 hover:bg-brand-700 text-white px-8 font-semibold transition-colors flex items-center gap-2 min-w-[120px] justify-center">
                            {loading ? <Icon name="loader-2" className="animate-spin" /> : <><Icon name="search" /> Search</>}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};

export default SearchHero;
