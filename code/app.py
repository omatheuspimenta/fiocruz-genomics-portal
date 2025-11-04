import streamlit as st
import hail as hl
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re

# Configure Streamlit page
st.set_page_config(page_title="Variant Browser", layout="wide")

@st.cache_resource
def init_hail():
    """Initialize Hail once and cache it"""
    hl.init(quiet=True, log='../logs/hail')
    return True

@st.cache_data
def get_available_fields(mt_path):
    """Get list of available INFO fields from the matrix table"""
    mt = hl.read_matrix_table(mt_path)
    return list(mt.info.dtype.fields)

@st.cache_data
def load_variant_data(mt_path):
    """Load and process matrix table dynamically based on available fields"""
    mt = hl.read_matrix_table(mt_path)
    variants = mt.rows()
    
    # Get available fields
    info_fields = set(mt.info.dtype.fields)
    
    # def safe_get(field, default, is_array=False, index=0):
    #     if field in info_fields:
    #         f = variants.info[field]
    #         if is_array:
    #             return hl.if_else(hl.len(f) > index, f[index], default)
    #         return f
    #     return hl.missing(hl.dtype(type(default).__name__))
    def safe_get(field, default, is_array=False, index=0):
        """
        Safely extract info field, handling missing fields and missing arrays
        by coalescing to a default value.
        """
        if field not in info_fields:
            return hl.literal(default)  # Field doesn't exist in header
        
        f = variants.info[field]
        
        if is_array:
            # 1. Check if field is defined.
            # 2. If yes, check if length is > index.
            # 3. If yes, get element.
            # 4. If no to 1 or 2, return default.
            return hl.if_else(
                hl.is_defined(f) & (hl.len(f) > index),
                f[index],
                hl.literal(default)
            )
        else:
            # Coalesce returns the field if it's not missing,
            # otherwise it returns the default value.
            return hl.coalesce(f, hl.literal(default))
    
    # Base selection (always present)
    selection = {
        'chrom': variants.locus.contig,
        'pos': variants.locus.position,
        'ref': variants.alleles[0],
        'alt': hl.delimit(variants.alleles[1:], ','),
        'rsid': variants.rsid,
        'qual': variants.qual,
        'filters': hl.delimit(variants.filters, ','),
    }
    
    # Add fields that exist
    field_mapping = [
        # Core allele stats
        ('AC', 'AC', 0, True),
        ('AN', 'AN', 0, False),
        ('AF', 'AF', 0.0, True),
        
        # gnomAD specific
        ('grpmax', 'grpmax', '', True),
        ('faf95_max', 'fafmax_faf95_max', 0.0, True),
        ('nhomalt', 'nhomalt', 0, True),
        
        # Sex-specific
        ('AC_XX', 'AC_XX', 0, True),
        ('AF_XX', 'AF_XX', 0.0, True),
        ('AN_XX', 'AN_XX', 0, False),
        ('AC_XY', 'AC_XY', 0, True),
        ('AF_XY', 'AF_XY', 0.0, True),
        ('AN_XY', 'AN_XY', 0, False),
        
        # Predictions
        ('cadd_phred', 'cadd_phred', 0.0, False),
        ('revel_max', 'revel_max', 0.0, False),
        ('spliceai_ds_max', 'spliceai_ds_max', 0.0, False),
        ('phylop', 'phylop', 0.0, False),
        ('polyphen_max', 'polyphen_max', 0.0, False),
        ('sift_max', 'sift_max', 0.0, False),
        
        # Quality
        ('DP', 'DP', 0, False),
        ('FS', 'FS', 0.0, False),
        ('MQ', 'MQ', 0.0, False),
        ('QD', 'QD', 0.0, False),
    ]
    
    for new_name, field_name, default, is_array in field_mapping:
        if field_name in info_fields:
            selection[new_name] = safe_get(field_name, default, is_array)
    
    # Add population fields if they exist
    for pop in ['afr', 'amr', 'asj', 'eas', 'fin', 'nfe', 'sas', 'mid']:
        if f'AC_{pop}' in info_fields:
            selection[f'AC_{pop}'] = safe_get(f'AC_{pop}', 0, True)
        if f'AF_{pop}' in info_fields:
            selection[f'AF_{pop}'] = safe_get(f'AF_{pop}', 0.0, True)
        if f'AN_{pop}' in info_fields:
            selection[f'AN_{pop}'] = safe_get(f'AN_{pop}', 0, False)
    
    # Add VEP if present
    if 'vep' in info_fields:
        selection['vep'] = variants.info.vep
    
    variants = variants.select(**selection)
    return variants, list(selection.keys())

