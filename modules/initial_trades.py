# flux_on/project/initial_trades.py

import streamlit as st
from typing import Dict
import logging
from project.config import TradeType, AssetCondition, MarketState, QuantumTrade, TraderProfile, TimeFrame
from project.utils import safe_divide

logger = logging.getLogger(__name__)

class InitialTradesModule:
    def __init__(self, system):
        self.system = system
        # Inicializa o estado das operações iniciais
        if 'initial_trades_state' not in st.session_state:
            required_trades = [
                TradeType.LONG,
                TradeType.SHORT,
                TradeType.BREAKOUT,
                TradeType.REVERSAL,
                TradeType.SCALPING,
                TradeType.HEDGE
            ]
            
            st.session_state.initial_trades_state = {
                "params": {
                    trade: {
                        "entry_price": 100.0 + (i*10),  # Preço de entrada simulado
                        "target_price": 105.0 + (i*10),  # Take profit
                        "stop_loss": 98.0 + (i*10),     # Stop loss
                        "timeframe": TimeFrame.M15       # Timeframe padrão
                    } for i, trade in enumerate(required_trades)
                },
                "allocations": None,
                "confirmed": False,
                "initial_params_fixed": None
            }
            
            # Ajustes específicos para operações obrigatórias
            st.session_state.initial_trades_state["params"][TradeType.HEDGE] = {
                "entry_price": 100.0,
                "target_price": 102.0,
                "stop_loss": 99.0,
                "timeframe": TimeFrame.H1
            }
            
            st.session_state.initial_trades_state["initial_params_fixed"] = st.session_state.initial_trades_state["params"].copy()

        self.state = st.session_state.initial_trades_state

    def run(self) -> bool:
        with st.container():
            if st.session_state.portfolio.capital < 1000.0:  # Capital baixo para trading
                return self._run_low_capital_mode()
            return self._run_standard_mode()

    def _run_standard_mode(self) -> bool:
        """Fluxo normal de alocação de 60% para capital padrão."""
        try:
            with st.container():
                st.header("Fase 1: Configuração das Operações Base (60% do Capital)")
                
                if not hasattr(st.session_state, 'portfolio'):
                    st.error("Erro: Portfólio não inicializado")
                    return False

                capital_for_phase = st.session_state.portfolio.capital * 0.60

                # Seção de ajuste de parâmetros
                with st.expander("Ajustar Parâmetros Iniciais", expanded=True):
                    cols = st.columns(2)
                    for i, trade_type in enumerate(self.state["params"]):
                        params = self.state["params"][trade_type]  # <<< Atribui corretamente
                            
                        with cols[i % 2]:
                            st.subheader(f"Parâmetros para {trade_type.value}")
                            
                            params["entry_price"] = st.number_input(
                                "Preço de Entrada",
                                min_value=0.01,
                                value=params["entry_price"],
                                key=f"entry_{trade_type.name}",
                                format="%.2f",
                                step=0.5
                            )
                            
                            params["target_price"] = st.number_input(
                                "Preço Alvo (TP)",
                                min_value=0.01,
                                value=params["target_price"],
                                key=f"target_{trade_type.name}",
                                format="%.2f",
                                step=0.1
                            )
                            
                            params["stop_loss"] = st.number_input(
                                "Stop Loss (SL)",
                                min_value=0.01,
                                value=max(params["stop_loss"], params["entry_price"] - 1.0),  # Garante diferença inicial
                                key=f"sl_{trade_type.name}",
                                format="%.2f",
                                step=0.5
                            )
                            
                            params["timeframe"] = st.selectbox(
                                "Timeframe",
                                options=list(TimeFrame),
                                index=list(TimeFrame).index(params["timeframe"]),
                                key=f"tf_{trade_type.name}"
                            )

                # Botão de otimização
                if st.button("Otimizar Alocação de Operações", key="optimize_standard"):
                    try:
                        # Criação da condição do ativo
                        asset_condition = AssetCondition(
                            asset="IBOV",  # Adicione esta linha
                            price=100.0,  # Preço atual simulado
                            volume=1000000,
                            rsi=50.0,
                            macd=0.5,
                            bollinger_band={"upper": 105.0, "middle": 100.0, "lower": 95.0},
                            market_context=['normal']  # Contexto de mercado padrão
                        )
                        
                        market_state = MarketState.ESTAVEL
                        timeframe = TimeFrame.M15

                        # Criando perfil do trader
                        trader_profile = TraderProfile(
                            asset_weights={
                                "IBOV": 1.15,
                                "DOLAR": 1.0,
                                "ACAO_INDIVIDUAL": 1.05
                            }
                        )
                        
                        # Prepara os dados para otimização
                        trade_opportunities = {}
                        for trade_type, params in self.state["params"].items():
                            if params["entry_price"] <= params["stop_loss"]:
                                st.error(f"Erro em {trade_type.value}: Stop Loss deve ser MENOR que Preço de Entrada")
                                st.error(f"Entrada: {params['entry_price']} | Stop: {params['stop_loss']}")
                                return False
                            
                            if params["target_price"] <= params["entry_price"]:
                                st.error(f"Erro em {trade_type.value}: Preço Alvo deve ser MAIOR que Preço de Entrada")
                                st.error(f"Entrada: {params['entry_price']} | Alvo: {params['target_price']}")
                                return False
                            
                            if abs(params["entry_price"] - params["stop_loss"]) < 0.01:
                                params["stop_loss"] = params["entry_price"] * 0.995  # Ajusta para 0.5% abaixo
                                st.warning(f"Ajuste automático aplicado no stop loss de {trade_type.value} para evitar divisão por zero")
                            
                            risk_reward = safe_divide(
                                params["target_price"] - params["entry_price"],
                                params["entry_price"] - params["stop_loss"],
                                default=0.0
                            )
                            trade_opportunities[trade_type] = risk_reward  # Agora risk_reward está definido

                        self.state["allocations"] = self.system.quantum_trader.optimize_portfolio(
                            available_trades=trade_opportunities,
                            condition=asset_condition,
                            market_state=market_state,
                            timeframe=timeframe,
                            trader_profile=trader_profile
                        )
                        st.success("Alocação otimizada com sucesso!")
                    except Exception as e:
                        st.error(f"Erro na otimização: {str(e)}")
                        return False

                # Seção de exibição dos resultados
                if self.state["allocations"]:
                    st.subheader("Alocação Inicial Recomendada")
                    st.info(f"Capital alocado para esta fase: R$ {capital_for_phase:.2f}")
                    
                    # Usando a nova função robusta de alocação
                    allocations = self.system.quantum_trader.allocate_capital_to_trades(
                        capital_for_phase,
                        self.state["allocations"]
                    )
                    
                    initial_trades = {}
                    for trade_type, amount in allocations.items():
                        params = self.state["params"][trade_type]
                        prob = self.system.quantum_trader.estimate_trade_probability(
                            trade_type, 
                            AssetCondition(
                                asset="IBOV",
                                price=params["entry_price"],
                                volume=1000000,
                                rsi=50.0,
                                macd=0.5,
                                bollinger_band={"upper": 105.0, "middle": 100.0, "lower": 95.0},
                                market_context=['normal']
                            ),
                            params["timeframe"]
                        )
                        
                        risk_reward = safe_divide(
                            params["target_price"] - params["entry_price"],
                            params["entry_price"] - params["stop_loss"],
                            default=0.0
                        )
                        
                        ev = amount * (prob * risk_reward - (1 - prob))  # Expected Value

                        initial_trades[trade_type] = QuantumTrade(
                            trade_type, 
                            amount, 
                            params["entry_price"], 
                            params["target_price"], 
                            params["stop_loss"], 
                            prob, 
                            risk_reward, 
                            ev
                        )
                        
                        with st.container():
                            cols = st.columns(4)
                            # Calcula o percentual da alocação em relação ao capital da fase
                            allocation_percentage = safe_divide(amount, capital_for_phase, default=0.0)
                            
                            cols[0].metric(label=f"**{trade_type.value}**", value=f"{allocation_percentage:.1%}")
                            cols[1].metric(label="Capital Alocado", value=f"R$ {amount:.2f}")
                            cols[2].metric(label="Risco/Retorno", value=f"{risk_reward:.2f}:1")
                            cols[3].metric(label="Valor Esperado", value=f"R$ {ev:.2f}")

                    # BOTÃO DE CONFIRMAÇÃO
                    if st.button("Confirmar Operações Base", key="confirm_standard", type="primary"):
                        if not self.state["allocations"]:
                            st.error("Nenhuma alocação calculada!")
                            return False
                        
                        # Validação para operações de proteção
                        mandatory_trades = [TradeType.HEDGE]
                        warning_shown = False
                        
                        for trade in mandatory_trades:
                            if trade not in initial_trades or initial_trades[trade].amount <= 0:
                                st.warning(f"Atenção: {trade.value} não foi alocada (recomendado para gestão de risco)")
                                warning_shown = True
                        
                        if warning_shown:
                            force_allocation = st.checkbox("Forçar alocação mínima em hedge?")
                            if force_allocation:
                                min_amount = capital_for_phase * 0.1  # 10% do capital da fase
                                for trade in mandatory_trades:
                                    if trade not in initial_trades or initial_trades[trade].amount <= 0:
                                        params = self.state["params"][trade]
                                        prob = self.system.quantum_trader.estimate_trade_probability(
                                            trade, 
                                            AssetCondition(
                                            asset="IBOV",  # Adicione esta linha 
                                            price=params["entry_price"]),
                                            params["timeframe"]
                                        )
                                        risk_reward = safe_divide(
                                            params["target_price"] - params["entry_price"],
                                            params["entry_price"] - params["stop_loss"],
                                            default=0.0
                                        )
                                        initial_trades[trade] = QuantumTrade(
                                            trade, 
                                            min_amount, 
                                            params["entry_price"], 
                                            params["target_price"], 
                                            params["stop_loss"], 
                                            prob, 
                                            risk_reward, 
                                            min_amount * (prob * risk_reward - (1 - prob))
                                        )
                        
                        try:
                            # Armazena os parâmetros iniciais fixos
                            self.state["initial_params_fixed"] = {
                                trade_type: {
                                    "entry_price": trade.entry_price,
                                    "target_price": trade.target_price,
                                    "stop_loss": trade.stop_loss,
                                    "timeframe": self.state["params"][trade_type]["timeframe"]
                                } for trade_type, trade in initial_trades.items()
                            }
                            
                            st.session_state.portfolio.core_trades = initial_trades
                            st.session_state.initial_trades_confirmed = True
                            self.state["confirmed"] = True
                            return True
                        except Exception as e:
                            st.error(f"Erro ao confirmar: {str(e)}")
                            return False

            return False
        except Exception as e:
            st.error(f"Erro na fase 1: {str(e)}")
            st.session_state.initial_trades_confirmed = False
            return False
        
    def _validate_trade_parameters(self) -> bool:
        """Valida todos os parâmetros antes da otimização"""
        MIN_DIFFERENCE = 0.01  # Diferença mínima aceitável
        
        for trade_type, params in self.state["params"].items():
            # Verifica se os preços são válidos
            if params["entry_price"] <= 0 or params["target_price"] <= 0 or params["stop_loss"] <= 0:
                st.error(f"Parâmetros inválidos para {trade_type.value}: Todos os preços devem ser positivos")
                return False
                
            # Verifica diferença mínima entre entrada e stop
            if abs(params["entry_price"] - params["stop_loss"]) < MIN_DIFFERENCE:
                st.error(f"Parâmetros inválidos para {trade_type.value}: Diferença entre entrada e stop muito pequena (min {MIN_DIFFERENCE})")
                return False
                
            if params["entry_price"] <= params["stop_loss"]:
                st.error(f"Parâmetros inválidos para {trade_type.value}: Stop Loss deve ser menor que Preço de Entrada")
                return False
                
            if params["target_price"] <= params["entry_price"]:
                st.error(f"Parâmetros inválidos para {trade_type.value}: Preço Alvo deve ser maior que Preço de Entrada")
                return False
                
        return True

    def _run_low_capital_mode(self) -> bool:
        """Versão simplificada para capital pequeno"""
        st.warning("Modo Low-Capital: Operação única com alocação máxima de R$ 500,00")
        
        trade_type = TradeType.LONG  # Operação mais conservadora
        params = self.state["params"][trade_type]
        amount = min(500.0, st.session_state.portfolio.capital * 0.9)
        
        prob = self.system.quantum_trader.estimate_trade_probability(
            trade_type, 
            AssetCondition(
            asset="IBOV",  # Adicione esta linha  
            price=params["entry_price"]),
            params["timeframe"]
        )
        risk_reward = safe_divide(
            params["target_price"] - params["entry_price"],
            params["entry_price"] - params["stop_loss"],
            default=0.0
        )
        ev = amount * (prob * risk_reward - (1 - prob))

        st.subheader("Operação Única Recomendada")
        col1, col2, col3 = st.columns(3)
        col1.metric("Estratégia", trade_type.value)
        col2.metric("Risco/Retorno", f"{risk_reward:.2f}:1")
        col3.metric("Valor Esperado", f"R$ {ev:.2f}")

        if st.button("Confirmar Operação Única", key="confirm_low_capital"):
            st.session_state.portfolio.core_trades = {
                trade_type: QuantumTrade(
                    trade_type, 
                    amount, 
                    params["entry_price"], 
                    params["target_price"], 
                    params["stop_loss"], 
                    prob, 
                    risk_reward, 
                    ev
                )
            }
            return True
            
        return False