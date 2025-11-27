import { useState, useEffect, useMemo } from 'react';
import { searchVariants } from '../api/client';

// --- HELPERS ---
const calculateMean = (arr) => arr.length ? arr.reduce((a, b) => a + b, 0) / arr.length : 0;
const countValues = (arr) => arr.reduce((acc, curr) => { acc[curr] = (acc[curr] || 0) + 1; return acc; }, {});
const categorizeFrequency = (af) => {
    if (af === null || af === undefined) return 'Unknown';
    if (af < 0.0001) return 'Ultra-rare (<0.01%)';
    if (af < 0.001) return 'Rare (0.01-0.1%)';
    if (af < 0.01) return 'Low freq (0.1-1%)';
    if (af < 0.05) return 'Common (1-5%)';
    return 'Very common (>5%)';
};

export const useSearch = () => {
    const [rawData, setRawData] = useState(null);
    const [filteredVariants, setFilteredVariants] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [filters, setFilters] = useState({
        minAF: 0, maxAF: 1, consequence: '', variantType: '', clinvar: '', rsid: '', gene: ''
    });

    // Pagination state
    const [currentPage, setCurrentPage] = useState(1);
    const [totalPages, setTotalPages] = useState(1);
    const [totalVariants, setTotalVariants] = useState(0);
    const [currentSearchType, setCurrentSearchType] = useState(null);
    const [currentQuery, setCurrentQuery] = useState('');

    const handleSearch = async (type, query, page = 1) => {
        setLoading(true);
        setError(null);
        // Don't clear data immediately to avoid flash if just changing page
        if (type !== currentSearchType || query !== currentQuery) {
            setRawData(null);
            setFilteredVariants([]);
            setCurrentPage(1);
        } else {
            setCurrentPage(page);
        }

        setCurrentSearchType(type);
        setCurrentQuery(query);

        try {
            const result = await searchVariants(type, query, page);
            setRawData(result);

            // Update pagination info from response
            if (result.total_pages) setTotalPages(result.total_pages);
            else setTotalPages(1);

            if (result.total_variants) setTotalVariants(result.total_variants);
            else setTotalVariants(result.variants ? result.variants.length : (result.variant ? 1 : 0));

        } catch (err) {
            setError(err.message);
            setRawData(null);
            setFilteredVariants([]);
        } finally {
            setLoading(false);
        }
    };

    const changePage = (page) => {
        if (currentSearchType && currentQuery) {
            handleSearch(currentSearchType, currentQuery, page);
        }
    };

    useEffect(() => {
        if (!rawData) {
            setFilteredVariants([]);
            return;
        }
        let variants = [];
        if (rawData.variant) variants = [rawData.variant];
        else if (rawData.variants) variants = rawData.variants;

        const filtered = variants.filter(v => {
            const af = v.gnomad_af !== undefined ? v.gnomad_af : 0;
            const cons = (v.all_consequences || []).join(' ').toLowerCase();
            const vType = (v.variant_type || '').toLowerCase();
            const clinvarSig = (v.clinvar_significance || '').toLowerCase();
            const rsidVal = (v.rsid || '').toLowerCase();
            const geneVal = (v.gene || '').toUpperCase();

            if (af < filters.minAF || af > filters.maxAF) return false;
            if (filters.consequence && !cons.includes(filters.consequence.toLowerCase())) return false;
            if (filters.variantType && !vType.includes(filters.variantType.toLowerCase())) return false;
            if (filters.clinvar && !clinvarSig.includes(filters.clinvar.toLowerCase())) return false;
            if (filters.rsid && !rsidVal.includes(filters.rsid.toLowerCase())) return false;

            // Handle gene filtering (check both gene string and genes array)
            if (filters.gene) {
                const filterGene = filters.gene.toUpperCase();
                const geneStr = (v.gene || '').toUpperCase();
                const genesList = Array.isArray(v.genes) ? v.genes.map(g => g.toUpperCase()) : [];

                if (!geneStr.includes(filterGene) && !genesList.some(g => g.includes(filterGene))) {
                    return false;
                }
            }
            return true;
        });
        setFilteredVariants(filtered);
    }, [rawData, filters]);

    const stats = useMemo(() => {
        // If we have server-side statistics (Global Stats), use them directly
        if (rawData && rawData.statistics) {
            return rawData.statistics;
        }

        // Fallback to client-side calculation (e.g. for single variant search or legacy)
        if (!filteredVariants || filteredVariants.length === 0) return null;

        const afs = filteredVariants.map(v => v.gnomad_af).filter(n => typeof n === 'number');
        const maxAF = afs.length ? Math.max(...afs) : 0;
        const meanAF = calculateMean(afs);
        const clinvarCount = filteredVariants.filter(v => v.clinvar_significance).length;

        const freqCats = countValues(filteredVariants.map(v => categorizeFrequency(v.gnomad_af)));
        const pieData = Object.entries(freqCats).map(([name, value]) => ({ name, value })).sort((a, b) => b.value - a.value);

        const pops = ['gnomad_afr_af', 'gnomad_amr_af', 'gnomad_eas_af', 'gnomad_nfe_af', 'gnomad_sas_af'];
        const popData = pops.map(pop => {
            const vals = filteredVariants.map(v => v[pop]).filter(n => typeof n === 'number');
            return { name: pop.replace('gnomad_', '').replace('_af', '').toUpperCase(), val: calculateMean(vals) };
        });

        const scatterData = filteredVariants
            .filter(v => typeof v.phylop_score === 'number' && v.gnomad_af > 0)
            .map(v => ({ x: v.gnomad_af, y: v.phylop_score, id: v.vid }));

        const variantTypes = countValues(filteredVariants.map(v => v.variant_type || 'Unknown'));
        const variantTypeData = Object.entries(variantTypes).map(([name, value]) => ({ name, value })).sort((a, b) => b.value - a.value);

        const qualityBins = [0, 30, 100, 500, 1000, Infinity];
        const qualityLabels = ['<30', '30-100', '100-500', '500-1000', '>1000'];
        const qualityDist = qualityLabels.map((label, i) => {
            const count = filteredVariants.filter(v => {
                const q = v.quality || 0;
                return q >= qualityBins[i] && q < qualityBins[i + 1];
            }).length;
            return { name: label, value: count };
        });

        const conservationData = ['phylop_score', 'gerp_score', 'dann_score'].map(score => {
            const vals = filteredVariants.map(v => v[score]).filter(n => typeof n === 'number');
            return {
                name: score.replace('_score', '').toUpperCase(),
                avg: calculateMean(vals),
                max: vals.length ? Math.max(...vals) : 0,
                min: vals.length ? Math.min(...vals) : 0
            };
        });

        let coverage = "100%";
        // Use totalVariants from state if available, otherwise fallback
        const total = totalVariants || (rawData && rawData.total_variants) || 0;

        if (total > 0) {
            // Note: This coverage calculation might be misleading with pagination 
            // as filteredVariants is only for the current page. 
            // Ideally we'd want total filtered count from backend.
            // For now, let's just show percentage of current page vs total found.
            const percent = (filteredVariants.length / total) * 100;
            coverage = `${percent.toFixed(1)}%`;
        }

        return {
            count: filteredVariants.length,
            uniqueTypes: new Set(filteredVariants.map(v => v.variant_type)).size,
            meanAF, maxAF, clinvarCount, pieData, popData, scatterData, variantTypeData, qualityDist, conservationData, coverage
        };
    }, [filteredVariants, rawData, totalVariants]);

    return {
        rawData,
        filteredVariants,
        loading,
        error,
        filters,
        setFilters,
        handleSearch,
        stats,
        // Pagination exports
        currentPage,
        totalPages,
        totalVariants,
        changePage
    };
};
