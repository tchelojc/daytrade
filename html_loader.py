# flux_on/project/html_loader.py
import streamlit as st
from pathlib import Path
import base64

def load_html_file(file_path):
    """Carrega um arquivo HTML e retorna como string"""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except Exception as e:
        st.error(f"Erro ao carregar arquivo HTML: {e}")
        return None

def display_html_content(html_content, height=800):
    """Exibe conteúdo HTML no Streamlit"""
    if html_content:
        # Usar components para HTML puro
        st.components.v1.html(html_content, height=height, scrolling=True)
    else:
        st.error("Conteúdo HTML não disponível")

def get_operator_html_path():
    """Retorna o caminho para o arquivo OPERADOR.html"""
    # Tentar várias localizações possíveis
    possible_paths = [
        Path(__file__).parent / "OPERADOR.html",
        Path.cwd() / "OPERADOR.html",
        Path.cwd() / "project" / "OPERADOR.html",
        Path(__file__).parent.parent / "OPERADOR.html"
    ]
    
    for path in possible_paths:
        if path.exists():
            return path
    
    return None

def create_fallback_operator_interface():
    """Cria uma interface fallback se o HTML não for encontrado"""
    st.warning("Arquivo OPERADOR.html não encontrado. Usando interface alternativa.")
    
    # Interface alternativa
    st.title("⚡ Quantum Escala System")
    
    # Simulação do sistema
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Capital Total", "R$ 10.000,00")
        st.metric("Escala Atual", "Nível 2 (1.5x)")
    
    with col2:
        st.metric("Eficiência", "87.3%")
        st.metric("Risco Total", "1.2%")
    
    with col3:
        st.metric("Win Rate", "72.3%")
        st.metric("Proteção Ativa", "65%")
    
    # Controles simulados
    st.subheader("Controles do Sistema")
    
    col_btn1, col_btn2, col_btn3, col_btn4 = st.columns(4)
    
    with col_btn1:
        if st.button("🚀 Ativar Escala"):
            st.success("Escala automática ativada!")
    
    with col_btn2:
        if st.button("⚖️ Balancear"):
            st.info("Ativos balanceados com sucesso")
    
    with col_btn3:
        if st.button("🎯 Otimizar"):
            st.info("Sistema otimizado")
    
    with col_btn4:
        if st.button("🛡️ Proteção Máxima"):
            st.warning("Proteção máxima ativada")
    
    # Exibição de ativos
    st.subheader("Ativos Monitorados")
    
    ativos = [
        {"nome": "Mini Índice", "ticker": "WIN$", "alocação": "R$ 2.500", "escala": "1.5x"},
        {"nome": "Mini Dólar", "ticker": "WDO$", "alocação": "R$ 2.000", "escala": "1.2x"},
        {"nome": "Petróleo", "ticker": "PETR4", "alocação": "R$ 1.800", "escala": "1.8x"},
        {"nome": "Ouro", "ticker": "GOLD$", "alocação": "R$ 2.200", "escala": "1.0x"},
        {"nome": "Bitcoin", "ticker": "BTC$", "alocação": "R$ 1.500", "escala": "2.2x"}
    ]
    
    for ativo in ativos:
        with st.expander(f"{ativo['nome']} ({ativo['ticker']})"):
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                st.write(f"**Alocação:** {ativo['alocação']}")
            with col_b:
                st.write(f"**Escala:** {ativo['escala']}")
            with col_c:
                if st.button(f"Operar {ativo['ticker']}", key=f"btn_{ativo['ticker']}"):
                    st.info(f"Operação em {ativo['nome']} iniciada")