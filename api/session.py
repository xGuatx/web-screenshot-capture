"""Gestion des sessions utilisateur avec cleanup automatique."""

import asyncio
import time
import uuid
import psutil
from typing import Dict, Optional
from collections import defaultdict

from api.config import settings, logger


class SessionManager:
    """Gere les sessions utilisateur et leur cleanup automatique."""

    def __init__(self):
        self.sessions: Dict[str, Dict] = {}
        self.cleanup_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

    def create_session(self) -> str:
        """
        Cree une nouvelle session.

        Returns:
            session_id (UUID)
        """
        session_id = str(uuid.uuid4())

        self.sessions[session_id] = {
            "created_at": time.time(),
            "last_activity": time.time(),
            "status": "active",
            "requests": []
        }

        logger.debug(f"Session creee: {session_id}")
        return session_id

    async def add_request(self, session_id: str, request_info: Dict):
        """Ajoute une requete a une session."""
        async with self._lock:
            if session_id in self.sessions:
                self.sessions[session_id]["requests"].append(request_info)
                self.sessions[session_id]["last_activity"] = time.time()

    async def cleanup_session(self, session_id: str):
        """Nettoie une session specifique."""
        async with self._lock:
            if session_id in self.sessions:
                del self.sessions[session_id]
                logger.debug(f"Session nettoyee: {session_id}")

    async def get_session(self, session_id: str) -> Optional[Dict]:
        """Recupere une session."""
        return self.sessions.get(session_id)

    def get_all_sessions(self) -> Dict:
        """Retourne toutes les sessions actives."""
        return {
            sid: {
                "created_at": s["created_at"],
                "last_activity": s["last_activity"],
                "age_seconds": int(time.time() - s["created_at"]),
                "status": s["status"],
                "request_count": len(s["requests"])
            }
            for sid, s in self.sessions.items()
        }

    async def _cleanup_loop(self):
        """Boucle de cleanup automatique."""
        logger.info(f"Demarrage cleanup automatique (intervalle: {settings.CLEANUP_INTERVAL}s)")

        while True:
            try:
                await asyncio.sleep(settings.CLEANUP_INTERVAL)

                now = time.time()
                to_remove = []

                async with self._lock:
                    for session_id, session in self.sessions.items():
                        age = now - session["last_activity"]

                        # Supprimer les sessions expirees
                        if age > settings.SESSION_TIMEOUT:
                            to_remove.append(session_id)
                            logger.info(f"Session expiree: {session_id} (inactivite: {int(age)}s)")

                    for session_id in to_remove:
                        del self.sessions[session_id]

                # Monitoring memoire
                mem = psutil.virtual_memory()
                if mem.percent > 85:
                    logger.warning(
                        f"[WARNING]  Memoire critique: {mem.percent}% "
                        f"({mem.used / 1024 / 1024:.0f}MB / {mem.total / 1024 / 1024:.0f}MB)"
                    )

                    # Force cleanup des plus vieilles sessions si critique
                    if mem.percent > 90:
                        await self._force_cleanup(keep_count=2)

                # Log periodique
                if len(self.sessions) > 0:
                    logger.debug(
                        f"Cleanup: {len(self.sessions)} sessions actives, "
                        f"RAM: {mem.percent}% ({mem.used / 1024 / 1024:.0f}MB)"
                    )

            except Exception as e:
                logger.error(f"Erreur dans cleanup loop: {e}")

    async def _force_cleanup(self, keep_count: int = 2):
        """Force le cleanup des plus vieilles sessions en cas de RAM critique."""
        logger.warning(f"Force cleanup - Conservation de {keep_count} sessions max")

        async with self._lock:
            # Trier par derniere activite
            sorted_sessions = sorted(
                self.sessions.items(),
                key=lambda x: x[1]["last_activity"],
                reverse=True
            )

            # Garder seulement les N plus recentes
            to_keep = {sid: data for sid, data in sorted_sessions[:keep_count]}
            removed_count = len(self.sessions) - len(to_keep)

            self.sessions = to_keep

            logger.warning(f"[+] Force cleanup termine: {removed_count} sessions supprimees")

    def start_cleanup(self):
        """Demarre la tache de cleanup automatique."""
        if self.cleanup_task is None or self.cleanup_task.done():
            self.cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.info("[+] Cleanup automatique demarre")

    async def stop_cleanup(self):
        """Arrete la tache de cleanup."""
        if self.cleanup_task and not self.cleanup_task.done():
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
            logger.info("[+] Cleanup automatique arrete")

    def get_stats(self) -> Dict:
        """Retourne les statistiques."""
        mem = psutil.virtual_memory()

        return {
            "active_sessions": len(self.sessions),
            "max_sessions": settings.MAX_CONCURRENT_SESSIONS,
            "memory_percent": mem.percent,
            "memory_used_mb": int(mem.used / 1024 / 1024),
            "memory_total_mb": int(mem.total / 1024 / 1024),
            "memory_available_mb": int(mem.available / 1024 / 1024)
        }


# Instance globale
session_manager = SessionManager()