def parse_variant_string(variant_str):
    """Parse variant string"""
    if variant_str.startswith('rs'):
        return None, None, None, None, variant_str
    
    match = re.match(r'chr?(\w+)[:-](\d+)[:-]([ACGT]+)[:-]([ACGT]+)', variant_str, re.IGNORECASE)
    if match:
        chrom, pos, ref, alt = match.groups()
        # Don't add 'chr' prefix if already there or if using numbers only
        if not variant_str.startswith('chr'):
            chrom = f"chr{chrom}" if mt_has_chr_prefix else chrom
        else:
            chrom = f"chr{chrom}"
        return chrom, int(pos), ref.upper(), alt.upper(), None
    
    return None, None, None, None, None

# Initialize
init_hail()

# Sidebar
with st.sidebar:
    st.header("⚙️ Configuration")
    mt_path = st.text_input("Matrix Table Path", value="/home/matheus/Documents/gnomeAD-tb/data/multisample_espanha.mt")
    
    if st.button("🔄 Load/Reload Data"):
        with st.spinner("Loading variant data..."):
            try:
                st.session_state.variants_ht, st.session_state.available_fields = load_variant_data(mt_path)
                st.session_state.info_fields = get_available_fields(mt_path)
                st.success("✅ Data loaded!")
                
                # Show what's available
                with st.expander("Available Data", expanded=False):
                    st.write("**Fields:**", len(st.session_state.available_fields))
                    
                    # Check for special fields
                    has_pop = any('AF_' in f and f.split('_')[1] in ['afr', 'amr', 'eas', 'nfe', 'sas'] 
                                 for f in st.session_state.available_fields)
                    has_pred = any(f in st.session_state.available_fields 
                                  for f in ['cadd_phred', 'revel_max', 'spliceai_ds_max'])
                    
                    st.write("✅ Core stats (AC, AN, AF)" if 'AC' in st.session_state.available_fields else "❌ Core stats")
                    st.write("✅ Population data" if has_pop else "❌ Population data")
                    st.write("✅ Prediction scores" if has_pred else "❌ Prediction scores")
                    st.write("✅ VEP annotations" if 'vep' in st.session_state.available_fields else "❌ VEP annotations")
                    
            except Exception as e:
                st.error(f"Error loading data: {e}")
    
    st.markdown("---")
    st.markdown("### 📖 Help")
    st.markdown("""
    **Search by:**
    - **Variant**: 
        - rsID: `rs123456`
        - Position: `chr1-12345-A-T` or `1-12345-A-T`
    - **Region**: `chr1:1000000-2000000` or `1:1000000-2000000`
    """)

# Main content
st.title("🧬 Variant Browser")

if 'variants_ht' not in st.session_state:
    st.info("👈 Please load data using the sidebar")
    st.stop()

# Check chromosome format
sample_df = st.session_state.variants_ht.head(1).to_pandas()
mt_has_chr_prefix = sample_df['chrom'].iloc[0].startswith('chr')

variants_ht = st.session_state.variants_ht
available_fields = st.session_state.available_fields

# Search section
st.markdown("---")
col1, col2, col3 = st.columns([2, 2, 1])

with col1:
    search_type = st.radio("Search by:", ["Variant", "Region", "Browse All"], horizontal=True)

with col2:
    if search_type == "Variant":
        search_query = st.text_input("Enter Variant:", placeholder="e.g., rs123456 or chr1-12345-A-T")
    elif search_type == "Region":
        search_query = st.text_input("Enter Region:", placeholder="e.g., chr1:1000000-2000000")
    else:
        max_vars = st.number_input("Max variants to display:", min_value=100, max_value=50000, value=1000)
        search_query = None

with col3:
    st.write("")
    st.write("")
    search_button = st.button("🔍 Search", type="primary", use_container_width=True)

