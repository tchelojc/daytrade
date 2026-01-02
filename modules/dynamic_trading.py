# flux_on/project/dynamic_trading.py

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.graph_objects as go
from typing import Optional, Dict, List
from project.config import TradeType, AssetCondition, MarketState, QuantumTrade, TimeFrame
from project.utils import safe_divide
from project.event_manager import EventManager
from functools import lru_cache
import random  # Necessário para a função _smart_allocation
import logging

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

class DynamicTradingModule:
    def __init__(self, system):
        self.system = system
        if 'dynamic_trading_state' not in st.session_state:
            st.session_state.dynamic_trading_state = {
                "price": 100.0,
                "volume": 1000000,
                "rsi": 50.0,
                "macd": 0.5,
                "bollinger_band": {"upper": 105.0, "middle": 100.0, "lower": 95.0},
                "volatility": "Estável",
                "timeframe": TimeFrame.M15
            }
        self.state = st.session_state.dynamic_trading_state

        # Mapeamento de volatilidade para valores numéricos
        self.volatility_map = {
            "Estável": 0.3,
            "Transição": 0.6,
            "Caótico": 0.9,
            "Tendência de Alta": 0.4,
            "Tendência de Baixa": 0.4
        }
        
    def _init_debug_mode(self):
        """Configura o modo de depuração para testes"""
        self.debug = st.sidebar.checkbox("🔧 Modo Debug", help="Mostra informações detalhadas de análise")
        if self.debug:
            st.sidebar.subheader("🧪 Cenários de Teste")
            self.test_scenario = st.sidebar.selectbox(
                "Selecionar Cenário",
                options=["Personalizado", "Tendência de Alta", "Tendência de Baixa", 
                    "RSI Extremo", "Bollinger Breakout", "Mercado Caótico"]
            )
        
    def _load_custom_styles(self):
        """CSS que deixa o painel SEXY"""
        st.markdown("""
        <style>
            @keyframes pulse {
                0% { transform: scale(1); }
                50% { transform: scale(1.03); }
                100% { transform: scale(1); }
            }
            .alert-pulse {
                animation: pulse 2s infinite;
            }
            .profit-glow {
                box-shadow: 0 0 15px #4ECDC4;
            }
            .loss-glow {
                box-shadow: 0 0 15px #FF6B6B;
            }
        </style>
        """, unsafe_allow_html=True)

    def run(self):
        try:
            # Verificação robusta de pré-requisitos
            if not self._validate_prerequisites():
                return False

            # Container principal
            with st.container():
                self._load_custom_styles()
                st.header("📈 Fase 3: Trading Dinâmico (9% do Capital)")
                st.markdown("""
                    **Fase de execução** onde monitoramos o mercado em tempo real para ajustar nossas posições.
                    Utilize os controles abaixo para simular as condições atuais do ativo.
                """)
                
                self._render_control_panel()
                self._render_technical_chart()
                self._render_trade_recommendations()
                
                # Botão de finalização
                if st.button("Finalizar Sessão", type="primary", key="finish_session"):
                    if self._validate_trades():
                        st.session_state.dynamic_trading_confirmed = True
                        st.success("Sessão concluída com sucesso!")
                        st.balloons()
                        return True
                    else:
                        st.error("Corrija as operações antes de finalizar")
                        return False

            return False
        except Exception as e:
            st.error(f"Erro crítico na fase 3: {str(e)}")
            st.session_state.dynamic_trading_confirmed = False
            return False
        
    def _validate_prerequisites(self):
        """Validação completa dos pré-requisitos para a fase"""
        checks = [
            st.session_state.get("initial_trades_confirmed", False),
            st.session_state.get("multi_trades_confirmed", False),
            hasattr(st.session_state, 'portfolio'),
            hasattr(st.session_state.portfolio, 'core_trades'),
            hasattr(st.session_state.portfolio, 'multi_trades')
        ]
        
        if not all(checks):
            missing = [
                "Confirmação da Fase 1" if not checks[0] else None,
                "Confirmação da Fase 2" if not checks[1] else None,
                "Portfólio inicializado" if not checks[2] else None,
                "Operações base definidas" if not checks[3] else None,
                "Combinações estratégicas definidas" if not checks[4] else None
            ]
            missing = [m for m in missing if m is not None]
            
            st.error(f"Pré-requisitos faltando: {', '.join(missing)}")
            return False
        return True

    def _validate_trades(self):
        """Validação das operações antes de finalizar"""
        if not st.session_state.portfolio.core_trades:
            st.error("Nenhuma operação base definida")
            return False
            
        if not st.session_state.portfolio.multi_trades:
            st.error("Nenhuma combinação estratégica definida")
            return False
            
        return True

    def _render_control_panel(self):
        """Painel de controle completo com indicadores e modos turbo"""
        self._init_debug_mode()  # Adiciona o seletor de debug
        
        # --- MODOS DE OPERAÇÃO ---
        mode_cols = st.columns([3, 1, 1])
        with mode_cols[0]:
            self.trading_mode = st.radio(
                "Modo de Operação",
                options=["🏎️ Turbo", "🛡️ Conservador", "🤖 Automático"],
                horizontal=True
            )

        with mode_cols[2]:
            if st.button("🚨 PANIC", type="primary", help="Fecha TODAS as posições imediatamente"):
                self._close_all_positions()
                self._trigger_alert('danger', 'Todas as posições foram fechadas!')

        # --- ALAVANCAGEM DINÂMICA ---
        if self.trading_mode == "🏎️ Turbo":
            lev_cols = st.columns(3)
            with lev_cols[0]:
                self.leverage = st.slider(
                    "Alavancagem", 1, 10, value=3,
                    help="Aumenta ganhos e perdas - use com cuidado"
                )
            with lev_cols[1]:
                st.metric("Exposição Total", f"R$ {self._calculate_available_capital() * self.leverage:.2f}")
            with lev_cols[2]:
                st.metric("Margem Requerida", f"R$ {self._calculate_available_capital() * 0.1:.2f}")

        # --- INDICADORES TÉCNICOS (mantidos) ---
        st.subheader("📊 Painel de Controle do Ativo")

        # CSS opcional
        st.markdown("""
        <style>
            .price-selector { margin-bottom: 1rem; }
            .indicator-sliders { margin-top: 1.5rem; }
        </style>
        """, unsafe_allow_html=True)

        # Preço e Volume
        st.markdown('<div class="price-selector">', unsafe_allow_html=True)
        cols = st.columns(2)
        with cols[0]:
            self.state["price"] = st.number_input(
                "Preço Atual", min_value=0.01, value=self.state["price"], step=0.1, format="%.2f"
            )
        with cols[1]:
            self.state["volume"] = st.number_input(
                "Volume (contratos)", min_value=0, value=self.state["volume"], step=1000
            )
        st.markdown('</div>', unsafe_allow_html=True)

        # Indicadores
        st.markdown('<div class="indicator-sliders">', unsafe_allow_html=True)
        cols = st.columns(3)
        with cols[0]:
            self.state["rsi"] = st.slider("RSI (14 períodos)", 0, 100, value=int(self.state["rsi"]))
        with cols[1]:
            self.state["macd"] = st.slider("MACD (12,26,9)", -5.0, 5.0, value=float(self.state["macd"]), step=0.1)
        with cols[2]:
            self.state["volatility"] = st.select_slider(
                "Volatilidade do Mercado",
                options=["Estável", "Transição", "Caótico", "Tendência de Alta", "Tendência de Baixa"],
                value=self.state["volatility"]
            )

        # Bandas de Bollinger
        st.markdown("**Bandas de Bollinger (20,2)**")
        b_cols = st.columns(3)
        with b_cols[0]:
            self.state["bollinger_band"]["upper"] = st.number_input(
                "Banda Superior", value=self.state["bollinger_band"]["upper"], step=0.1, format="%.2f"
            )
        with b_cols[1]:
            self.state["bollinger_band"]["middle"] = st.number_input(
                "Média Móvel", value=self.state["bollinger_band"]["middle"], step=0.1, format="%.2f"
            )
        with b_cols[2]:
            self.state["bollinger_band"]["lower"] = st.number_input(
                "Banda Inferior", value=self.state["bollinger_band"]["lower"], step=0.1, format="%.2f"
            )

        # Timeframe
        self.state["timeframe"] = st.selectbox(
            "Timeframe de Análise", options=list(TimeFrame),
            index=list(TimeFrame).index(self.state["timeframe"])
        )
        st.markdown('</div>', unsafe_allow_html=True)
        
        if self.debug:
            st.warning("MODO DEBUG ATIVADO - Mostrando informações detalhadas")
            self._apply_test_scenario()  # Aplica cenários de teste

    def _apply_test_scenario(self):
        """Aplica configurações pré-definidas para teste"""
        if self.test_scenario == "Tendência de Alta":
            self.state.update({
                "price": 102.0,
                "rsi": 65.0,
                "macd": 1.2,
                "volatility": "Tendência de Alta",
                "bollinger_band": {"upper": 105.0, "middle": 100.0, "lower": 95.0}
            })
        elif self.test_scenario == "Tendência de Baixa":
            self.state.update({
                "price": 98.0,
                "rsi": 35.0,
                "macd": -1.2,
                "volatility": "Tendência de Baixa",
                "bollinger_band": {"upper": 105.0, "middle": 100.0, "lower": 95.0}
            })
        elif self.test_scenario == "RSI Extremo":
            self.state.update({
                "rsi": 75.0 if random.random() > 0.5 else 25.0,
                "volatility": "Transição"
            })
        elif self.test_scenario == "Bollinger Breakout":
            self.state.update({
                "price": 106.0 if random.random() > 0.5 else 94.0,
                "volatility": "Caótico"
            })
        elif self.test_scenario == "Mercado Caótico":
            self.state.update({
                "price": random.uniform(90, 110),
                "rsi": random.randint(30, 70),
                "macd": random.uniform(-2, 2),
                "volatility": "Caótico",
                "timeframe": TimeFrame.M5
            })
        
    def _render_technical_chart(self):
        """Gráfico técnico avançado com candlestick, volume, Bollinger e heatmap"""
        
        # Preparar df (preserva df antigo ou cria novo)
        periods = 20
        times = pd.date_range(end=pd.Timestamp.now(), periods=periods, freq="5min")
        df = pd.DataFrame({
            "Time": times,
            "Open": [self.state["price"]*0.99 for _ in range(periods)],
            "High": [self.state["price"]*1.01 for _ in range(periods)],
            "Low": [self.state["price"]*0.98 for _ in range(periods)],
            "Close": [self.state["price"] for _ in range(periods)],
            "Upper": [self.state["bollinger_band"]["upper"]]*periods,
            "Middle": [self.state["bollinger_band"]["middle"]]*periods,
            "Lower": [self.state["bollinger_band"]["lower"]]*periods,
            "Volume": [self.state["volume"]*(0.8+0.02*i) for i in range(periods)]
        })

        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.02, row_heights=[0.7, 0.3])

        # Candlestick + Bollinger
        fig.add_trace(go.Candlestick(x=df['Time'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="Candles"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df['Time'], y=df['Upper'], line=dict(color='rgba(78,205,196,0.7)'), name="Banda Superior"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df['Time'], y=df['Middle'], line=dict(color='rgba(255,255,255,0.5)'), name="Média Móvel"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df['Time'], y=df['Lower'], line=dict(color='rgba(78,205,196,0.7)'), name="Banda Inferior"), row=1, col=1)

        patterns = self._detect_chart_patterns(AssetCondition(
            price=self.state["price"],
            rsi=self.state["rsi"],
            volume=self.state["volume"],
            bollinger_band=self.state["bollinger_band"]
        ))
        
        for pattern in patterns:
            if pattern['name'] == "Hammer":
                fig.add_annotation(
                    x=df['Time'].iloc[-1], y=df['Low'].iloc[-1],
                    text="🔨 Hammer",
                    showarrow=True,
                    arrowhead=1,
                    ax=0, ay=40
                )
            elif pattern['name'] == "Shooting Star":
                fig.add_annotation(
                    x=df['Time'].iloc[-1], y=df['High'].iloc[-1],
                    text="⭐ Shooting Star",
                    showarrow=True,
                    arrowhead=1,
                    ax=0, ay=-40
                )
            
        # Heatmap de liquidez
        fig.add_trace(go.Heatmap(
            x=df['Time'],
            y=[f"Lvl {i}" for i in range(5)],
            z=self._calculate_liquidity_matrix(),
            colorscale='Electric',
            showscale=False,
            name="Profundidade"
        ), row=2, col=1)

        fig.update_layout(
            title=f"Análise 3D - {self.state['volatility']} | {self.trading_mode}",
            hovermode="x unified",
            height=700,
            xaxis_rangeslider_visible=False,
            template="plotly_dark"
        )

        st.plotly_chart(fig, use_container_width=True)
        
    def _show_rules_status(self, condition, market_state):
        """Mostra quais regras estão sendo atendidas"""
        st.subheader("📋 Status das Regras de Trading")
        
        rules = [
            ("Tendência de Alta", 
            condition.macd > 0 and condition.price > condition.bollinger_band["middle"] and 
            market_state in [MarketState.TENDENCIA_ALTA, MarketState.ESTAVEL]),
            
            ("Reversão por RSI", 
            (condition.rsi < 30 or condition.rsi > 70) and market_state != MarketState.CAOTICO),
            
            ("Rompimento Bollinger", 
            condition.price > condition.bollinger_band["upper"] or 
            condition.price < condition.bollinger_band["lower"]),
            
            ("Scalping Volátil", 
            market_state == MarketState.CAOTICO and self.state["timeframe"] in [TimeFrame.M1, TimeFrame.M5])
        ]
        
        for name, active in rules:
            st.markdown(f"{'✅' if active else '❌'} **{name}**")
        
        st.caption("Legenda: ✅ Condição atendida | ❌ Condição não atendida")
    
    def _calculate_liquidity_matrix(self, levels=5, periods=20):
        """Retorna uma matriz de liquidez simulada"""
        # Simula liquidez crescente e decrescente
        liquidity = np.array([[self.state["volume"]*(0.5 + 0.1*i + 0.02*j) 
                            for j in range(periods)] 
                            for i in range(levels)])
        return liquidity

    def _render_trade_recommendations(self):
        """Recomendações de trading dinâmico"""
        st.subheader("💡 Recomendações de Operações")
        
        capital_for_phase = self._calculate_available_capital()
        st.info(f"Capital disponível para esta fase: **R$ {capital_for_phase:.2f}** (9% do total)")
        
        # Mostrar histórico de operações
        with st.expander("📋 Histórico de Operações", expanded=True):
            self._display_trade_history()
            
        # Primeiro definir as variáveis condition e market_state
        condition = AssetCondition(
            price=self.state["price"],
            volume=self.state["volume"],
            rsi=self.state["rsi"],
            macd=self.state["macd"],
            bollinger_band=self.state["bollinger_band"],
            market_context=[self.state["volatility"]]
        )
        
        market_state = MarketState(self.state["volatility"])
        timeframe = self.state["timeframe"]
        
        # Agora podemos chamar _show_rules_status com as variáveis definidas
        self._show_rules_status(condition, market_state)
        
        recommendations = self._generate_dynamic_recommendations(
            condition, 
            market_state,
            timeframe,
            capital_for_phase
        )
        
        # Exibir recomendações
        if not recommendations:
            st.warning("""
            ⚠️ Nenhuma oportunidade clara no momento. 
            O sistema está monitorando o mercado e notificará quando surgirem padrões favoráveis.
            """)
        else:
            for rec in recommendations:
                if not isinstance(rec, dict) or 'trade_type' not in rec:
                    st.error(f"Recomendação inválida: {rec}")
                    continue
                    
                with st.expander(f"📌 {rec.get('name', 'Sem nome')}", expanded=True):
                    self._display_recommendation_card(rec, condition)

    def _display_trade_history(self):
        """Exibe o histórico de operações"""
        try:
            # Layout em colunas
            col1, col2 = st.columns(2)
            
            with col1:
                with st.expander("🔍 Operações Base (60%)", expanded=True):
                    if hasattr(st.session_state.portfolio, 'core_trades') and st.session_state.portfolio.core_trades:
                        for trade_type, trade in st.session_state.portfolio.core_trades.items():
                            st.metric(
                                label=trade_type.value,
                                value=f"R$ {trade.amount:.2f}",
                                delta=f"Alvo: {trade.target_price:.2f} | Stop: {trade.stop_loss:.2f}"
                            )
                        total_core = sum(t.amount for t in st.session_state.portfolio.core_trades.values())
                        st.metric("Total Base", f"R$ {total_core:.2f}")
                    else:
                        st.warning("Nenhuma operação base definida")
            
            with col2:
                with st.expander("🧩 Combinações (31%)", expanded=True):
                    if hasattr(st.session_state.portfolio, 'multi_trades') and st.session_state.portfolio.multi_trades:
                        total_combo = st.session_state.portfolio.capital * 0.31
                        st.metric("Total Combinações", f"R$ {total_combo:.2f}")
                        
                        for i, combo in enumerate(st.session_state.portfolio.multi_trades):
                            st.write(f"**{i+1}. {combo['name']}**")
                            st.write(f"- Estratégia: {combo['description']}")
                            st.write(f"- Risco: {combo['risk_level']}")
                    else:
                        st.warning("Nenhuma combinação definida")
            
            # Resumo de proteção
            total_invested = total_core + total_combo
            st.info(f"""
            **🛡️ Gestão de Risco:**
            - Total investido: R$ {total_invested:.2f}
            - Capital em risco: R$ {total_invested * 0.6:.2f} (~60%)
            - Capital disponível: R$ {st.session_state.portfolio.capital - total_invested:.2f}
            """)
        
        except Exception as e:
            st.error(f"Erro ao exibir histórico: {str(e)}")

    def _display_recommendation_card(self, rec, condition):
        """Card de recomendação com métricas e ações"""
        try:
            # --- Defaults seguros ---
            rec = dict(rec or {})
            rec.setdefault('name', rec['trade_type'].value)
            rec.setdefault('entry_price', condition.price)
            rec.setdefault('target_price', condition.price * 1.03)
            rec.setdefault('stop_loss', condition.price * 0.98)
            rec.setdefault('prob', 0.60)
            rec.setdefault('risk_reward', 2.0)
            rec.setdefault('stake', 0.0)
            rec.setdefault('reason', 'Análise técnica')
            rec.setdefault('strategy', 'Estratégia padrão')
            
            # Cálculo do valor esperado
            ev = rec['stake'] * (rec['prob'] * rec['risk_reward'] - (1 - rec['prob']))
            
            # Layout do card
            st.markdown(f"""
            <div style="margin-top: 1rem;">
                <h4 style="margin-bottom: 0.5rem; color: #4ECDC4;">📊 Contexto Técnico</h4>
                <p style="color: #ddd;">{rec['reason']}</p>
            </div>
            """, unsafe_allow_html=True)

            # Métricas
            cols = st.columns(4)
            cols[0].metric("Probabilidade", f"{rec['prob']:.0%}")
            cols[1].metric("Risco/Retorno", f"{rec['risk_reward']:.2f}:1")
            cols[2].metric("Valor Esperado", f"R$ {ev:.2f}")
            cols[3].metric("Capital Sugerido", f"R$ {rec['stake']:.2f}")

            # Alocação dinâmica
            protection_ratio = 0.6  # Default, pode ser calculado dinamicamente
            attack_ratio = 1 - protection_ratio
            
            st.markdown(f"""
            <div style="margin: 1.5rem 0;">
                <h4 style="margin-bottom: 0.5rem; color: #4ECDC4;">📊 Alocação Dinâmica</h4>
                <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                    <div>
                        <small>Proteção</small>
                        <div style="font-weight: 700;">R$ {rec['stake'] * protection_ratio:.2f}</div>
                        <small>({protection_ratio:.0%})</small>
                    </div>
                    <div>
                        <small>Ataque</small>
                        <div style="font-weight: 700;">R$ {rec['stake'] * attack_ratio:.2f}</div>
                        <small>({attack_ratio:.0%})</small>
                    </div>
                </div>
                <div style="height: 8px; background: #333; border-radius: 4px; overflow: hidden; display: flex;">
                    <div style="width: {protection_ratio*100}%; height: 100%; background: #4ECDC4;"></div>
                    <div style="width: {attack_ratio*100}%; height: 100%; background: #FF6B6B;"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Botão de ação
            btn_key = f"apply_{rec['trade_type'].name}_{rec['name']}".replace(" ", "_").lower()
            clicked = st.button(
                f"Executar R$ {rec['stake']:.2f} em {rec['trade_type'].value}",
                key=btn_key,
                type="primary",
                disabled=rec['stake'] <= 0
            )

            if clicked:
                st.success(f"Operação executada: {rec['name']} | R$ {rec['stake']:.2f}")

        except Exception as e:
            st.error(f"Erro ao exibir recomendação: {e}")

    def _generate_dynamic_recommendations(self, condition, market_state, timeframe, capital):
        """Motor de recomendações com logs detalhados"""
        recommendations = []
        
        if self.debug:
            st.write("🔍 Analisando condições do mercado:")
            st.write(f"- Preço: {condition.price:.2f}")
            st.write(f"- RSI: {condition.rsi:.1f}")
            st.write(f"- MACD: {condition.macd:.2f}")
            st.write(f"- Volatilidade: {market_state.value}")
        
        # 1️⃣ Cenário: Tendência de alta (modificado para mostrar triggers)
        if (condition.macd > 0 and condition.price > condition.bollinger_band["middle"]):
            trigger_active = market_state in [MarketState.TENDENCIA_ALTA, MarketState.ESTAVEL]
            
            if self.debug:
                status = "✅" if trigger_active else "❌ (Estado de mercado não confirma)"
                st.write(f"{status} Tendência de Alta - MACD: {condition.macd:.2f}, Preço acima da MM: {condition.price:.2f} > {condition.bollinger_band['middle']:.2f}")
            
            if trigger_active:
                recommendations.append({
                    "trade_type": TradeType.LONG,
                    "name": "Tendência de Alta Confirmada",
                    "reason": f"MACD positivo + preço acima da média | RSI: {condition.rsi:.0f}",
                    "entry_price": condition.price,
                    "target_price": condition.price * 1.05,
                    "stop_loss": condition.price * 0.98,
                    "prob": 0.65,
                    "risk_reward": 2.5,
                    "timeframe": timeframe,
                    "priority": "Alta"
                })

        # 2️⃣ Cenário: RSI Extremo (com feedback visual)
        rsi_extreme = (condition.rsi < 30 or condition.rsi > 70) and market_state != MarketState.CAOTICO
        if self.debug:
            st.write(f"📊 RSI Extremo: {condition.rsi:.1f} - {'✅' if rsi_extreme else '❌'} (Limites: <30 ou >70)")
            
        if rsi_extreme:
            if condition.rsi < 30:
                trade_type = TradeType.LONG
                name = "Reversão por RSI Sobrevendido"
                reason = f"RSI {condition.rsi:.0f} indica sobrevenda. Potencial rebote."
                target = condition.price * 1.03
                stop = condition.price * 0.97
            else:
                trade_type = TradeType.SHORT
                name = "Reversão por RSI Sobrecomprado"
                reason = f"RSI {condition.rsi:.0f} indica sobrecompra. Potencial correção."
                target = condition.price * 0.97
                stop = condition.price * 1.03
            
            recommendations.append({
                "trade_type": trade_type,
                "name": name,
                "reason": reason,
                "entry_price": condition.price,
                "target_price": target,
                "stop_loss": stop,
                "prob": 0.60,
                "risk_reward": 2.0,
                "timeframe": timeframe,
                "priority": "Média"
            })
        
        # 3️⃣ Cenário: Rompimento de banda de Bollinger
        if (condition.price > condition.bollinger_band["upper"] or 
            condition.price < condition.bollinger_band["lower"]):
            
            if condition.price > condition.bollinger_band["upper"]:
                trade_type = TradeType.SHORT
                name = "Rompimento da Banda Superior"
                reason = "Preço acima da banda superior, potencial reversão."
                target = condition.bollinger_band["middle"]
                stop = condition.price * 1.02
            else:
                trade_type = TradeType.LONG
                name = "Rompimento da Banda Inferior"
                reason = "Preço abaixo da banda inferior, potencial rebote."
                target = condition.bollinger_band["middle"]
                stop = condition.price * 0.98
            
            recommendations.append({
                "trade_type": trade_type,
                "name": name,
                "reason": reason,
                "entry_price": condition.price,
                "target_price": target,
                "stop_loss": stop,
                "prob": 0.55,
                "risk_reward": 1.5,
                "timeframe": timeframe,
                "priority": "Média"
            })
        
        # 4️⃣ Cenário: Hedge para operações existentes
        if hasattr(st.session_state, 'portfolio') and hasattr(st.session_state.portfolio, 'core_trades'):
            for trade_type, trade in st.session_state.portfolio.core_trades.items():
                if trade_type == TradeType.LONG and condition.price < trade.stop_loss * 0.99:
                    recommendations.append({
                        "trade_type": TradeType.HEDGE_SHORT,
                        "name": "Hedge para Posição Long",
                        "reason": "Preço se aproximando do stop loss, proteger posição.",
                        "entry_price": condition.price,
                        "target_price": condition.price * 0.98,
                        "stop_loss": condition.price * 1.01,
                        "prob": 0.70,
                        "risk_reward": 2.0,
                        "timeframe": timeframe,
                        "priority": "Proteção"
                    })
                elif trade_type == TradeType.SHORT and condition.price > trade.stop_loss * 1.01:
                    recommendations.append({
                        "trade_type": TradeType.HEDGE_LONG,
                        "name": "Hedge para Posição Short",
                        "reason": "Preço se aproximando do stop loss, proteger posição.",
                        "entry_price": condition.price,
                        "target_price": condition.price * 1.02,
                        "stop_loss": condition.price * 0.99,
                        "prob": 0.70,
                        "risk_reward": 2.0,
                        "timeframe": timeframe,
                        "priority": "Proteção"
                    })
        
        # 5️⃣ Cenário: Scalping em mercado volátil
        if market_state == MarketState.CAOTICO and timeframe in [TimeFrame.M1, TimeFrame.M5]:
            recommendations.append({
                "trade_type": TradeType.SCALPING,
                "name": "Scalping em Mercado Volátil",
                "reason": "Alta volatilidade em timeframe curto, oportunidades de scalping.",
                "entry_price": condition.price,
                "target_price": condition.price * 1.005,
                "stop_loss": condition.price * 0.995,
                "prob": 0.55,
                "risk_reward": 1.0,
                "timeframe": timeframe,
                "priority": "Agressivo"
            })

        # ---- NOVO: scan de padrões gráficos, notícias e sazonalidade ----
        patterns = self._detect_chart_patterns(condition)
        if self.debug and patterns:
            st.write("🔎 Padrões Gráficos Detectados:")
            for p in patterns:
                st.write(f"- {p['name']} (Confiança: {p['confidence']:.0%})")
        news_impact = self._check_news_impact()
        seasonality = self._get_time_seasonality()

        for pattern in patterns:
            if pattern['name'] == "Hammer":
                recommendations.append({
                    'trade_type': TradeType.LONG,
                    'name': f"Padrão: {pattern['name']}",
                    'reason': "Reversão de baixa confirmada",
                    'entry_price': condition.price,
                    'target_price': condition.price * 1.03,
                    'stop_loss': condition.price * 0.97,
                    'prob': 0.68,
                    'risk_reward': 3.0,
                    'priority': 'Alta'
                })

        # Filtros externos
        recommendations = [
            r for r in recommendations 
            if not (news_impact == 'negative' and r['trade_type'] == TradeType.LONG)
        ]

        # Alocação inteligente de capital
        return self._smart_allocation(capital, recommendations)
    
    def _get_market_pulse(self):
        """Analisa 5 fatores cruciais para determinar o 'pulso' do mercado"""
        pulse = {
            'trend_strength': self._calculate_trend_strength(),
            'volatility_index': self._get_volatility_score(),
            'volume_anomaly': self._detect_volume_anomaly(),
            'sentiment': self._get_market_sentiment(),
            'liquidity': self._assess_liquidity()
        }
        return {k: v for k, v in sorted(pulse.items(), key=lambda x: x[1], reverse=True)}

    def _smart_allocation(self, capital: float, recommendations: list) -> list:
        """Distribui o capital usando:
        - 40% Probabilidade
        - 30% Risk/Reward  
        - 20% Correlação com operações existentes
        - 10% Fator surpresa (inovação)
        """
        weighted_recs = []
        for rec in recommendations:
            # Fator de proteção para trades existentes
            hedge_factor = 1.5 if any(
                t for t in st.session_state.portfolio.core_trades.values() 
                if t.trade_type == rec['trade_type']
            ) else 1.0
            
            # Score composto
            score = (rec['prob'] * 0.4 + 
                    rec['risk_reward'] * 0.3 + 
                    hedge_factor * 0.2 + 
                    random.uniform(0, 0.1))  # Fator aleatório controlado
            
            weighted_recs.append((score, rec))
        
        # Distribuição proporcional ao score
        total_score = sum(s for s, _ in weighted_recs)
        for score, rec in weighted_recs:
            rec['stake'] = capital * (score / total_score)
        
        return [r for _, r in weighted_recs]

    def _trigger_alert(self, alert_type: str, message: str):
        """Alertas visuais personalizados (sem áudio)"""
        alert_config = {
            'danger': {'color': '#FF6B6B', 'icon': '🚨'},
            'warning': {'color': '#FFD166', 'icon': '⚠️'},
            'opportunity': {'color': '#4ECDC4', 'icon': '💰'}
        }
        
        config = alert_config.get(alert_type, alert_config['warning'])
        st.markdown(f"""
        <div style="padding: 1rem; border-radius: 0.5rem; 
                    background: {config['color']}20; border-left: 4px solid {config['color']};
                    margin: 1rem 0; display: flex; align-items: center;">
            <span style="font-size: 1.5rem; margin-right: 0.5rem;">{config['icon']}</span>
            <strong>{message}</strong>
        </div>
        """, unsafe_allow_html=True)

    def _calculate_available_capital(self):
        """Calcula o capital disponível para trading dinâmico"""
        try:
            # Calcula o total investido nas operações base
            core_invested = sum(
                t.amount for t in st.session_state.portfolio.core_trades.values()
            ) if hasattr(st.session_state.portfolio, 'core_trades') else 0
            
            # Calcula o valor investido nas combinações (31% do capital)
            combo_capital = st.session_state.portfolio.capital * 0.31
            
            # Capital restante
            remaining_capital = st.session_state.portfolio.capital - (core_invested + combo_capital)
            
            # Capital para fase 3 é o mínimo entre 9% do total e o restante
            return min(
                st.session_state.portfolio.capital * 0.09,
                remaining_capital
            )
        except Exception as e:
            st.error(f"Erro ao calcular capital disponível: {str(e)}")
            return 0
        
    def _detect_chart_patterns(self, condition: AssetCondition) -> List[Dict]:
        """Detecta padrões gráficos comuns no preço atual"""
        patterns = []
        
        # 1. Hammer (martelo) - padrão de reversão de baixa
        if (condition.price > condition.bollinger_band["lower"] * 1.01 and 
            condition.rsi < 35 and 
            condition.volume > 1000000):
            patterns.append({
                "name": "Hammer",
                "confidence": 0.7,
                "direction": "bullish"
            })
        
        # 2. Shooting Star (estrela cadente) - padrão de reversão de alta
        if (condition.price < condition.bollinger_band["upper"] * 0.99 and 
            condition.rsi > 65 and 
            condition.volume > 1000000):
            patterns.append({
                "name": "Shooting Star",
                "confidence": 0.7,
                "direction": "bearish"
            })
        
        # 3. Head and Shoulders (cabeça e ombros)
        # (Implementação simplificada - em produção seria mais complexa)
        if (condition.price < condition.bollinger_band["middle"] and 
            condition.rsi > 60 and condition.rsi < 70):
            patterns.append({
                "name": "Potential Head and Shoulders",
                "confidence": 0.6,
                "direction": "bearish"
            })
        
        return patterns
    
    def _check_news_impact(self) -> str:
        """Simula a verificação de impacto de notícias"""
        # Em uma implementação real, isso se conectaria a uma API de notícias
        return random.choice(['positive', 'neutral', 'negative'])

    def _get_time_seasonality(self) -> str:
        """Retorna fatores sazonais"""
        now = pd.Timestamp.now()
        
        # Fim de mês - fluxo de capital
        if now.day >= 25:
            return "month_end"
        
        # Fim de semana - redução de liquidez
        if now.weekday() >= 4:  # Sexta-feira ou sábado
            return "weekend_effect"
        
        # Horário de abertura/fechamento
        if now.hour in [10, 16]:  # Abertura e fechamento do mercado
            return "market_open_close"
        
        return "normal"
        
    def _close_all_positions(self):
        """Fecha TODAS as posições com confirmação"""
        if not st.session_state.get('panic_confirmed', False):
            st.error("""
            🔥 ATENÇÃO: TEM CERTEZA QUE QUER FECHAR TODAS AS POSIÇÕES?
            Esta ação executará ordens de mercado para todas as posições abertas.
            """)
            
            if st.button("CONFIRMAR FECHAMENTO TOTAL", type="primary", key="confirm_panic"):
                st.session_state.panic_confirmed = True
                st.rerun()
            return
        
        # Execução real do fechamento
        try:
            # Fecha operações base
            for trade in st.session_state.portfolio.core_trades.values():
                self.system.broker.execute_close(trade)
            
            # Fecha combinações
            for combo in st.session_state.portfolio.multi_trades:
                self.system.broker.execute_close(combo)
            
            st.success("Todas as posições foram fechadas com sucesso!")
            self._trigger_alert('danger', 'TODAS AS POSIÇÕES FORAM LIQUIDADAS!')
        except Exception as e:
            st.error(f"Erro ao fechar posições: {str(e)}")
        finally:
            st.session_state.panic_confirmed = False