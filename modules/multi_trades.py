# flux_on/project/multi_trades.py

import streamlit as st
from project.config import TradeType, AssetCondition, MarketState, QuantumTrade, TimeFrame
from project.utils import safe_divide
from project.event_manager import EventManager

STATE_KEYS = {
    'multi_trades': {
        'selected_combos': [],
        'manual_params': {},
        'calculated_amounts': []
    },
    'dynamic_trading': {
        'price': 0.0,
        'volume': 0,
        'volatility': 'Estável'
    }
}

def init_state(module_name):
    if f'{module_name}_state' not in st.session_state:
        st.session_state[f'{module_name}_state'] = STATE_KEYS[module_name].copy()

class MultiTradesModule:
    def __init__(self, system):
        self.system = system
        if hasattr(system, 'bridge'):
            system.bridge.register_module('multi_trades', self)
        
        if 'multi_trades_state' not in st.session_state:
            st.session_state.multi_trades_state = {
                "selected_combos": [],
                "manual_params": {},
                "calculated": False
            }
        self.state = st.session_state.multi_trades_state

    def run(self) -> bool:
        try:
            # Verificação de pré-requisitos
            if not st.session_state.get("initial_trades_confirmed", False):
                st.error("Confirme as operações base primeiro!")
                return False
                
            with st.container():
                st.markdown("""
                <style>
                .wrap-text {
                    white-space: normal !important;
                    word-wrap: break-word !important;
                    overflow-wrap: break-word !important;
                }
                .strategy-item {
                    margin: 5px 0;
                    padding: 5px;
                    border-left: 3px solid #1f77b4;
                }
                </style>
                """, unsafe_allow_html=True)
                
                st.header("Fase 2: Combinações Estratégicas (31% do Capital)")
                
                # Verificação de operações base
                if not hasattr(st.session_state.portfolio, 'core_trades') or not st.session_state.portfolio.core_trades:
                    st.error("Complete a Fase 1 primeiro! Nenhuma operação base definida.")
                    return False
                    
                # Obter combinações disponíveis
                available_combos = self._get_available_combinations()
                
                if not available_combos:
                    st.warning("Nenhuma combinação disponível devido a operações base faltando.")
                    return False
                    
                # Mostrar seleção de combinações
                st.subheader("Selecione as Estratégias Combinadas")
                selected = self._render_combo_selection(available_combos)
                
                # Mostrar detalhes das combinações selecionadas
                if selected:
                    capital_for_phase = self._calculate_available_capital()
                    self._render_combo_details(selected, capital_for_phase)
                    
                    # Botão de confirmação
                    if st.button("Confirmar Combinações Estratégicas", key="confirm_combos", type="primary"):
                        st.session_state.portfolio.multi_trades = selected
                        st.session_state.multi_trades_confirmed = True
                        return True

            return False
        except Exception as e:
            st.error(f"Erro na fase 2: {str(e)}")
            st.session_state.multi_trades_confirmed = False
            return False
        
    def get_calculated_amounts(self):
        """Retorna os valores calculados de forma segura"""
        if hasattr(self, 'state') and 'calculated_amounts' in self.state:
            return self.state['calculated_amounts']
        return None

    def _get_available_combinations(self):
        core_trades = st.session_state.portfolio.core_trades
        
        # Dicionário de nomes de operações
        TRADE_NAMES = {
            TradeType.LONG: "Compra (Long)",
            TradeType.SHORT: "Venda (Short)",
            TradeType.BREAKOUT: "Rompimento",
            TradeType.REVERSAL: "Reversão",
            TradeType.SCALPING: "Scalping",
            TradeType.HEDGE: "Proteção"
        }

        # Verificação adaptativa das operações obrigatórias
        mandatory_trades = {
            TradeType.HEDGE: "Proteção",
            TradeType.LONG: "Compra"
        }
        
        # Cria operações faltantes com valor zero
        for trade, name in mandatory_trades.items():
            if trade not in core_trades:
                core_trades[trade] = QuantumTrade(trade, 0, 100.0, 105.0, 98.0, 0, 0, 0)

        # Função para obter parâmetros com fallback
        def get_params(trade_type, default_params):
            if trade_type in core_trades:
                return {
                    "entry": core_trades[trade_type].entry_price,
                    "target": core_trades[trade_type].target_price,
                    "stop": core_trades[trade_type].stop_loss
                }
            return default_params

        # Todas combinações possíveis
        all_combinations = [
            {
                "name": "Tendência com Proteção",
                "trades": [TradeType.LONG, TradeType.HEDGE],
                "params": [
                    get_params(TradeType.LONG, {"entry": 100.0, "target": 105.0, "stop": 98.0}),
                    get_params(TradeType.HEDGE, {"entry": 100.0, "target": 102.0, "stop": 99.0})
                ],
                "description": "Operação principal com hedge para redução de risco",
                "risk_level": "Moderado"
            },
            {
                "name": "Rompimento e Pullback",
                "trades": [TradeType.BREAKOUT, TradeType.REVERSAL],
                "params": [
                    get_params(TradeType.BREAKOUT, {"entry": 100.0, "target": 108.0, "stop": 97.0}),
                    get_params(TradeType.REVERSAL, {"entry": 100.0, "target": 95.0, "stop": 103.0})
                ],
                "description": "Combinação para mercados voláteis com níveis claros",
                "risk_level": "Agressivo"
            },
            {
                "name": "Scalping com Momentum",
                "trades": [TradeType.SCALPING, TradeType.MOMENTUM],
                "params": [
                    get_params(TradeType.SCALPING, {"entry": 100.0, "target": 101.5, "stop": 99.5}),
                    get_params(TradeType.MOMENTUM, {"entry": 100.0, "target": 103.0, "stop": 99.0})
                ],
                "description": "Operações rápidas em prazos curtos com momentum",
                "risk_level": "Conservador"
            }
        ]

        # Filtra combinações disponíveis
        available_combos = all_combinations
        
        # Mostra aviso se alguma combinação foi filtrada
        if len(available_combos) < len(all_combinations):
            missing = [combo["name"] for combo in all_combinations 
                    if combo not in available_combos]
            st.warning(f"Combinações não disponíveis: {', '.join(missing)}")

        return available_combos

    def _render_combo_selection(self, combos):
        """Renderiza a seleção de combinações"""
        selected = []
        for combo in combos:
            combo_key = f"combo_{combo['name']}"
            if st.checkbox(
                f"**{combo['name']}**: {combo['description']} (Risco: {combo['risk_level']})",
                key=f"combo_{combo['name']}",
                value=any(c['name'] == combo['name'] for c in self.state["selected_combos"])
            ):
                selected.append(combo)
        return selected

    def _calculate_combo_priority(self, combo):
        """Calcula a prioridade com base em regras estratégicas"""
        priority = 0.0
        
        # 1. Prioridade base para todas as combinações
        priority += 0.3  # Valor base
        
        # 2. Ajuste por nível de risco
        if combo['risk_level'] == "Conservador":
            priority += 0.2
        elif combo['risk_level'] == "Moderado":
            priority += 0.1
        
        # 3. Ajuste para combinações com hedge
        if TradeType.HEDGE in combo['trades']:
            priority += 0.25
            
        # 4. Ajuste para operações de curto prazo
        if TradeType.SCALPING in combo['trades']:
            priority += 0.15
        
        return min(priority, 1.0)  # Limite máximo

    def _calculate_combo_weights(self, combos):
        """Calcula pesos com distribuição equilibrada"""
        weights = []
        
        # 1. Calcular prioridades base
        priorities = [self._calculate_combo_priority(c) for c in combos]
        
        # 2. Calcular valor investido inicialmente
        invested = []
        portfolio = getattr(st.session_state, 'portfolio', None)
        core_trades = getattr(portfolio, 'core_trades', {})
        
        for combo in combos:
            total = sum(
                core_trades[tt].amount 
                for tt in combo['trades'] 
                if tt in core_trades
            )
            invested.append(total if total > 0 else 0.1)  # Evita zero
        
        # 3. Fator de ajuste pelo risco (favorece menor risco)
        risk_factors = []
        for combo in combos:
            if combo['risk_level'] == "Conservador":
                risk_factors.append(1.0)
            elif combo['risk_level'] == "Moderado":
                risk_factors.append(0.7)
            else:
                risk_factors.append(0.4)
        
        # Normalização
        total_priority = sum(priorities) or 1
        total_invested = sum(invested) or 1
        total_risk = sum(risk_factors) or 1
        
        # Combinação final (40% prioridade, 40% investimento, 20% risco)
        for p, i, r in zip(priorities, invested, risk_factors):
            weight = (0.4 * safe_divide(p, total_priority)) + \
                    (0.4 * safe_divide(i, total_invested)) + \
                    (0.2 * safe_divide(r, total_risk))
            weights.append(weight)
        
        # Garantir soma = 1
        total = sum(weights) or 1
        return [w/total for w in weights]
    
    def _render_strategy_analysis(self, combo):
        """Mostra a análise estratégica"""
        analysis = []
        
        # 1. Verificar presença de hedge
        if TradeType.HEDGE in combo['trades']:
            analysis.append("✅ Contém proteção (Hedge)")
            
        # 2. Análise do nível de risco
        if combo['risk_level'] == "Conservador":
            analysis.append("🟢 Risco Conservador")
        elif combo['risk_level'] == "Moderado":
            analysis.append("🟡 Risco Moderado")
        else:
            analysis.append("🔴 Risco Agressivo")
        
        # 3. Mostrar recomendação de alocação
        priority = self._calculate_combo_priority(combo)
        if priority > 0.7:
            analysis.append("🔵 ALOCAÇÃO PRIORITÁRIA")
        elif priority > 0.4:
            analysis.append("🟢 ALOCAÇÃO RECOMENDADA")
        else:
            analysis.append("🟡 ALOCAÇÃO OPCIONAL")
        
        st.markdown('<div class="strategy-analysis">' + 
                ''.join([f'<div class="strategy-item">{item}</div>' for item in analysis]) +
                '</div>', unsafe_allow_html=True)

    def _render_combo_details(self, combos, capital):
        """Renderização detalhada das combinações"""
        st.subheader("📊 Detalhes das Combinações Estratégicas")
        
        if capital <= 0:
            st.warning("Capital insuficiente para distribuição")
            return
        
        # Calcular pesos e valores
        weights = self._calculate_combo_weights(combos)
        amounts = [capital * w for w in weights]
        
        # Armazena os valores calculados
        self.state['calculated_amounts'] = amounts
        
        # Ajuste para garantir soma exata
        total = sum(amounts)
        if total != capital:
            amounts[-1] += (capital - total)
        
        # Exibir cada combinação
        for i, combo in enumerate(combos):
            with st.expander(f"🔍 {combo['name']} (Alocado: R$ {amounts[i]:.2f})", expanded=True):
                cols = st.columns([1, 1, 2])
                
                # Calcular risco/retorno combinado
                risk_rewards = []
                for params in combo['params']:
                    rr = safe_divide(
                        params['target'] - params['entry'],
                        params['entry'] - params['stop']
                    )
                    risk_rewards.append(rr)
                avg_risk_reward = sum(risk_rewards)/len(risk_rewards)
                
                cols[0].metric("Risco/Retorno Médio", f"{avg_risk_reward:.2f}:1")
                cols[1].metric("Capital Alocado", f"R$ {amounts[i]:.2f}")
                
                # Análise estratégica
                with cols[2]:
                    self._render_strategy_analysis(combo)
                    
                    # Inputs para ajuste manual
                    st.markdown("🔢 Ajuste de Parâmetros")
                    for j, trade_type in enumerate(combo['trades']):
                        st.markdown(f"**{trade_type.value}**")
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            new_entry = st.number_input(
                                "Preço Entrada",
                                value=float(combo['params'][j]['entry']),
                                min_value=0.01,
                                step=0.1,
                                key=f"entry_{combo['name']}_{j}"
                            )
                        with col2:
                            new_target = st.number_input(
                                "Alvo",
                                value=float(combo['params'][j]['target']),
                                min_value=0.01,
                                step=0.1,
                                key=f"target_{combo['name']}_{j}"
                            )
                        with col3:
                            new_stop = st.number_input(
                                "Stop",
                                value=float(combo['params'][j]['stop']),
                                min_value=0.01,
                                step=0.1,
                                key=f"stop_{combo['name']}_{j}"
                            )
                        
                        # Atualizar parâmetros manuais
                        if 'manual_params' not in self.state:
                            self.state['manual_params'] = {}
                        if combo['name'] not in self.state['manual_params']:
                            self.state['manual_params'][combo['name']] = []
                        self.state['manual_params'][combo['name']].append({
                            "entry": new_entry,
                            "target": new_target,
                            "stop": new_stop
                        })

    def _calculate_available_capital(self):
        """Calcula o capital disponível de forma segura"""
        core_trades = st.session_state.portfolio.core_trades.values()
        total_core = sum(t.amount for t in core_trades) if core_trades else 0
        return min(
            st.session_state.portfolio.capital * 0.31,
            st.session_state.portfolio.capital - total_core
        )

    def _calculate_combinations(self, capital):
        """Calcula os valores das combinações"""
        num_combos = len(self.state["selected_combos"])
        amount_per_combo = capital / num_combos
        
        st.subheader("Combinações Selecionadas")
        st.info(f"Capital alocado: R$ {capital:.2f} (R$ {amount_per_combo:.2f} por combinação)")
        
        for combo in self.state["selected_combos"]:
            st.write(f"- **{combo['name']}**: Risco/Retorno Médio: {combo['risk_level']}")

    def _confirm_combinations(self):
        """Confirma as combinações selecionadas"""
        try:
            st.session_state.portfolio.multi_trades = self.state["selected_combos"]
            self.state["calculated"] = False
            st.session_state.current_phase = "dynamic_trading"
            st.rerun()
            return True
        except Exception as e:
            st.error(f"Erro ao confirmar combinações: {str(e)}")
            return False