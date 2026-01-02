# flux_on/project/quantum/optimizer.py

import numpy as np
import math
from typing import Dict, List
from scipy.optimize import minimize
from collections import defaultdict
from project.config import TradeType, MarketState, AssetCondition, TraderProfile, TimeFrame, RiskLevel
from project.utils import safe_divide
import logging
logging.basicConfig(level=logging.INFO)

class QuantumTrader:
    """
    O motor que traduz o 'Fluxo Matemático' em estratégias de trading.
    Ele não apenas calcula, mas interpreta os padrões subjacentes do mercado.
    """
    def __init__(self):
        self.historical_data = self._load_historical_data()
        self.quantum_factors = self._init_quantum_factors()
        self.risk_parameters = self._init_risk_parameters()
        self.historical_avg_volume = 1000000  # Adicione esta linha com um valor padrão

    def _load_historical_data(self) -> Dict[str, Dict]:
        """Dados históricos com parâmetros ajustados para diferentes tipos de operação"""
        return {
            'long': {
                'base_prob': 0.55,
                'momentum_factor': 1.2,
                'volatility_adjustment': 0.8
            },
            'short': {
                'base_prob': 0.45,
                'reversal_factor': 1.3,
                'volatility_adjustment': 1.2
            },
            'breakout': {
                'base_prob': 0.5,
                'volume_sensitivity': 1.5,
                'time_decay': 0.01
            },
            'reversal': {
                'base_prob': 0.4,
                'rsi_sensitivity': 1.8,
                'bollinger_band_factor': 1.1
            },
            'scalping': {
                'base_prob': 0.6,
                'liquidity_factor': 1.4,
                'timeframe_adjustment': 0.7
            },
            'hedge': {
                'base_prob': 0.65,
                'correlation_threshold': 0.7
            }
        }

    def _init_quantum_factors(self) -> Dict[str, float]:
        """
        Fatores que representam constantes fundamentais do 'Fluxo Matemático' adaptado para trading.
        """
        return {
            'phi': 1.618,  # Proporção áurea para alocação ótima
            'pi': 3.14159,  # Para ciclos de mercado
            'e': 2.718,    # Para crescimento exponencial
            'gamma': 0.577 # Constante de Euler-Mascheroni para ajuste de risco
        }

    def _init_risk_parameters(self) -> Dict[str, float]:
        """Parâmetros de risco para diferentes tipos de operação"""
        return {
            'conservative': {
                'max_capital': 0.05,
                'stop_loss': 0.01,
                'take_profit': 0.03
            },
            'moderate': {
                'max_capital': 0.1,
                'stop_loss': 0.02,
                'take_profit': 0.06
            },
            'aggressive': {
                'max_capital': 0.15,
                'stop_loss': 0.03,
                'take_profit': 0.09
            },
            'hedge': {
                'max_capital': 0.2,
                'stop_loss': 0.015,
                'take_profit': 0.045
            }
        }

    def estimate_trade_probability(self, trade_type: TradeType, condition: AssetCondition, timeframe: TimeFrame) -> float:
        """
        Estima a probabilidade de sucesso de uma operação, ajustando aos dados de mercado em tempo real.
        """
        data = self.historical_data.get(trade_type.name.lower(), {'base_prob': 0.5})
        base_prob = data['base_prob']
        prob = base_prob
        
        # Ajustes baseados no tipo de operação
        if trade_type == TradeType.LONG:
            # Aumenta probabilidade se tendência de alta e RSI não sobrecomprado
            if condition.rsi < 70:
                prob *= (1 + (condition.macd if condition.macd > 0 else 0))
            # Reduz probabilidade se perto da banda superior de Bollinger
            if condition.price > condition.bollinger_band['upper'] * 0.95:
                prob *= 0.7
                
        elif trade_type == TradeType.SHORT:
            # Aumenta probabilidade se tendência de baixa e RSI não sobrevendido
            if condition.rsi > 30:
                prob *= (1 + abs(condition.macd) if condition.macd < 0 else 1)
            # Reduz probabilidade se perto da banda inferior de Bollinger
            if condition.price < condition.bollinger_band['lower'] * 1.05:
                prob *= 0.7
                
        elif trade_type == TradeType.BREAKOUT:
            # Aumenta probabilidade com volume acima da média
            volume_factor = min(2.0, condition.volume / (self.historical_avg_volume + 1e-6))
            prob *= volume_factor ** 0.5
            # Reduz probabilidade em mercados sem tendência
            if 'no_trend' in condition.market_context:
                prob *= 0.6
                
        elif trade_type == TradeType.REVERSAL:
            # Aumenta probabilidade com RSI extremo
            rsi_factor = 1.0
            if condition.rsi > 70 or condition.rsi < 30:
                rsi_factor = 1.5
            prob *= rsi_factor
            # Ajuste para timeframe - reversais melhores em prazos maiores
            if timeframe in [TimeFrame.M1, TimeFrame.M5]:
                prob *= 0.8
                
        elif trade_type == TradeType.SCALPING:
            # Aumenta probabilidade com alta liquidez
            liquidity_factor = min(1.5, condition.volume / (self.historical_avg_volume + 1e-6))
            prob *= liquidity_factor
            # Melhor em timeframes curtos
            if timeframe in [TimeFrame.M15, TimeFrame.M30]:
                prob *= 1.2
                
        elif trade_type == TradeType.HEDGE:
            # Probabilidade baseada na correlação
            correlation = self._get_asset_correlation(condition.asset)
            prob *= (correlation ** 2)  # Correlação quadrática para hedge

        # Ajuste final baseado na volatilidade
        volatility = self._calculate_volatility(condition)
        prob *= (1 + min(0.5, volatility * 0.1))  # Pequeno aumento com volatilidade controlada

        return min(0.95, max(0.05, prob))

    def _calculate_volatility(self, condition: AssetCondition) -> float:
        """Calcula a volatilidade baseada nas bandas de Bollinger"""
        bandwidth = (condition.bollinger_band['upper'] - condition.bollinger_band['lower']) / condition.bollinger_band['middle']
        return bandwidth * 100  # Volatilidade percentual

    def _get_asset_correlation(self, asset: str) -> float:
        """Simula a correlação do ativo com o mercado (implementação simplificada)"""
        correlations = {
            'IBOV': 0.9,
            'DOLAR': 0.6,
            'ACAO_INDIVIDUAL': 0.7,
            'CRIPTO': 0.4
        }
        return correlations.get(asset, 0.5)
    
    def _validate_trade_parameters(params):
        errors = []
        for trade_type, values in params.items():
            if values['entry_price'] <= values['stop_loss']:
                errors.append(f"{trade_type}: Preço entrada <= Stop Loss")
            if values['target_price'] <= values['entry_price']:
                errors.append(f"{trade_type}: Target Price <= Preço entrada")
            if abs(values['entry_price'] - values['stop_loss']) < 0.01:
                errors.append(f"{trade_type}: Diferença entrada/stop muito pequena")
        return errors

    def allocate_capital_to_trades(self, total_capital: float, normalized_weights: Dict[TradeType, float]) -> Dict[TradeType, float]:
        """
        Distribui o capital entre trades usando pesos normalizados,
        garantindo que não ocorra divisão por zero.
        
        Args:
            total_capital: Capital total disponível para a fase
            normalized_weights: Pesos finais normalizados das trades {TradeType: peso}
        
        Returns:
            Alocação de capital por trade {TradeType: capital_alocado}
        """
        # Garantir que existam trades e pesos válidos
        if not normalized_weights:
            logging.warning("Nenhum trade disponível para alocação. Retornando zeros.")
            return {}

        # Garantir soma > 0
        total_weight = sum(normalized_weights.values())
        if total_weight <= 0:
            logging.warning("Soma dos pesos inválida (<=0). Aplicando fallback igualitário.")
            num_trades = len(normalized_weights)
            return {t: total_capital / num_trades for t in normalized_weights}

        # Distribuição segura do capital
        allocation = {}
        for t, w in normalized_weights.items():
            allocation[t] = total_capital * w / total_weight

        return allocation

    def optimize_portfolio(
        self,
        available_trades: Dict[TradeType, float],
        condition: AssetCondition,
        market_state: MarketState,
        timeframe: TimeFrame,
        trader_profile: TraderProfile = None
    ) -> Dict[TradeType, float]:

        # 1️⃣ Pré-validação
        if not available_trades:
            logging.warning("Nenhuma operação disponível para otimização")
            return {}

        # 2️⃣ Filtragem de trades válidos
        selected_trades = {
            t: v for t, v in available_trades.items()
            if self._is_trade_valid(t, condition)
        }
        if not selected_trades:
            logging.warning("Nenhum trade válido após filtragem")
            return {}

        # 3️⃣ Cálculo de probabilidades com limites seguros
        trade_probs = {
            t: max(0.05, min(0.95, self.estimate_trade_probability(t, condition, timeframe)))
            for t in selected_trades
        }

        # 4️⃣ Cálculo de Risk/Reward com limites
        risk_rewards = {
            t: max(0.1, min(10.0, self._calculate_risk_reward(t, condition)))
            for t in selected_trades
        }

        # 5️⃣ Expected Value seguro
        ev_data = {
            t: max(0.01, (trade_probs[t] * risk_rewards[t]) - (1 - trade_probs[t]))
            for t in selected_trades
        }

        # 6️⃣ Aplicação de perfil do trader, se existir
        if trader_profile:
            for t in ev_data:
                weight_factor = trader_profile.asset_weights.get(condition.asset, 1.0)
                ev_data[t] *= max(0.01, weight_factor)

        # 7️⃣ Normalização robusta de EVs
        total_ev = sum(ev_data.values())
        if total_ev <= 0:
            logging.warning("Total de EVs <= 0, aplicando fallback conservador")
            fallback_weights = {t: 1.0 / len(ev_data) for t in ev_data}
            base_weights = fallback_weights
        else:
            base_weights = {t: ev / total_ev for t, ev in ev_data.items()}

        # 8️⃣ Aplicação de limites de risco
        final_weights = {}
        for t, w in base_weights.items():
            risk_level = self._get_risk_level(t, condition)
            max_alloc = self.risk_parameters.get(risk_level, {}).get('max_capital', 1.0)
            final_weights[t] = min(w, max_alloc)

        # 9️⃣ Garantir soma total = 1.0
        total_weight = sum(final_weights.values())
        if total_weight <= 0:
            logging.warning("Peso total final <= 0, fallback conservador aplicado")
            num_trades = len(final_weights)
            return {t: 1.0 / num_trades for t in final_weights}

        normalized_weights = {t: w / total_weight for t, w in final_weights.items()}

        logging.info(f"Pesos finais normalizados: {normalized_weights}")
        return normalized_weights

    def _is_trade_valid(self, trade_type: TradeType, condition: AssetCondition) -> bool:
        """Verificação rigorosa de viabilidade"""
        try:
            params = self._get_risk_parameters(trade_type, condition)
            return (
                params['stop_loss'] > 1e-8 and 
                params['take_profit'] > params['stop_loss']
            )
        except:
            return False
        
    def _filter_trades_by_market_state(self, trades: Dict[TradeType, float], market_state: MarketState) -> Dict[TradeType, float]:
        """Filtra operações baseado no estado do mercado"""
        filtered = {}
        
        for trade_type, value in trades.items():
            # Operações de tendência performam melhor em mercados estáveis
            if market_state == MarketState.ESTAVEL:
                if trade_type in [TradeType.LONG, TradeType.SHORT, TradeType.BREAKOUT]:
                    filtered[trade_type] = value
                    
            # Operações de reversão performam melhor em transição
            elif market_state == MarketState.TRANSICAO:
                if trade_type in [TradeType.REVERSAL, TradeType.SCALPING]:
                    filtered[trade_type] = value
                    
            # Operações de proteção e scalping em mercados caóticos
            elif market_state == MarketState.CAOTICO:
                if trade_type in [TradeType.HEDGE, TradeType.SCALPING]:
                    filtered[trade_type] = value
                    
            # Operações direcionais em tendências claras
            elif market_state == MarketState.TENDENCIA_ALTA:
                if trade_type == TradeType.LONG:
                    filtered[trade_type] = value
                    
            elif market_state == MarketState.TENDENCIA_BAIXA:
                if trade_type == TradeType.SHORT:
                    filtered[trade_type] = value
                    
        return filtered or trades  # Retorna todas se nenhum filtro aplicado

    def _calculate_risk_reward(self, trade_type: TradeType, condition: AssetCondition) -> float:
        """Versão totalmente segura com fallbacks"""
        try:
            risk_params = self._get_risk_parameters(trade_type, condition)
            take_profit = risk_params.get('take_profit', 0.03)  # Default 3%
            stop_loss = risk_params.get('stop_loss', 0.01)      # Default 1%
            
            if abs(stop_loss) < 1e-8:  # Evita divisão por zero
                return 0.0
                
            rr = take_profit / abs(stop_loss)
            return rr if rr > 0 else 0.0
        except Exception:
            return 0.0

    def _get_risk_level(self, trade_type: TradeType, condition: AssetCondition) -> str:
        """Determina o nível de risco para uma operação"""
        if trade_type in [TradeType.HEDGE, TradeType.PAIR_TRADING]:
            return 'hedge'
        elif trade_type in [TradeType.SCALPING, TradeType.REVERSAL]:
            return 'moderate'
        elif condition.rsi > 70 or condition.rsi < 30:
            return 'aggressive'
        return 'conservative'

    def _get_risk_parameters(self, trade_type: TradeType, condition: AssetCondition) -> Dict[str, float]:
        """Retorna parâmetros de risco para uma operação"""
        risk_level = self._get_risk_level(trade_type, condition)
        return self.risk_parameters[risk_level]

    def calculate_position_size(self, prob: float, risk_reward: float, capital: float, 
                                market_state: MarketState, risk_level: RiskLevel) -> float:

        if not prob or not risk_reward:
            logging.warning(f"Parâmetros inválidos: prob={prob}, risk_reward={risk_reward}")
            return 0.0

        # Fator de ajuste baseado no estado do mercado
        market_factor = {
            MarketState.ESTAVEL: 0.5,
            MarketState.TRANSICAO: 0.3,
            MarketState.CAOTICO: 0.1,
            MarketState.TENDENCIA_ALTA: 0.6,
            MarketState.TENDENCIA_BAIXA: 0.6
        }[market_state]

        # Fator de ajuste baseado no perfil de risco
        risk_factor = {
            RiskLevel.CONSERVADOR: 0.3,
            RiskLevel.MODERADO: 0.5,
            RiskLevel.AGRESSIVO: 0.7,
            RiskLevel.HEDGE: 0.4
        }[risk_level]

        # Kelly fraction adaptado com proteção segura
        if risk_reward == 0:
            kelly_fraction = 0.0
        else:
            kelly_fraction = (prob * risk_reward - (1 - prob)) / risk_reward

        if kelly_fraction <= 0:
            return 0.0

        position_size = capital * kelly_fraction * market_factor * risk_factor

        # Limites de segurança
        max_position = {
            RiskLevel.CONSERVADOR: 0.05,
            RiskLevel.MODERADO: 0.1,
            RiskLevel.AGRESSIVO: 0.15,
            RiskLevel.HEDGE: 0.2
        }[risk_level]

        return max(0.0, min(position_size, capital * max_position))

    def _get_correlation_matrix(self, trade_types: List[TradeType]) -> np.ndarray:
        """Matriz de correlação entre diferentes estratégias de trading"""
        correlations = {
            (TradeType.LONG, TradeType.SHORT): -1.0,
            (TradeType.LONG, TradeType.HEDGE_SHORT): -0.7,
            (TradeType.SHORT, TradeType.HEDGE_LONG): -0.7,
            (TradeType.BREAKOUT, TradeType.REVERSAL): -0.6,
            (TradeType.SCALPING, TradeType.MOMENTUM): 0.4,
            (TradeType.PAIR_TRADING, TradeType.HEDGE): 0.5,
        }
        
        size = len(trade_types)
        matrix = np.identity(size)
        
        for i in range(size):
            for j in range(i + 1, size):
                val = correlations.get((trade_types[i], trade_types[j]), 
                                    correlations.get((trade_types[j], trade_types[i]), 0.0))
                matrix[i, j] = matrix[j, i] = val
        return matrix