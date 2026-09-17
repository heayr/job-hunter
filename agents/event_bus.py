import json
import time
import queue
import threading
from typing import Dict, Any, List, Optional, Set


class AgentEventBus:
    """
    In-memory pub/sub event bus for streaming real-time agent events
    to multiple SSE (Server-Sent Events) listeners in browser UI and Extension.
    """
    _instance: Optional['AgentEventBus'] = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(AgentEventBus, cls).__new__(cls)
                cls._instance._subscribers: Dict[str, Set[queue.Queue]] = {}
                cls._sub_lock = threading.Lock()
            return cls._instance

    def publish(self, session_id: str, event_type: str, data: Optional[Dict[str, Any]] = None) -> None:
        """
        Publishes a structured event to all active subscribers for the session.
        """
        payload = {
            "session_id": session_id,
            "event": event_type,
            "timestamp": time.time(),
            "data": data or {}
        }
        raw_sse = f"event: {event_type}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"

        with self._sub_lock:
            subs = list(self._subscribers.get(session_id, set()))
            # Also notify wildcard subscribers (e.g. global monitoring)
            wildcard_subs = list(self._subscribers.get("*", set()))

        for q in subs + wildcard_subs:
            try:
                q.put_nowait(raw_sse)
            except queue.Full:
                pass

    def subscribe(self, session_id: str = "*", max_queue_size: int = 200) -> queue.Queue:
        """
        Subscribes to session events. Returns a thread-safe queue yielding SSE message strings.
        """
        q = queue.Queue(maxsize=max_queue_size)
        with self._sub_lock:
            if session_id not in self._subscribers:
                self._subscribers[session_id] = set()
            self._subscribers[session_id].add(q)
        return q

    def unsubscribe(self, session_id: str, q: queue.Queue) -> None:
        """
        Removes a subscriber queue.
        """
        with self._sub_lock:
            if session_id in self._subscribers:
                self._subscribers[session_id].discard(q)
                if not self._subscribers[session_id]:
                    del self._subscribers[session_id]


def get_event_bus() -> AgentEventBus:
    return AgentEventBus()


get_agent_event_bus = get_event_bus

