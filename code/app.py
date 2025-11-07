import streamlit as st
import hail as hl
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import re

# Configure Streamlit page
st.set_page_config(page_title="Nirvana Variant Browser", layout="wide", page_icon="🧬")

@st.cache_resource
def init_hail():
    """Initialize Hail once and cache it"""
    hl.init(quiet=True, log='./logs/hail')
    return True

@st.cache_data
def get_table_info(table_path):
    """Get information about the Hail table structure"""
    ht = hl.read_table(table_path)
    fields = list(ht.row)
    
    # Categorize fields
    info = {
        'all_fields': fields,
        'has_gnomad': any(f.startswith('gnomad_') for f in fields),
        'has_topmed': any(f.startswith('topmed_') for f in fields),
        'has_clinvar': 'clinvar_significance' in fields,
        'has_transcripts': 'transcripts' in fields,
        'has_conservation': any(f in fields for f in ['phylop_score', 'gerp_score']),
        'population_fields': [f for f in fields if f.endswith('_af') and 'gnomad_' in f],
        'n_variants': ht.count(),
    }
    return info

@st.cache_data
def load_variant_data(table_path, limit=None):
    """Load Nirvana Hail table"""
    ht = hl.read_table(table_path)
    
    # Select commonly used fields for display
    selection = {
        'chromosome': ht.chromosome,
        'position': ht.position,
        'ref': ht.ref,
        'alt': ht.alt,
        'rsid': ht.rsid,
        'vid': ht.vid,
        'variant_type': ht.variant_type,
        'hgvsg': ht.hgvsg,
        
        # gnomAD frequencies
        'gnomad_af': ht.gnomad_af,
        'gnomad_exome_af': ht.gnomad_exome_af,
        'max_gnomad_af': ht.max_gnomad_af,
        'max_pop_af': ht.max_pop_af,
        
        # Population-specific
        'gnomad_afr_af': ht.gnomad_afr_af,
        'gnomad_amr_af': ht.gnomad_amr_af,
        'gnomad_eas_af': ht.gnomad_eas_af,
        'gnomad_fin_af': ht.gnomad_fin_af,
        'gnomad_nfe_af': ht.gnomad_nfe_af,
        'gnomad_asj_af': ht.gnomad_asj_af,
        'gnomad_sas_af': ht.gnomad_sas_af,
        
        # TOPMed
        'topmed_af': ht.topmed_af,
        
        # Conservation
        'phylop_score': ht.phylop_score,
        'gerp_score': ht.gerp_score,
        
        # ClinVar
        'clinvar_significance': ht.clinvar_significance,
        'clinvar_id': ht.clinvar_id,
        
        # Quality
        'filters': ht.filters,
        'mapping_quality': ht.mapping_quality,
        
        # Annotations
        'n_transcripts': ht.n_transcripts,
        'genes': ht.genes,
        'all_consequences': ht.all_consequences,
        'canonical_transcript': ht.canonical_transcript,
    }
    
    ht = ht.select(**selection)
    
    if limit:
        ht = ht.head(limit)
    
    return ht

def parse_variant_string(variant_str):
    """Parse variant string in multiple formats"""
    variant_str = variant_str.strip()
    
    # rsID
    if variant_str.startswith('rs'):
        return None, None, None, None, variant_str
    
    # chr1:12345:A:T or chr1-12345-A-T
    match = re.match(r'(chr\w+)[:-](\d+)[:-]([ACGT]+)[:-]([ACGT]+)', variant_str, re.IGNORECASE)
    if match:
        chrom, pos, ref, alt = match.groups()
        return chrom, int(pos), ref.upper(), alt.upper(), None
    
    # chr1:12345 (position only)
    match = re.match(r'(chr\w+)[:-](\d+)$', variant_str, re.IGNORECASE)
    if match:
        chrom, pos = match.groups()
        return chrom, int(pos), None, None, None
    
    return None, None, None, None, None

def parse_region(region_str):
    """Parse region string: chr1:1000000-2000000"""
    match = re.match(r'(chr\w+)[:-](\d+)-(\d+)', region_str, re.IGNORECASE)
    if match:
        chrom, start, end = match.groups()
        return chrom, int(start), int(end)
    return None, None, None

