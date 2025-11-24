const API_BASE = ''; // Relative path for proxy

export const fetchVariant = async (variantId) => {
    const res = await fetch(`${API_BASE}/variant/${variantId}`);
    if (!res.ok) throw new Error("Variant details not found");
    return res.json();
};

export const searchVariants = async (type, query, page = 1) => {
    let endpoint = '';
    const cleanQuery = query.trim();

    if (type === 'variant') {
        // Direct variant lookup is handled slightly differently in the original app, 
        // but we can standardize the interface here.
        return fetchVariant(cleanQuery);
    } else if (type === 'gene') {
        endpoint = `/gene/${cleanQuery}?page=${page}`;
    } else {
        // Region
        const regionQuery = cleanQuery.replace(/\s/g, '');
        endpoint = `/region/${regionQuery}?page=${page}`;
    }

    const res = await fetch(`${API_BASE}${endpoint}`);
    if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.detail || `API Error: ${res.status}`);
    }
    return res.json();
};
