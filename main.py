# flux_on/project/main.py
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pathlib import Path
import streamlit as st
import logging

# Configuração inicial de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Adiciona o diretório raiz ao path (ajuste conforme sua estrutura)
sys.path.append(str(Path(__file__).parent.parent))

try:
    from project.quantum.optimizer import QuantumTrader
    from modules.initial_trades import InitialTradesModule
    from modules.multi_trades import MultiTradesModule
    from modules.dynamic_trading import DynamicTradingModule
    from config import TradePortfolio, TradeType, QuantumTrade
    from utils import safe_divide
except ImportError as e:
    logger.error(f"Erro de importação: {e}")
    raise

class TradingSystem:
    def __init__(self):
        self.quantum_trader = QuantumTrader()
        self.initial_trades = InitialTradesModule(self)
        self.multi_trades = MultiTradesModule(self)
        self.dynamic_trading = DynamicTradingModule(self)
        self._phase_containers = {
            "initial_trades": st.empty(),
            "multi_trades": st.empty(),
            "dynamic_trading": st.empty()
        }
        
    def _validate_state(self):
        required_states = {
            'portfolio': None,
            'current_phase': "initial_trades",
            'initial_trades_state': {},
            'initial_trades_confirmed': False,
            'multi_trades_confirmed': False,
            'dynamic_trading_confirmed': False
        }
        
        missing_states = []
        
        for state, default_value in required_states.items():
            if state not in st.session_state:
                logger.warning(f"Estado {state} não encontrado - Inicializando com valor padrão")
                st.session_state[state] = default_value
                missing_states.append(state)
        
        if missing_states:
            logger.info(f"Estados inicializados: {missing_states}")
        
        return True

    def run_phase(self):
        # Validação inicial do estado
        self._validate_state()
        
        try:
            current_phase = st.session_state.current_phase
            
            # Limpeza segura dos containers
            for container in self._phase_containers.values():
                container.empty()

            # Validação das fases
            if current_phase == "multi_trades" and not st.session_state.get("initial_trades_confirmed", False):
                st.error("Complete a Fase 1 primeiro!")
                st.session_state.current_phase = "initial_trades"
                st.rerun()
                return

            if current_phase == "dynamic_trading" and not all([
                st.session_state.get("initial_trades_confirmed", False),
                st.session_state.get("multi_trades_confirmed", False)
            ]):
                st.error("Complete as fases anteriores primeiro!")
                st.session_state.current_phase = "multi_trades"
                st.rerun()
                return

            # Renderização da Fase Atual
            with self._phase_containers[current_phase]:
                phase_result = False
                
                if current_phase == "initial_trades":
                    phase_result = self.initial_trades.run()
                    if phase_result and st.session_state.get("initial_trades_confirmed"):
                        st.session_state.current_phase = "multi_trades"

                elif current_phase == "multi_trades":
                    phase_result = self.multi_trades.run()
                    if phase_result and st.session_state.get("multi_trades_confirmed"):
                        st.session_state.current_phase = "dynamic_trading"

                elif current_phase == "dynamic_trading":
                    phase_result = self.dynamic_trading.run()
                    if phase_result and st.session_state.get("dynamic_trading_confirmed"):
                        self._reset_system()

                # Transição segura
                if phase_result and current_phase != st.session_state.current_phase:
                    st.rerun()
                    
                if not self._validate_state():
                    st.error("Estado inválido - Reiniciando sistema")
                    self._reset_system()
                    return

        except Exception as e:
            st.error(f"Erro crítico: {str(e)}")
            self._reset_system()

    def _reset_system(self):
        """Reinicialização completa e segura do sistema"""
        current_capital = st.session_state.portfolio.capital
        st.session_state.clear()
        st.session_state.portfolio = TradePortfolio(capital=current_capital)
        st.session_state.current_phase = "initial_trades"
        st.session_state.system = self

    def _safe_phase_transition(self, next_phase):
        """Garante uma transição limpa entre fases"""
        st.session_state.current_phase = next_phase
        st.rerun()