def parse_gene(gene_str):
    """Parse gene name"""
    return gene_str.strip().upper()

# Initialize
init_hail()

# Sidebar
with st.sidebar:
    st.image("https://via.placeholder.com/150x50/4CAF50/FFFFFF?text=Nirvana+Browser", use_container_width=True)
    st.header("⚙️ Configuration")
    
    table_path = st.text_input(
        "Hail Table Path",
        value="nirvana_variants.ht",
        help="Path to your Nirvana Hail table"
    )
    
    if st.button("🔄 Load/Reload Data"):
        with st.spinner("Loading table..."):
            try:
                # Clear cache
                get_table_info.clear()
                load_variant_data.clear()
                
                # Load info
                table_info = get_table_info(table_path)
                st.session_state.table_info = table_info
                st.session_state.table_path = table_path
                
                st.success(f"✅ Loaded {table_info['n_variants']:,} variants!")
                
                # Show capabilities
                with st.expander("📊 Table Features", expanded=True):
                    st.write(f"**Total Variants:** {table_info['n_variants']:,}")
                    st.write(f"**gnomAD:** {'✅' if table_info['has_gnomad'] else '❌'}")
                    st.write(f"**TOPMed:** {'✅' if table_info['has_topmed'] else '❌'}")
                    st.write(f"**ClinVar:** {'✅' if table_info['has_clinvar'] else '❌'}")
                    st.write(f"**Transcripts:** {'✅' if table_info['has_transcripts'] else '❌'}")
                    st.write(f"**Conservation:** {'✅' if table_info['has_conservation'] else '❌'}")
                    st.write(f"**Populations:** {len(table_info['population_fields'])}")
                
            except Exception as e:
                st.error(f"❌ Error loading table: {e}")
                import traceback
                with st.expander("Error Details"):
                    st.code(traceback.format_exc())
    
    st.markdown("---")
    st.markdown("### 📖 Quick Guide")
    st.markdown("""
    **Search Options:**
    
    🔹 **Variant**
    - rsID: `rs123456`
    - Position: `chr1:12345` or `chr1:12345:A:T`
    
    🔹 **Region**
    - Format: `chr1:1000000-2000000`
    
    🔹 **Gene**
    - Symbol: `BRCA1`, `TP53`
    
    🔹 **Browse**
    - View random variants
    """)

# Main content
st.title("🧬 Nirvana Variant Browser")

if 'table_info' not in st.session_state:
    st.info("👈 Please load your Hail table using the sidebar")
    st.stop()

table_info = st.session_state.table_info
table_path = st.session_state.table_path

# Search Interface
st.markdown("---")
st.subheader("🔍 Search Variants")

col1, col2 = st.columns([3, 1])

with col1:
    search_type = st.radio(
        "Search by:",
        ["Variant", "Region", "Gene", "Browse All"],
        horizontal=True
    )

with col2:
    st.write("")
    st.write("")

# Search input based on type
if search_type == "Variant":
    search_query = st.text_input(
        "Enter variant:",
        placeholder="e.g., rs123456 or chr1:12345:A:T",
        help="Search by rsID or genomic coordinates"
    )
elif search_type == "Region":
    search_query = st.text_input(
        "Enter region:",
        placeholder="e.g., chr1:1000000-2000000",
        help="Search a genomic region"
    )
elif search_type == "Gene":
    search_query = st.text_input(
        "Enter gene symbol:",
        placeholder="e.g., BRCA1",
        help="Search variants in a gene"
    )
else:  # Browse All
    max_variants = st.number_input(
        "Number of variants to display:",
        min_value=100,
        max_value=10000,
        value=1000,
        step=100
    )
    search_query = None

search_button = st.button("🔎 Search", type="primary", use_container_width=False)

