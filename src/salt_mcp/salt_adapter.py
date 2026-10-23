from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional


class SaltAdapter:
    """Async adapter wrapping SaltStack LocalClient, Key, and RunnerClient."""

    def __init__(
        self,
        local_client: Optional[Any] = None,
        key_client: Optional[Any] = None,
        runner_client: Optional[Any] = None,
        mopts: Optional[Dict[str, Any]] = None,
    ):
        self._local_client = local_client
        self._key_client = key_client
        self._runner_client = runner_client
        self._mopts = mopts

    def _get_local_client(self) -> Any:
        if self._local_client is None:
            try:
                import salt.client
                self._local_client = salt.client.LocalClient(mopts=self._mopts)
            except ImportError as e:
                raise RuntimeError(
                    "Không thể import module 'salt.client'. Hãy chắc chắn package 'salt' "
                    "được cài đặt và server đang chạy trên Salt Master."
                ) from e
        return self._local_client

    def _get_key_client(self) -> Any:
        if self._key_client is None:
            try:
                import salt.key
                import salt.config
                opts = self._mopts or salt.config.client_config("/etc/salt/master")
                self._key_client = salt.key.Key(opts)
            except ImportError as e:
                raise RuntimeError(
                    "Không thể import module 'salt.key'. Hãy chắc chắn package 'salt' "
                    "được cài đặt và server đang chạy trên Salt Master."
                ) from e
        return self._key_client

    def _get_runner_client(self) -> Any:
        if self._runner_client is None:
            try:
                import salt.runner
                import salt.config
                opts = self._mopts or salt.config.client_config("/etc/salt/master")
                self._runner_client = salt.runner.RunnerClient(opts)
            except ImportError as e:
                raise RuntimeError(
                    "Không thể import module 'salt.runner'. Hãy chắc chắn package 'salt' "
                    "được cài đặt và server đang chạy trên Salt Master."
                ) from e
        return self._runner_client

    async def cmd(
        self,
        tgt: str,
        fun: str,
        arg: Optional[List[Any]] = None,
        kwarg: Optional[Dict[str, Any]] = None,
        tgt_type: str = "glob",
        timeout: int = 60,
    ) -> Dict[str, Any]:
        """Runs a command on target minions via LocalClient."""
        client = self._get_local_client()
        return await asyncio.to_thread(
            client.cmd,
            tgt,
            fun,
            arg=arg,
            kwarg=kwarg,
            tgt_type=tgt_type,
            timeout=timeout,
        )

    async def list_keys(self) -> Dict[str, Any]:
        """Lists minion keys via salt.key.Key."""
        key = self._get_key_client()
        return await asyncio.to_thread(key.list_keys)

    async def manage_key(self, action: str, match: str) -> Dict[str, Any]:
        """Performs accept/reject/delete on minion keys."""
        key = self._get_key_client()

        def _manage():
            if action == "accept":
                res = key.accept(match=match)
            elif action == "reject":
                res = key.reject(match=match)
            elif action == "delete":
                res = key.delete_key(match=match)
            else:
                raise ValueError(f"Hành động key không hợp lệ: '{action}'")
            return {"success": bool(res), "action": action, "match": match}

        return await asyncio.to_thread(_manage)

    async def run_job(self, fun: str, kwarg: Optional[Dict[str, Any]] = None) -> Any:
        """Executes a runner module (e.g. jobs.lookup_jid, jobs.active)."""
        runner = self._get_runner_client()
        return await asyncio.to_thread(runner.cmd, fun, kwarg=kwarg)
