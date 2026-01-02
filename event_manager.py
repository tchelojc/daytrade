# project/event_manager.py
from typing import Any, Callable, Dict, List
import threading
import logging

logger = logging.getLogger(__name__)

class EventManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._events: Dict[str, List[Callable[[Any], None]]] = {}
        return cls._instance
    
    def subscribe(self, event_name: str, callback: Callable[[Any], None]) -> None:
        """Registra um callback para um tipo de evento com thread-safety"""
        with self._lock:
            if event_name not in self._events:
                self._events[event_name] = []
            self._events[event_name].append(callback)
    
    def publish(self, event_name: str, data: Any = None) -> None:
        """Dispara um evento para todos os subscribers com tratamento de erros"""
        callbacks = self._events.get(event_name, [])
        for callback in callbacks:
            try:
                callback(data)
            except Exception as e:
                logger.error(f"Error in event callback {callback.__name__}: {str(e)}", exc_info=True)

    def unsubscribe(self, event_name: str, callback: Callable[[Any], None]) -> bool:
        """Remove um callback específico de um evento"""
        with self._lock:
            if event_name in self._events and callback in self._events[event_name]:
                self._events[event_name].remove(callback)
                return True
        return False