import hail as hl
import gnomad_toolbox
import streamlit as st

hl.init()

st.write("Hail and gnomad_toolbox setup is complete!")

# print("Hail and gnomad_toolbox setup is complete!")

# arquivo = '/home/matheus/Documents/gnomeAD-tb/data/gnomad.exomes.v4.1.sites.chr18.vcf.bgz'



# # Ler VCF
# mt = hl.import_vcf(arquivo, force_bgz=True, reference_genome='GRCh38')

# # Salvar no formato de matrix do hail
# mt.write('meu_arquivo_hail_matrix')

# # Printar infos
# print(mt.count())
# print(mt.summarize())