# Execute search
filtered_ht = None
if search_button or (search_type == "Browse All"):
    with st.spinner("Searching..."):
        try:
            if search_type == "Variant" and search_query:
                chrom, pos, ref, alt, rsid = parse_variant_string(search_query)
                if rsid:
                    filtered_ht = variants_ht.filter(variants_ht.rsid == rsid)
                    search_desc = f"rsID: {rsid}"
                elif chrom and pos:
                    filtered_ht = variants_ht.filter(
                        (variants_ht.chrom == chrom) & (variants_ht.pos == pos)
                    )
                    if ref and alt:
                        filtered_ht = filtered_ht.filter(
                            (filtered_ht.ref == ref) & (filtered_ht.alt == alt)
                        )
                    search_desc = f"Variant: {search_query}"
                else:
                    st.error("Invalid variant format")
                    st.stop()
            
            elif search_type == "Region" and search_query:
                match = re.match(r'chr?(\w+)[:-](\d+)-(\d+)', search_query, re.IGNORECASE)
                if match:
                    chrom, start, end = match.groups()
                    chrom = f"chr{chrom}" if mt_has_chr_prefix and not search_query.startswith('chr') else chrom
                    if not mt_has_chr_prefix and search_query.startswith('chr'):
                        chrom = chrom[3:]
                    
                    filtered_ht = variants_ht.filter(
                        (variants_ht.chrom == chrom) &
                        (variants_ht.pos >= int(start)) &
                        (variants_ht.pos <= int(end))
                    )
                    search_desc = f"Region: {chrom}:{start}-{end}"
                else:
                    st.error("Invalid region format. Use: chr1:1000000-2000000")
                    st.stop()
            
            else:  # Browse All
                filtered_ht = variants_ht.head(max_vars)
                search_desc = f"Browsing first {max_vars} variants"
            
            # Convert to pandas
            df = filtered_ht.to_pandas()
            
            if len(df) == 0:
                st.warning(f"No variants found for {search_desc}")
            else:
                st.success(f"Found {len(df):,} variants - {search_desc}")
                st.session_state.current_df = df
                st.session_state.search_desc = search_desc
        
        except Exception as e:
            st.error(f"Search error: {e}")
            import traceback
            st.code(traceback.format_exc())