# Execute search
if search_button or search_type == "Browse All":
    with st.spinner("Searching variants..."):
        try:
            ht = hl.read_table(table_path)
            
            if search_type == "Variant" and search_query:
                chrom, pos, ref, alt, rsid = parse_variant_string(search_query)
                
                if rsid:
                    filtered_ht = ht.filter(ht.rsid == rsid)
                    search_desc = f"rsID: {rsid}"
                elif chrom and pos:
                    if ref and alt:
                        filtered_ht = ht.filter(
                            (ht.chromosome == chrom) &
                            (ht.position == pos) &
                            (ht.ref == ref) &
                            (ht.alt == alt)
                        )
                        search_desc = f"Variant: {chrom}:{pos}:{ref}:{alt}"
                    else:
                        filtered_ht = ht.filter(
                            (ht.chromosome == chrom) &
                            (ht.position == pos)
                        )
                        search_desc = f"Position: {chrom}:{pos}"
                else:
                    st.error("❌ Invalid variant format")
                    st.stop()
            
            elif search_type == "Region" and search_query:
                chrom, start, end = parse_region(search_query)
                if chrom:
                    filtered_ht = ht.filter(
                        (ht.chromosome == chrom) &
                        (ht.position >= start) &
                        (ht.position <= end)
                    )
                    search_desc = f"Region: {chrom}:{start:,}-{end:,}"
                else:
                    st.error("❌ Invalid region format. Use: chr1:1000000-2000000")
                    st.stop()
            
            elif search_type == "Gene" and search_query:
                gene = parse_gene(search_query)
                filtered_ht = ht.filter(ht.genes.contains(gene))
                search_desc = f"Gene: {gene}"
            
            else:  # Browse All
                filtered_ht = ht.head(max_variants)
                search_desc = f"Browsing {max_variants:,} variants"
            
            # Load selected fields
            filtered_ht = filtered_ht.select(
                'chromosome', 'position', 'ref', 'alt', 'rsid', 'vid',
                'variant_type', 'hgvsg',
                'gnomad_af', 'gnomad_exome_af', 'max_gnomad_af', 'max_pop_af',
                'gnomad_afr_af', 'gnomad_amr_af', 'gnomad_eas_af', 
                'gnomad_fin_af', 'gnomad_nfe_af', 'gnomad_asj_af', 'gnomad_sas_af',
                'topmed_af', 'phylop_score', 'gerp_score',
                'clinvar_significance', 'clinvar_id',
                'filters', 'mapping_quality',
                'n_transcripts', 'genes', 'all_consequences',
            )
            
            # Convert to pandas
            df = filtered_ht.to_pandas()
            
            # Convert sets to strings for display
            if 'genes' in df.columns:
                df['genes'] = df['genes'].apply(lambda x: ', '.join(sorted(x)) if x and len(x) > 0 else '')
            if 'all_consequences' in df.columns:
                df['all_consequences'] = df['all_consequences'].apply(
                    lambda x: ', '.join(sorted(x)) if x and len(x) > 0 else ''
                )
            
            if len(df) == 0:
                st.warning(f"⚠️ No variants found for: {search_desc}")
                st.stop()
            
            st.success(f"✅ Found **{len(df):,}** variants - {search_desc}")
            st.session_state.current_df = df
            st.session_state.search_desc = search_desc
            
        except Exception as e:
            st.error(f"❌ Search error: {e}")
            import traceback
            with st.expander("Error Details"):
                st.code(traceback.format_exc())
            st.stop()