def initialize_session_state():
    """Garante a inicialização correta de todos os estados com operações básicas"""
    if 'portfolio' not in st.session_state:
        st.session_state.portfolio = TradePortfolio(capital=0.0)
        
        # Inicializa com todas as operações necessárias com valores padrão
        required_trades = [
            TradeType.LONG,
            TradeType.SHORT,
            TradeType.BREAKOUT,
            TradeType.REVERSAL,
            TradeType.SCALPING,
            TradeType.HEDGE
        ]
        
        st.session_state.portfolio.core_trades = {
            trade: QuantumTrade(
                trade_type=trade,
                amount=0.0,  # Valor será definido na Fase 1
                entry_price=100.0,
                target_price=105.0,
                stop_loss=98.0,
                probability=0.0,
                risk_reward=2.0,
                ev=0.0
            )
            for trade in required_trades
        }
    
    if 'current_phase' not in st.session_state:
        st.session_state.current_phase = "initial_trades"
    
    if 'system' not in st.session_state:
        st.session_state.system = TradingSystem()

def main():
    # Configuração inicial estável
    st.set_page_config(
        page_title="TRADE-ON",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # CSS para melhorar as interações
    st.markdown("""
    <style>
    /* Aplica transição de opacidade nos blocos verticais do Streamlit */
    div[data-testid="stVerticalBlock"] {
        transition: opacity 0.25s ease-in-out;
    }

    /* Melhora a visualização dos cards de trading */
    .trade-card {
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 15px;
        background-color: #1E1E1E;
        border-left: 4px solid #4ECDC4;
    }
    
    /* Destaque para valores positivos/negativos */
    .positive {
        color: #4ECDC4;
    }
    .negative {
        color: #FF6B6B;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Inicializa estados antes de qualquer renderização
    initialize_session_state()

    # Interface principal
    st.title("Sistema de Day Trade TRADE-ON")
    st.markdown("---")

    # Sidebar com controle de estado
    with st.sidebar:
        st.header("Painel de Controle do Fluxo")
        
        # Controle de capital apenas na fase inicial
        if st.session_state.current_phase == "initial_trades" and st.session_state.portfolio.capital == 0:
            capital = st.number_input(
                "Capital Total (R$)", 
                min_value=1000.0, 
                value=10000.0, 
                step=1000.0,
                key="capital_input"
            )
            
            if st.button("Iniciar Operações", key="init_flow"):
                st.session_state.portfolio.capital = capital
                st.rerun()
        
        # Exibição do estado atual
        st.metric("Capital Total", f"R$ {st.session_state.portfolio.capital:.2f}")
        st.write("---")
        st.subheader("Navegação de Fase")
        
        # Mapeamento de fases para nomes amigáveis
        phase_names = {
            "initial_trades": "Operações Base",
            "multi_trades": "Combinações Estratégicas",
            "dynamic_trading": "Trading Dinâmico"
        }
        
        st.write(f"Fase Atual: **{phase_names.get(st.session_state.current_phase, st.session_state.current_phase)}**")
        
        # Exibição do resumo de alocação
        if hasattr(st.session_state, 'portfolio') and st.session_state.portfolio.capital > 0:
            st.write("---")
            st.subheader("Alocação de Capital")
            
            if hasattr(st.session_state.portfolio, 'core_trades'):
                core_invested = sum(t.amount for t in st.session_state.portfolio.core_trades.values())
                st.write(f"🔹 **Base:** R$ {core_invested:.2f} (60%)")
            
            if hasattr(st.session_state.portfolio, 'multi_trades'):
                combo_capital = st.session_state.portfolio.capital * 0.31
                st.write(f"🧩 **Combinações:** R$ {combo_capital:.2f} (31%)")
            
            remaining = st.session_state.portfolio.capital - (core_invested + combo_capital)
            st.write(f"⚡ **Dinâmico:** R$ {remaining:.2f} (9%)")

    # Conteúdo principal condicional
    if st.session_state.portfolio.capital > 0:
        st.session_state.system.run_phase()
    else:
        st.info("Defina o Capital Total na barra lateral e clique em 'Iniciar Operações' para começar.")

if __name__ == "__main__":
    main()