# Display results
if 'current_df' in st.session_state:
    df = st.session_state.current_df
    
    # Summary metrics
    st.markdown("---")
    st.subheader(f"📊 Summary")
    
    cols = st.columns(5)
    with cols[0]:
        st.metric("Variants", f"{len(df):,}")
    
    if 'AC' in df.columns:
        with cols[1]:
            st.metric("Mean AC", f"{df['AC'].mean():.2f}")
    if 'AF' in df.columns:
        with cols[2]:
            st.metric("Mean AF", f"{df['AF'].mean():.6f}")
    if 'faf95_max' in df.columns:
        with cols[3]:
            st.metric("Mean FAF95", f"{df['faf95_max'].mean():.6f}")
    if 'nhomalt' in df.columns:
        with cols[4]:
            st.metric("Homozygotes", f"{df['nhomalt'].sum():,}")
    
    # Filters
    st.markdown("---")
    with st.expander("🔧 Apply Filters", expanded=False):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if 'AF' in df.columns:
                af_min = st.number_input("Min AF", 0.0, 1.0, 0.0, format="%.6f")
                af_max = st.number_input("Max AF", 0.0, 1.0, 1.0, format="%.6f")
        
        with col2:
            if 'AC' in df.columns:
                ac_min = st.number_input("Min AC", 0, int(df['AC'].max()), 0)
                ac_max = st.number_input("Max AC", 0, int(df['AC'].max()), int(df['AC'].max()))
        
        with col3:
            if 'cadd_phred' in df.columns:
                min_cadd = st.number_input("Min CADD", 0.0, 50.0, 0.0)
            if 'revel_max' in df.columns:
                min_revel = st.number_input("Min REVEL", 0.0, 1.0, 0.0)
        
        # Apply filters
        mask = pd.Series([True] * len(df))
        if 'AF' in df.columns:
            mask &= (df['AF'] >= af_min) & (df['AF'] <= af_max)
        if 'AC' in df.columns:
            mask &= (df['AC'] >= ac_min) & (df['AC'] <= ac_max)
        if 'cadd_phred' in df.columns and min_cadd > 0:
            mask &= (df['cadd_phred'] >= min_cadd)
        if 'revel_max' in df.columns and min_revel > 0:
            mask &= (df['revel_max'] >= min_revel)
        
        df = df[mask]
        st.info(f"After filtering: {len(df):,} variants")
    
    # Visualizations
    st.markdown("---")
    
    # Create tabs based on available data
    tab_names = ["📋 Variant Table"]
    if 'AF' in df.columns:
        tab_names.insert(0, "📈 AF Distribution")
    
    pop_cols = [c for c in df.columns if c.startswith('AF_') and c.split('_')[1] in 
                ['afr', 'amr', 'asj', 'eas', 'fin', 'nfe', 'sas', 'mid']]
    if pop_cols:
        tab_names.insert(-1, "🌍 Populations")
    
    pred_cols = [c for c in df.columns if c in ['cadd_phred', 'revel_max', 'spliceai_ds_max']]
    if pred_cols:
        tab_names.insert(-1, "🔬 Predictions")
    
    tabs = st.tabs(tab_names)
    tab_idx = 0
    
    # AF Distribution tab
    if 'AF' in df.columns:
        with tabs[tab_idx]:
            col1, col2 = st.columns(2)
            with col1:
                fig = px.histogram(df, x='AF', nbins=50, title="Allele Frequency Distribution")
                st.plotly_chart(fig, use_container_width=True)
            with col2:
                if 'AC' in df.columns:
                    fig = px.scatter(df, x='AC', y='AF', hover_data=['rsid', 'chrom', 'pos'],
                                   title="Allele Count vs Frequency", opacity=0.6)
                    st.plotly_chart(fig, use_container_width=True)
        tab_idx += 1
    
    # Population tab
    if pop_cols:
        with tabs[tab_idx]:
            pop_names = [c.split('_')[1].upper() for c in pop_cols]
            pop_means = [df[col].mean() for col in pop_cols]
            
            fig = go.Figure(data=[go.Bar(x=pop_names, y=pop_means)])
            fig.update_layout(title="Mean Allele Frequency by Population",
                             xaxis_title="Population", yaxis_title="Mean AF")
            st.plotly_chart(fig, use_container_width=True)
        tab_idx += 1
    
    # Predictions tab
    if pred_cols:
        with tabs[tab_idx]:
            cols = st.columns(len(pred_cols))
            for i, col in enumerate(pred_cols):
                with cols[i]:
                    fig = px.histogram(df, x=col, nbins=30, title=f"{col.replace('_', ' ').title()} Distribution")
                    st.plotly_chart(fig, use_container_width=True)
        tab_idx += 1
    
    # Variant table tab
    with tabs[tab_idx]:
        # Select columns to display
        display_cols = ['chrom', 'pos', 'rsid', 'ref', 'alt']
        if 'AC' in df.columns:
            display_cols.append('AC')
        if 'AN' in df.columns:
            display_cols.append('AN')
        if 'AF' in df.columns:
            display_cols.append('AF')
        if 'faf95_max' in df.columns:
            display_cols.append('faf95_max')
        if 'nhomalt' in df.columns:
            display_cols.append('nhomalt')
        if 'cadd_phred' in df.columns:
            display_cols.append('cadd_phred')
        if 'revel_max' in df.columns:
            display_cols.append('revel_max')
        
        # Format numeric columns
        format_dict = {
            'AF': '{:.6f}',
            'faf95_max': '{:.6f}',
            'cadd_phred': '{:.2f}',
            'revel_max': '{:.3f}'
        }
        format_dict = {k: v for k, v in format_dict.items() if k in display_cols}
        
        st.dataframe(
            df[display_cols].style.format(format_dict),
            use_container_width=True,
            height=400
        )
        
        # Download
        csv = df.to_csv(index=False)
        st.download_button(
            "📥 Download Results (CSV)",
            data=csv,
            file_name=f"variants_{st.session_state.search_desc.replace(' ', '_').replace(':', '-')}.csv",
            mime="text/csv"
        )