# Display Results
if 'current_df' in st.session_state:
    df = st.session_state.current_df.copy()
    
    # Summary Metrics
    st.markdown("---")
    st.subheader("📊 Summary Statistics")
    
    metrics = st.columns(6)
    
    with metrics[0]:
        st.metric("Total Variants", f"{len(df):,}")
    
    with metrics[1]:
        variant_types = df['variant_type'].value_counts()
        st.metric("Variant Types", len(variant_types))
    
    with metrics[2]:
        if 'gnomad_af' in df.columns:
            mean_af = df['gnomad_af'].dropna().mean()
            st.metric("Mean gnomAD AF", f"{mean_af:.6f}" if not pd.isna(mean_af) else "N/A")
    
    with metrics[3]:
        if 'max_gnomad_af' in df.columns:
            max_af = df['max_gnomad_af'].dropna().max()
            st.metric("Max AF", f"{max_af:.6f}" if not pd.isna(max_af) else "N/A")
    
    with metrics[4]:
        if 'clinvar_significance' in df.columns:
            clinvar_count = df['clinvar_significance'].notna().sum()
            st.metric("ClinVar Variants", f"{clinvar_count:,}")
    
    with metrics[5]:
        if 'genes' in df.columns:
            unique_genes = len(set(gene for genes in df['genes'].dropna() 
                                  for gene in str(genes).split(', ') if gene))
            st.metric("Unique Genes", f"{unique_genes:,}")
    
    # Filters
    st.markdown("---")
    with st.expander("🔧 Apply Filters", expanded=False):
        filter_cols = st.columns(4)
        
        with filter_cols[0]:
            st.markdown("**Frequency Filters**")
            if 'max_gnomad_af' in df.columns:
                af_min = st.number_input("Min AF", 0.0, 1.0, 0.0, format="%.6f", key="af_min")
                af_max = st.number_input("Max AF", 0.0, 1.0, 1.0, format="%.6f", key="af_max")
            
            freq_category = st.multiselect(
                "Frequency Category",
                ["Ultra-rare (<0.01%)", "Rare (0.01-0.1%)", "Low freq (0.1-1%)", 
                 "Common (1-5%)", "Very common (>5%)"],
                default=[]
            )
        
        with filter_cols[1]:
            st.markdown("**Conservation Filters**")
            if 'phylop_score' in df.columns:
                min_phylop = st.number_input("Min PhyloP", -20.0, 20.0, -20.0, key="phylop")
            if 'gerp_score' in df.columns:
                min_gerp = st.number_input("Min GERP", -20.0, 20.0, -20.0, key="gerp")
        
        with filter_cols[2]:
            st.markdown("**Annotation Filters**")
            if 'clinvar_significance' in df.columns:
                clinvar_filter = st.multiselect(
                    "ClinVar Significance",
                    ["Pathogenic", "Likely pathogenic", "Benign", "Likely benign"],
                    default=[]
                )
            
            if 'all_consequences' in df.columns:
                consequence_filter = st.text_input("Consequence contains", "")
        
        with filter_cols[3]:
            st.markdown("**Other Filters**")
            if 'variant_type' in df.columns:
                var_types = df['variant_type'].unique()
                selected_types = st.multiselect("Variant Type", var_types, default=[])
            
            if 'genes' in df.columns:
                gene_filter = st.text_input("Gene contains", "")
        
        # Apply filters
        mask = pd.Series([True] * len(df))
        
        if 'max_gnomad_af' in df.columns:
            mask &= (df['max_gnomad_af'] >= af_min) & (df['max_gnomad_af'] <= af_max)
        
        if freq_category:
            freq_mask = pd.Series([False] * len(df))
            for cat in freq_category:
                if cat == "Ultra-rare (<0.01%)":
                    freq_mask |= (df['max_gnomad_af'] < 0.0001)
                elif cat == "Rare (0.01-0.1%)":
                    freq_mask |= (df['max_gnomad_af'] >= 0.0001) & (df['max_gnomad_af'] < 0.001)
                elif cat == "Low freq (0.1-1%)":
                    freq_mask |= (df['max_gnomad_af'] >= 0.001) & (df['max_gnomad_af'] < 0.01)
                elif cat == "Common (1-5%)":
                    freq_mask |= (df['max_gnomad_af'] >= 0.01) & (df['max_gnomad_af'] < 0.05)
                elif cat == "Very common (>5%)":
                    freq_mask |= (df['max_gnomad_af'] >= 0.05)
            mask &= freq_mask
        
        if 'phylop_score' in df.columns and min_phylop > -20:
            mask &= (df['phylop_score'] >= min_phylop)
        
        if 'gerp_score' in df.columns and min_gerp > -20:
            mask &= (df['gerp_score'] >= min_gerp)
        
        if clinvar_filter:
            clinvar_mask = pd.Series([False] * len(df))
            for sig in clinvar_filter:
                clinvar_mask |= df['clinvar_significance'].str.contains(sig, case=False, na=False)
            mask &= clinvar_mask
        
        if consequence_filter:
            mask &= df['all_consequences'].str.contains(consequence_filter, case=False, na=False)
        
        if selected_types:
            mask &= df['variant_type'].isin(selected_types)
        
        if gene_filter:
            mask &= df['genes'].str.contains(gene_filter, case=False, na=False)
        
        df_filtered = df[mask]
        
        if len(df_filtered) < len(df):
            st.info(f"📉 After filtering: **{len(df_filtered):,}** variants (from {len(df):,})")
            df = df_filtered
    
    # Visualizations
    st.markdown("---")
    st.subheader("📈 Visualizations")
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Frequency", "🌍 Populations", "🔬 Conservation", 
        "📋 Variant Table", "🧬 Annotations"
    ])
    
    # Tab 1: Frequency Distribution
    with tab1:
        if 'gnomad_af' in df.columns or 'max_gnomad_af' in df.columns:
            col1, col2 = st.columns(2)
            
            with col1:
                # AF histogram
                af_data = df['max_gnomad_af'].dropna()
                if len(af_data) > 0:
                    fig = px.histogram(
                        af_data,
                        nbins=50,
                        title="Allele Frequency Distribution (log scale)",
                        labels={'value': 'Allele Frequency', 'count': 'Count'}
                    )
                    fig.update_xaxis(type="log")
                    st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                # Frequency categories
                df_with_af = df[df['max_gnomad_af'].notna()].copy()
                df_with_af['freq_category'] = pd.cut(
                    df_with_af['max_gnomad_af'],
                    bins=[0, 0.0001, 0.001, 0.01, 0.05, 1],
                    labels=['Ultra-rare', 'Rare', 'Low freq', 'Common', 'Very common']
                )
                cat_counts = df_with_af['freq_category'].value_counts()
                
                fig = px.pie(
                    values=cat_counts.values,
                    names=cat_counts.index,
                    title="Frequency Categories"
                )
                st.plotly_chart(fig, use_container_width=True)
            
            # gnomAD genome vs exome
            if 'gnomad_af' in df.columns and 'gnomad_exome_af' in df.columns:
                comparison_df = df[
                    df['gnomad_af'].notna() & df['gnomad_exome_af'].notna()
                ].copy()
                
                if len(comparison_df) > 0:
                    fig = px.scatter(
                        comparison_df,
                        x='gnomad_af',
                        y='gnomad_exome_af',
                        hover_data=['chromosome', 'position', 'rsid'],
                        title="gnomAD Genome vs Exome Frequencies",
                        labels={'gnomad_af': 'Genome AF', 'gnomad_exome_af': 'Exome AF'},
                        opacity=0.6
                    )
                    fig.update_xaxis(type="log")
                    fig.update_yaxis(type="log")
                    fig.add_shape(
                        type="line", line=dict(dash="dash", color="gray"),
                        x0=0.00001, x1=1, y0=0.00001, y1=1
                    )
                    st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No frequency data available")
    
    # Tab 2: Population Distribution
    with tab2:
        pop_cols = ['gnomad_afr_af', 'gnomad_amr_af', 'gnomad_eas_af', 
                    'gnomad_fin_af', 'gnomad_nfe_af', 'gnomad_asj_af', 'gnomad_sas_af']
        pop_cols = [c for c in pop_cols if c in df.columns]
        
        if pop_cols:
            # Population means
            pop_names = [c.replace('gnomad_', '').replace('_af', '').upper() for c in pop_cols]
            pop_means = [df[col].mean() for col in pop_cols]
            
            fig = go.Figure(data=[
                go.Bar(x=pop_names, y=pop_means, marker_color='lightblue')
            ])
            fig.update_layout(
                title="Mean Allele Frequency by Population",
                xaxis_title="Population",
                yaxis_title="Mean AF",
                height=400
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Population comparison heatmap
            if len(df) > 1:
                pop_data = df[pop_cols].dropna()
                if len(pop_data) > 0:
                    corr = pop_data.corr()
                    fig = px.imshow(
                        corr,
                        labels=dict(color="Correlation"),
                        x=pop_names,
                        y=pop_names,
                        title="Population Frequency Correlation",
                        color_continuous_scale="RdBu_r",
                        zmin=-1,
                        zmax=1
                    )
                    st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No population data available")
    
    # Tab 3: Conservation Scores
    with tab3:
        cons_cols = [c for c in ['phylop_score', 'gerp_score'] if c in df.columns]
        
        if cons_cols:
            cols = st.columns(len(cons_cols))
            for i, col in enumerate(cons_cols):
                with cols[i]:
                    data = df[col].dropna()
                    if len(data) > 0:
                        fig = px.histogram(
                            data,
                            nbins=50,
                            title=f"{col.replace('_', ' ').title()} Distribution"
                        )
                        st.plotly_chart(fig, use_container_width=True)
            
            # Conservation vs AF
            if 'phylop_score' in df.columns and 'max_gnomad_af' in df.columns:
                plot_df = df[df['phylop_score'].notna() & df['max_gnomad_af'].notna()]
                if len(plot_df) > 0:
                    fig = px.scatter(
                        plot_df,
                        x='max_gnomad_af',
                        y='phylop_score',
                        hover_data=['chromosome', 'position', 'rsid'],
                        title="Conservation vs Allele Frequency",
                        opacity=0.5
                    )
                    fig.update_xaxis(type="log")
                    st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No conservation scores available")
    
    # Tab 4: Variant Table
    with tab4:
        # Select display columns
        display_cols = ['chromosome', 'position', 'rsid', 'ref', 'alt', 'variant_type']
        
        optional_cols = {
            'gnomad_af': 'gnomAD AF',
            'gnomad_exome_af': 'gnomAD Exome AF',
            'max_gnomad_af': 'Max AF',
            'topmed_af': 'TOPMed AF',
            'phylop_score': 'PhyloP',
            'gerp_score': 'GERP',
            'clinvar_significance': 'ClinVar',
            'genes': 'Genes',
            'all_consequences': 'Consequences',
            'n_transcripts': '# Transcripts'
        }
        
        for col, label in optional_cols.items():
            if col in df.columns:
                display_cols.append(col)
        
        # Column selector
        selected_cols = st.multiselect(
            "Select columns to display:",
            display_cols,
            default=display_cols[:10]
        )
        
        if selected_cols:
            # Format numeric columns
            format_dict = {}
            for col in selected_cols:
                if col.endswith('_af'):
                    format_dict[col] = '{:.6f}'
                elif col in ['phylop_score', 'gerp_score']:
                    format_dict[col] = '{:.3f}'
            
            st.dataframe(
                df[selected_cols].style.format(format_dict, na_rep='—'),
                use_container_width=True,
                height=500
            )
            
            # Download button
            csv = df[selected_cols].to_csv(index=False)
            st.download_button(
                "📥 Download Results (CSV)",
                data=csv,
                file_name=f"nirvana_variants_{st.session_state.search_desc.replace(' ', '_').replace(':', '-')}.csv",
                mime="text/csv",
                use_container_width=False
            )
    
    # Tab 5: Annotations
    with tab5:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Variant Types")
            if 'variant_type' in df.columns:
                var_type_counts = df['variant_type'].value_counts()
                fig = px.bar(
                    x=var_type_counts.index,
                    y=var_type_counts.values,
                    title="Variant Type Counts",
                    labels={'x': 'Variant Type', 'y': 'Count'}
                )
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No 'variant_type' data available.")
        
        with col2:
            st.markdown("#### ClinVar Significance")
            if 'clinvar_significance' in df.columns:
                # Handle potentially null or empty values before counting
                clinvar_data = df['clinvar_significance'].dropna()
                clinvar_data = clinvar_data[clinvar_data != '']
                clinvar_counts = clinvar_data.value_counts()
                
                if not clinvar_counts.empty:
                    fig = px.bar(
                        x=clinvar_counts.index,
                        y=clinvar_counts.values,
                        title="ClinVar Significance Counts",
                        labels={'x': 'Significance', 'y': 'Count'}
                    )
                    fig.update_layout(height=400)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No ClinVar data to display.")
            else:
                st.info("No 'clinvar_significance' data available.")
        
        st.markdown("---")
        st.markdown("#### Variant Consequences (Top 20)")
        if 'all_consequences' in df.columns:
            # This field is a list/set, converted to comma-separated string
            # We need to split and explode to count individual consequences
            consequences = df['all_consequences'].dropna().str.split(', ').explode()
            consequence_counts = consequences[consequences != ''].value_counts().head(20)
            
            if not consequence_counts.empty:
                fig = px.bar(
                    x=consequence_counts.index,
                    y=consequence_counts.values,
                    title="Top 20 Variant Consequences",
                    labels={'x': 'Consequence', 'y': 'Count'}
                )
                fig.update_layout(height=450)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No consequence data to display.")
        else:
            st.info("No 'all_consequences' data available.")