from __future__ import annotations

import json
import os
from contextlib import contextmanager
from typing import Any, Iterator
from uuid import uuid4

try:
	import psycopg
	from psycopg import sql as psycopg_sql
except Exception:  # pragma: no cover - optional dependency in some local test paths
	psycopg = None
	psycopg_sql = None

try:
	import redis
except Exception:  # pragma: no cover - optional dependency in some local test paths
	redis = None

try:
	from neo4j import GraphDatabase
except Exception:  # pragma: no cover - optional dependency in some local test paths
	GraphDatabase = None

try:
	from openai import OpenAI
except Exception:  # pragma: no cover - optional dependency in some local test paths
	OpenAI = None


def _json_default(value: Any) -> Any:
	if hasattr(value, "model_dump"):
		return value.model_dump()
	if isinstance(value, set):
		return sorted(value)
	return str(value)


def _safe_json_loads(payload: Any) -> Any:
	if payload in {None, ""}:
		return None
	if isinstance(payload, (dict, list)):
		return payload
	try:
		return json.loads(str(payload))
	except Exception:  # noqa: BLE001
		return payload


def _vector_literal(values: list[float]) -> str:
	return "[" + ",".join(f"{float(item):.8f}" for item in values) + "]"


def _validated_embedding_dimensions(value: int) -> int:
	return max(8, min(int(value), 3_072))


def _vector_type_sql(dimensions: int) -> Any:
	assert psycopg_sql is not None
	return psycopg_sql.SQL("vector({})").format(
		psycopg_sql.SQL(str(_validated_embedding_dimensions(dimensions)))
	)


class _BasePostgresService:
	def __init__(self, dsn: str) -> None:
		self.dsn = str(dsn or "").strip()
		self.enabled = bool(self.dsn) and psycopg is not None
		self._initialized = False

	@contextmanager
	def _connect(self) -> Iterator[Any]:
		if not self.enabled:
			raise RuntimeError("Postgres service is not enabled")
		assert psycopg is not None
		with psycopg.connect(self.dsn, autocommit=True) as connection:
			yield connection

	def healthcheck(self) -> bool:
		if not self.enabled:
			return False
		try:
			with self._connect() as connection:
				with connection.cursor() as cursor:
					cursor.execute("SELECT 1")
					row = cursor.fetchone()
			return bool(row and row[0] == 1)
		except Exception:  # noqa: BLE001
			return False


class PostgresStateStore(_BasePostgresService):
	def initialize(self) -> None:
		if not self.enabled or self._initialized:
			return
		with self._connect() as connection:
			with connection.cursor() as cursor:
				cursor.execute(
					"""
					CREATE TABLE IF NOT EXISTS frontier_state_store (
						state_key TEXT PRIMARY KEY,
						payload JSONB NOT NULL,
						updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now())
					)
					"""
				)
		self._initialized = True

	def load_state(self) -> dict[str, Any] | None:
		if not self.enabled:
			return None
		self.initialize()
		with self._connect() as connection:
			with connection.cursor() as cursor:
				cursor.execute(
					"SELECT payload FROM frontier_state_store WHERE state_key = %s",
					("global",),
				)
				row = cursor.fetchone()
		if not row:
			return None
		payload = row[0]
		if isinstance(payload, dict):
			return payload
		return _safe_json_loads(payload)

	def save_state(self, payload: dict[str, Any]) -> None:
		if not self.enabled:
			return
		self.initialize()
		encoded_payload = json.dumps(payload, default=_json_default)
		with self._connect() as connection:
			with connection.cursor() as cursor:
				cursor.execute(
					"""
					INSERT INTO frontier_state_store (state_key, payload, updated_at)
					VALUES (%s, %s::jsonb, timezone('utc', now()))
					ON CONFLICT (state_key)
					DO UPDATE SET payload = EXCLUDED.payload, updated_at = EXCLUDED.updated_at
					""",
					("global", encoded_payload),
				)


class RedisMemoryStore:
	def __init__(self, url: str) -> None:
		self.url = str(url or "").strip()
		self.enabled = bool(self.url) and redis is not None
		self._client = redis.from_url(self.url, decode_responses=True) if self.enabled else None
		self.max_entries = max(10, int(os.getenv("FRONTIER_SHORT_TERM_MEMORY_MAX", "200")))

	def _key(self, session_id: str) -> str:
		return f"frontier:memory:short:{session_id}"

	def _nonce_key(self, nonce: str) -> str:
		return f"frontier:a2a:nonce:{nonce}"

	def healthcheck(self) -> bool:
		if not self.enabled or self._client is None:
			return False
		try:
			return bool(self._client.ping())
		except Exception:  # noqa: BLE001
			return False

	def get_entries(self, session_id: str, *, limit: int = 100) -> list[dict[str, Any]]:
		if not self.enabled or self._client is None:
			return []
		try:
			start = -max(1, limit)
			payloads = self._client.lrange(self._key(session_id), start, -1)
		except Exception:  # noqa: BLE001
			return []
		entries: list[dict[str, Any]] = []
		for item in payloads:
			decoded = _safe_json_loads(item)
			if isinstance(decoded, dict):
				entries.append(decoded)
		return entries

	def append_entry(self, session_id: str, entry: dict[str, Any]) -> None:
		if not self.enabled or self._client is None:
			return
		try:
			self._client.rpush(self._key(session_id), json.dumps(entry, default=_json_default))
			self._client.ltrim(self._key(session_id), -self.max_entries, -1)
		except Exception:  # noqa: BLE001
			return

	def load_entries(self, session_id: str, entries: list[dict[str, Any]]) -> None:
		if not self.enabled or self._client is None or not entries:
			return
		try:
			serialized = [json.dumps(item, default=_json_default) for item in entries if isinstance(item, dict)]
			if not serialized:
				return
			self._client.rpush(self._key(session_id), *serialized)
			self._client.ltrim(self._key(session_id), -self.max_entries, -1)
		except Exception:  # noqa: BLE001
			return

	def clear_entries(self, session_id: str) -> None:
		if not self.enabled or self._client is None:
			return
		try:
			self._client.delete(self._key(session_id))
		except Exception:  # noqa: BLE001
			return

	def register_nonce_once(self, nonce: str, *, ttl_seconds: int) -> bool:
		if not self.enabled or self._client is None:
			return False
		nonce_text = str(nonce or "").strip()
		if not nonce_text:
			return False
		try:
			created = self._client.set(self._nonce_key(nonce_text), "1", ex=max(1, int(ttl_seconds)), nx=True)
		except Exception:  # noqa: BLE001
			return False
		return bool(created)


class PostgresLongTermMemoryStore(_BasePostgresService):
	def __init__(self, dsn: str) -> None:
		super().__init__(dsn)
		self.vector_enabled = False
		self.embedding_dimensions = _validated_embedding_dimensions(
			int(os.getenv("FRONTIER_MEMORY_EMBEDDING_DIMENSIONS", "1536"))
		)
		self.embedding_model = str(os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small") or "text-embedding-3-small").strip()
		self._openai_client: Any | None = None

	def initialize(self) -> None:
		if not self.enabled or self._initialized:
			return

		with self._connect() as connection:
			with connection.cursor() as cursor:
				try:
					cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")
				except Exception:  # noqa: BLE001
					pass

				try:
					cursor.execute("SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector')")
					row = cursor.fetchone()
					self.vector_enabled = bool(row and row[0])
				except Exception:  # noqa: BLE001
					self.vector_enabled = False

				cursor.execute(
					"""
					CREATE TABLE IF NOT EXISTS frontier_long_term_memory (
						id TEXT PRIMARY KEY,
						bucket_id TEXT NOT NULL,
						session_id TEXT NOT NULL,
						memory_scope TEXT NOT NULL,
						source TEXT NOT NULL,
						task_id TEXT,
						content TEXT NOT NULL,
						metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
						embedding_model TEXT,
						embedding_json JSONB,
						created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now()),
						updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now())
					)
					"""
				)
				if self.vector_enabled:
					cursor.execute(
						psycopg_sql.SQL(
							"ALTER TABLE frontier_long_term_memory ADD COLUMN IF NOT EXISTS embedding {}"
						).format(_vector_type_sql(self.embedding_dimensions))
					)
				cursor.execute(
					"CREATE INDEX IF NOT EXISTS frontier_long_term_memory_bucket_idx ON frontier_long_term_memory (bucket_id, created_at DESC)"
				)
				cursor.execute(
					"CREATE INDEX IF NOT EXISTS frontier_long_term_memory_session_idx ON frontier_long_term_memory (session_id, created_at DESC)"
				)
				cursor.execute(
					"CREATE INDEX IF NOT EXISTS frontier_long_term_memory_scope_idx ON frontier_long_term_memory (memory_scope, created_at DESC)"
				)
				cursor.execute(
					"""
					CREATE TABLE IF NOT EXISTS frontier_memory_consolidation_queue (
						id TEXT PRIMARY KEY,
						entry_id TEXT NOT NULL UNIQUE,
						bucket_id TEXT NOT NULL,
						session_id TEXT NOT NULL,
						memory_scope TEXT NOT NULL,
						source TEXT NOT NULL,
						task_id TEXT,
						candidate_kind TEXT NOT NULL DEFAULT 'promotion',
						status TEXT NOT NULL DEFAULT 'pending',
						content TEXT NOT NULL,
						metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
						created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now()),
						updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now())
					)
					"""
				)
				cursor.execute(
					"CREATE INDEX IF NOT EXISTS frontier_memory_consolidation_queue_status_idx ON frontier_memory_consolidation_queue (status, created_at DESC)"
				)
				cursor.execute(
					"CREATE INDEX IF NOT EXISTS frontier_memory_consolidation_queue_bucket_idx ON frontier_memory_consolidation_queue (bucket_id, created_at DESC)"
				)
				cursor.execute(
					"CREATE INDEX IF NOT EXISTS frontier_memory_consolidation_queue_scope_idx ON frontier_memory_consolidation_queue (memory_scope, created_at DESC)"
				)
				if self.vector_enabled:
					try:
						cursor.execute(
							"CREATE INDEX IF NOT EXISTS frontier_long_term_memory_embedding_idx ON frontier_long_term_memory USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
						)
					except Exception:  # noqa: BLE001
						pass
		self._initialized = True

	def _get_openai_client(self) -> Any | None:
		if OpenAI is None:
			return None
		api_key = str(os.getenv("OPENAI_API_KEY", "") or "").strip()
		if not api_key:
			return None
		if self._openai_client is None:
			self._openai_client = OpenAI(api_key=api_key)
		return self._openai_client

	def _embed_text(self, text: str) -> tuple[list[float] | None, str | None]:
		if not text.strip():
			return None, None
		client = self._get_openai_client()
		if client is None:
			return None, None
		try:
			response = client.embeddings.create(model=self.embedding_model, input=text[:8000])
			vector = response.data[0].embedding if getattr(response, "data", None) else None
		except Exception:  # noqa: BLE001
			return None, None
		if not isinstance(vector, list) or not vector:
			return None, None
		return [float(value) for value in vector], self.embedding_model

	def _row_to_entry(self, row: tuple[Any, ...]) -> dict[str, Any]:
		created_at = row[8]
		metadata = _safe_json_loads(row[7]) if row[7] is not None else {}
		payload = dict(metadata) if isinstance(metadata, dict) else {}
		payload.update({
			"id": str(row[0]),
			"bucket_id": str(row[1]),
			"session_id": str(row[2]),
			"memory_scope": str(row[3]),
			"source": str(row[4]),
			"task_id": str(row[5] or ""),
			"content": str(row[6]),
			"metadata": metadata if isinstance(metadata, dict) else {},
			"at": created_at.isoformat() if hasattr(created_at, "isoformat") else str(created_at or ""),
			"tier": "long-term",
		})
		return payload

	def _row_to_consolidation_candidate(self, row: tuple[Any, ...]) -> dict[str, Any]:
		created_at = row[9]
		updated_at = row[10]
		metadata = _safe_json_loads(row[12]) if row[12] is not None else {}
		payload = dict(metadata) if isinstance(metadata, dict) else {}
		payload.update({
			"id": str(row[0]),
			"entry_id": str(row[1]),
			"bucket_id": str(row[2]),
			"session_id": str(row[3]),
			"memory_scope": str(row[4]),
			"source": str(row[5]),
			"task_id": str(row[6] or ""),
			"candidate_kind": str(row[7]),
			"status": str(row[8]),
			"content": str(row[11]),
			"metadata": metadata if isinstance(metadata, dict) else {},
			"created_at": created_at.isoformat() if hasattr(created_at, "isoformat") else str(created_at or ""),
			"updated_at": updated_at.isoformat() if hasattr(updated_at, "isoformat") else str(updated_at or ""),
		})
		return payload

	def _filters(
		self,
		*,
		bucket_id: str | None = None,
		session_id: str | None = None,
		memory_scope: str | None = None,
		status: str | None = None,
		extra_clauses: list[Any] | None = None,
	) -> tuple[Any, list[Any]]:
		assert psycopg_sql is not None
		clauses: list[Any] = []
		params: list[Any] = []
		column_map = {
			"bucket_id": psycopg_sql.Identifier("bucket_id"),
			"session_id": psycopg_sql.Identifier("session_id"),
			"memory_scope": psycopg_sql.Identifier("memory_scope"),
			"status": psycopg_sql.Identifier("status"),
		}
		if bucket_id:
			clauses.append(psycopg_sql.SQL("{} = %s").format(column_map["bucket_id"]))
			params.append(bucket_id)
		if session_id:
			clauses.append(psycopg_sql.SQL("{} = %s").format(column_map["session_id"]))
			params.append(session_id)
		if memory_scope:
			clauses.append(psycopg_sql.SQL("{} = %s").format(column_map["memory_scope"]))
			params.append(memory_scope)
		if status:
			clauses.append(psycopg_sql.SQL("{} = %s").format(column_map["status"]))
			params.append(status)
		if extra_clauses:
			clauses.extend(extra_clauses)
		where_sql = psycopg_sql.SQL("")
		if clauses:
			where_sql = psycopg_sql.SQL(" WHERE ") + psycopg_sql.SQL(" AND ").join(clauses)
		return where_sql, params

	def get_entries(
		self,
		*,
		bucket_id: str | None = None,
		session_id: str | None = None,
		memory_scope: str | None = None,
		limit: int = 100,
	) -> list[dict[str, Any]]:
		if not self.enabled:
			return []
		self.initialize()
		where_sql, params = self._filters(bucket_id=bucket_id, session_id=session_id, memory_scope=memory_scope)
		with self._connect() as connection:
			with connection.cursor() as cursor:
				cursor.execute(
					psycopg_sql.SQL(
						"""
						SELECT id, bucket_id, session_id, memory_scope, source, task_id, content, metadata, created_at
						FROM frontier_long_term_memory
						"""
					)
					+ where_sql
					+ psycopg_sql.SQL(
						"""
						ORDER BY created_at DESC
						LIMIT %s
						"""
					),
					(*params, max(1, limit)),
				)
				rows = cursor.fetchall()
		return [self._row_to_entry(row) for row in reversed(rows)]

	def search_entries(
		self,
		query_text: str,
		*,
		bucket_id: str | None = None,
		session_id: str | None = None,
		memory_scope: str | None = None,
		limit: int = 10,
	) -> list[dict[str, Any]]:
		if not self.enabled:
			return []
		normalized_query = str(query_text or "").strip()
		if not normalized_query:
			return self.get_entries(bucket_id=bucket_id, session_id=session_id, memory_scope=memory_scope, limit=limit)

		self.initialize()
		where_sql, params = self._filters(bucket_id=bucket_id, session_id=session_id, memory_scope=memory_scope)
		vector, _model = self._embed_text(normalized_query)
		with self._connect() as connection:
			with connection.cursor() as cursor:
				if self.vector_enabled and vector:
					vector_where, vector_params = self._filters(
						bucket_id=bucket_id,
						session_id=session_id,
						memory_scope=memory_scope,
						extra_clauses=[psycopg_sql.SQL("embedding IS NOT NULL")],
					)
					cursor.execute(
						psycopg_sql.SQL(
							"""
							SELECT id, bucket_id, session_id, memory_scope, source, task_id, content, metadata, created_at
							FROM frontier_long_term_memory
							"""
						)
						+ vector_where
						+ psycopg_sql.SQL(
							"""
							ORDER BY embedding <=> %s::vector, created_at DESC
							LIMIT %s
							"""
						),
						(*vector_params, _vector_literal(vector), max(1, limit)),
					)
					rows = cursor.fetchall()
				else:
					pattern = f"%{normalized_query[:200]}%"
					lexical_where, lexical_params = self._filters(
						bucket_id=bucket_id,
						session_id=session_id,
						memory_scope=memory_scope,
						extra_clauses=[psycopg_sql.SQL("(content ILIKE %s OR metadata::text ILIKE %s)")],
					)
					cursor.execute(
						psycopg_sql.SQL(
							"""
							SELECT id, bucket_id, session_id, memory_scope, source, task_id, content, metadata, created_at
							FROM frontier_long_term_memory
							"""
						)
						+ lexical_where
						+ psycopg_sql.SQL(
							"""
							ORDER BY created_at DESC
							LIMIT %s
							"""
						),
						(*lexical_params, pattern, pattern, max(1, limit)),
					)
					rows = cursor.fetchall()
		return [self._row_to_entry(row) for row in rows]

	def append_entry(
		self,
		*,
		bucket_id: str,
		session_id: str,
		memory_scope: str,
		entry: dict[str, Any],
		source: str,
		task_id: str | None = None,
	) -> None:
		if not self.enabled:
			return
		self.initialize()
		content = str(entry.get("content") or json.dumps(entry, default=_json_default))[:4000]
		metadata = dict(entry) if isinstance(entry, dict) else {"raw": entry}
		entry_id = str(entry.get("id") or uuid4())
		vector, embedding_model = self._embed_text(content)
		encoded_metadata = json.dumps(metadata, default=_json_default)
		encoded_embedding = json.dumps(vector, default=_json_default) if vector else None

		with self._connect() as connection:
			with connection.cursor() as cursor:
				if self.vector_enabled and vector:
					cursor.execute(
						"""
						INSERT INTO frontier_long_term_memory (
							id, bucket_id, session_id, memory_scope, source, task_id, content,
							metadata, embedding_model, embedding_json, embedding, created_at, updated_at
						)
						VALUES (
							%s, %s, %s, %s, %s, %s, %s,
							%s::jsonb, %s, %s::jsonb, %s::vector, timezone('utc', now()), timezone('utc', now())
						)
						ON CONFLICT (id)
						DO UPDATE SET
							bucket_id = EXCLUDED.bucket_id,
							session_id = EXCLUDED.session_id,
							memory_scope = EXCLUDED.memory_scope,
							source = EXCLUDED.source,
							task_id = EXCLUDED.task_id,
							content = EXCLUDED.content,
							metadata = EXCLUDED.metadata,
							embedding_model = EXCLUDED.embedding_model,
							embedding_json = EXCLUDED.embedding_json,
							embedding = EXCLUDED.embedding,
							updated_at = timezone('utc', now())
						""",
						(
							entry_id,
							bucket_id,
							session_id,
							memory_scope,
							source,
							task_id,
							content,
							encoded_metadata,
							embedding_model,
							encoded_embedding,
							_vector_literal(vector),
						),
					)
				else:
					cursor.execute(
						"""
						INSERT INTO frontier_long_term_memory (
							id, bucket_id, session_id, memory_scope, source, task_id, content,
							metadata, embedding_model, embedding_json, created_at, updated_at
						)
						VALUES (
							%s, %s, %s, %s, %s, %s, %s,
							%s::jsonb, %s, %s::jsonb, timezone('utc', now()), timezone('utc', now())
						)
						ON CONFLICT (id)
						DO UPDATE SET
							bucket_id = EXCLUDED.bucket_id,
							session_id = EXCLUDED.session_id,
							memory_scope = EXCLUDED.memory_scope,
							source = EXCLUDED.source,
							task_id = EXCLUDED.task_id,
							content = EXCLUDED.content,
							metadata = EXCLUDED.metadata,
							embedding_model = EXCLUDED.embedding_model,
							embedding_json = EXCLUDED.embedding_json,
							updated_at = timezone('utc', now())
						""",
						(
							entry_id,
							bucket_id,
							session_id,
							memory_scope,
							source,
							task_id,
							content,
							encoded_metadata,
							embedding_model,
							encoded_embedding,
						),
					)

	def enqueue_consolidation_candidate(
		self,
		*,
		bucket_id: str,
		session_id: str,
		memory_scope: str,
		entry: dict[str, Any],
		source: str,
		task_id: str | None = None,
		candidate_kind: str = "promotion",
	) -> None:
		if not self.enabled:
			return
		self.initialize()
		entry_id = str(entry.get("id") or uuid4())
		candidate_id = f"consolidation:{entry_id}"
		content = str(entry.get("content") or json.dumps(entry, default=_json_default))[:4000]
		metadata = dict(entry) if isinstance(entry, dict) else {"raw": entry}
		metadata.setdefault("queued_for_consolidation", True)
		metadata.setdefault("candidate_kind", candidate_kind)
		encoded_metadata = json.dumps(metadata, default=_json_default)

		with self._connect() as connection:
			with connection.cursor() as cursor:
				cursor.execute(
					"""
					INSERT INTO frontier_memory_consolidation_queue (
						id, entry_id, bucket_id, session_id, memory_scope, source, task_id,
						candidate_kind, status, content, metadata, created_at, updated_at
					)
					VALUES (
						%s, %s, %s, %s, %s, %s, %s,
						%s, 'pending', %s, %s::jsonb, timezone('utc', now()), timezone('utc', now())
					)
					ON CONFLICT (entry_id)
					DO UPDATE SET
						bucket_id = EXCLUDED.bucket_id,
						session_id = EXCLUDED.session_id,
						memory_scope = EXCLUDED.memory_scope,
						source = EXCLUDED.source,
						task_id = EXCLUDED.task_id,
						candidate_kind = EXCLUDED.candidate_kind,
						status = 'pending',
						content = EXCLUDED.content,
						metadata = EXCLUDED.metadata,
						updated_at = timezone('utc', now())
					""",
					(
						candidate_id,
						entry_id,
						bucket_id,
						session_id,
						memory_scope,
						source,
						task_id,
						str(candidate_kind or "promotion"),
						content,
						encoded_metadata,
					),
				)

	def list_consolidation_candidates(
		self,
		*,
		bucket_id: str | None = None,
		memory_scope: str | None = None,
		status: str | None = "pending",
		limit: int = 100,
	) -> list[dict[str, Any]]:
		if not self.enabled:
			return []
		self.initialize()
		where_sql, params = self._filters(bucket_id=bucket_id, memory_scope=memory_scope, status=status)

		with self._connect() as connection:
			with connection.cursor() as cursor:
				cursor.execute(
					psycopg_sql.SQL(
						"""
						SELECT id, entry_id, bucket_id, session_id, memory_scope, source, task_id,
						candidate_kind, status, created_at, updated_at, content, metadata
						FROM frontier_memory_consolidation_queue
						"""
					)
					+ where_sql
					+ psycopg_sql.SQL(
						"""
						ORDER BY created_at DESC
						LIMIT %s
						"""
					),
					(*params, max(1, limit)),
				)
				rows = cursor.fetchall()
		return [self._row_to_consolidation_candidate(row) for row in reversed(rows)]

	def mark_consolidation_candidate(
		self,
		candidate_id: str,
		*,
		status: str,
		extra_metadata: dict[str, Any] | None = None,
	) -> None:
		if not self.enabled:
			return
		self.initialize()

		with self._connect() as connection:
			with connection.cursor() as cursor:
				if isinstance(extra_metadata, dict) and extra_metadata:
					cursor.execute(
						"""
						UPDATE frontier_memory_consolidation_queue
						SET status = %s,
						metadata = COALESCE(metadata, '{}'::jsonb) || %s::jsonb,
						updated_at = timezone('utc', now())
						WHERE id = %s
						""",
						(str(status or "pending"), json.dumps(extra_metadata, default=_json_default), str(candidate_id)),
					)
				else:
					cursor.execute(
						"""
						UPDATE frontier_memory_consolidation_queue
						SET status = %s,
						updated_at = timezone('utc', now())
						WHERE id = %s
						""",
						(str(status or "pending"), str(candidate_id)),
					)

	def clear_entries(
		self,
		*,
		bucket_id: str | None = None,
		session_id: str | None = None,
		memory_scope: str | None = None,
	) -> None:
		if not self.enabled:
			return
		self.initialize()
		where_sql, params = self._filters(bucket_id=bucket_id, session_id=session_id, memory_scope=memory_scope)
		if not where_sql:
			return
		with self._connect() as connection:
			with connection.cursor() as cursor:
				cursor.execute(psycopg_sql.SQL("DELETE FROM frontier_long_term_memory") + where_sql, params)


class Neo4jRunGraph:
	def __init__(self, uri: str, username: str, password: str) -> None:
		self.uri = str(uri or "").strip()
		self.username = str(username or "").strip()
		self.password = str(password or "").strip()
		self.enabled = bool(self.uri and self.username and self.password and GraphDatabase is not None)
		self._driver = GraphDatabase.driver(self.uri, auth=(self.username, self.password)) if self.enabled else None

	def healthcheck(self) -> bool:
		if not self.enabled or self._driver is None:
			return False
		try:
			with self._driver.session() as session:
				result = session.run("RETURN 1 AS ok")
				row = result.single()
			return bool(row and row["ok"] == 1)
		except Exception:  # noqa: BLE001
			return False

	def record_run(self, *, run_id: str, title: str, agent: str | None, workflow: str | None) -> None:
		if not self.enabled or self._driver is None:
			return
		try:
			with self._driver.session() as session:
				session.run(
					"""
					MERGE (r:WorkflowRun {id: $run_id})
					SET r.title = $title,
						r.updated_at = datetime()
					WITH r
					FOREACH (_ IN CASE WHEN $agent IS NULL OR $agent = '' THEN [] ELSE [1] END |
						MERGE (a:Agent {name: $agent})
						MERGE (r)-[:EXECUTED_BY]->(a)
					)
					FOREACH (_ IN CASE WHEN $workflow IS NULL OR $workflow = '' THEN [] ELSE [1] END |
						MERGE (w:Workflow {name: $workflow})
						MERGE (r)-[:PART_OF]->(w)
					)
					""",
					{
						"run_id": run_id,
						"title": title,
						"agent": agent,
						"workflow": workflow,
					},
				)
		except Exception:  # noqa: BLE001
			return

	def project_memory_summary(self, *, projection: dict[str, Any]) -> None:
		if not self.enabled or self._driver is None:
			return

		owner = projection.get("owner") if isinstance(projection.get("owner"), dict) else {}
		memory = projection.get("memory") if isinstance(projection.get("memory"), dict) else {}
		topics = projection.get("topics") if isinstance(projection.get("topics"), list) else []
		evidences = projection.get("evidences") if isinstance(projection.get("evidences"), list) else []

		if not owner or not memory:
			return

		try:
			with self._driver.session() as session:
				session.run(
					"""
					MERGE (owner:KnowledgeOwner {id: $owner_id})
					SET owner.name = $owner_name,
						owner.owner_type = $owner_type,
						owner.memory_scope = $owner_scope,
						owner.updated_at = datetime()

					MERGE (memory:KnowledgeMemory {id: $memory_id})
					SET memory.content = $memory_content,
						memory.kind = $memory_kind,
						memory.bucket_id = $memory_bucket_id,
						memory.session_id = $memory_session_id,
						memory.memory_scope = $memory_scope,
						memory.candidate_kind = $candidate_kind,
						memory.source_count = $source_count,
						memory.created_at = $memory_created_at,
						memory.updated_at = datetime()

					MERGE (owner)-[rel:OWNS_MEMORY]->(memory)
					SET rel.memory_scope = $memory_scope,
						rel.updated_at = datetime()
					""",
					{
						"owner_id": str(owner.get("id") or ""),
						"owner_name": str(owner.get("name") or ""),
						"owner_type": str(owner.get("type") or "Owner"),
						"owner_scope": str(owner.get("memory_scope") or memory.get("memory_scope") or "session"),
						"memory_id": str(memory.get("id") or ""),
						"memory_content": str(memory.get("content") or ""),
						"memory_kind": str(memory.get("kind") or "memory-consolidation"),
						"memory_bucket_id": str(memory.get("bucket_id") or ""),
						"memory_session_id": str(memory.get("session_id") or ""),
						"memory_scope": str(memory.get("memory_scope") or "session"),
						"candidate_kind": str(memory.get("candidate_kind") or "promotion"),
						"source_count": int(memory.get("source_count") or 0),
						"memory_created_at": str(memory.get("at") or memory.get("created_at") or ""),
					},
				)

				if evidences:
					session.run(
						"""
						UNWIND $evidences AS evidence
						MERGE (memory:KnowledgeMemory {id: $memory_id})
						MERGE (source:MemoryEvidence {id: evidence.id})
						SET source.name = evidence.name,
							source.bucket_id = evidence.bucket_id,
							source.memory_scope = evidence.memory_scope,
							source.updated_at = datetime()
						MERGE (memory)-[rel:DERIVED_FROM]->(source)
						SET rel.updated_at = datetime()
						""",
						{
							"memory_id": str(memory.get("id") or ""),
							"evidences": [
								{
									"id": str(item.get("id") or ""),
									"name": str(item.get("name") or item.get("id") or ""),
									"bucket_id": str(item.get("bucket_id") or memory.get("bucket_id") or ""),
									"memory_scope": str(item.get("memory_scope") or memory.get("memory_scope") or "session"),
								}
								for item in evidences
								if isinstance(item, dict) and str(item.get("id") or "")
							],
						},
					)

				if topics:
					session.run(
						"""
						UNWIND $topics AS topic
						MERGE (owner:KnowledgeOwner {id: $owner_id})
						MERGE (memory:KnowledgeMemory {id: $memory_id})
						MERGE (node:KnowledgeTopic {id: topic.id})
						SET node.name = topic.name,
							node.weight = topic.weight,
							node.updated_at = datetime()
						MERGE (memory)-[rel:MENTIONS_TOPIC]->(node)
						SET rel.weight = topic.weight,
							rel.updated_at = datetime()
						MERGE (owner)-[owner_rel:RELATES_TO_TOPIC]->(node)
						SET owner_rel.updated_at = datetime()
						""",
						{
							"owner_id": str(owner.get("id") or ""),
							"memory_id": str(memory.get("id") or ""),
							"topics": [
								{
									"id": str(item.get("id") or ""),
									"name": str(item.get("name") or ""),
									"weight": int(item.get("weight") or 0),
								}
								for item in topics
								if isinstance(item, dict) and str(item.get("id") or "")
							],
						},
					)
		except Exception:  # noqa: BLE001
			return

	def query_memory_context(
		self,
		*,
		bucket_id: str,
		memory_scope: str,
		query_text: str = "",
		limit: int = 10,
	) -> dict[str, Any]:
		if not self.enabled or self._driver is None:
			return {"memories": [], "topics": [], "relations": []}

		owner_id = f"owner:{str(bucket_id or '').strip()}"
		bounded_limit = max(1, int(limit))
		query = str(query_text or "").strip().lower()
		memory_rows: list[dict[str, Any]] = []
		topic_rows: list[dict[str, Any]] = []

		try:
			with self._driver.session() as session:
				memory_result = session.run(
					"""
					MATCH (owner:KnowledgeOwner {id: $owner_id})-[:OWNS_MEMORY]->(memory:KnowledgeMemory)
					WHERE memory.memory_scope = $memory_scope
					AND ($query = '' OR toLower(memory.content) CONTAINS $query)
					RETURN memory.id AS id,
					memory.content AS content,
					memory.kind AS kind,
					memory.candidate_kind AS candidate_kind,
					memory.bucket_id AS bucket_id,
					memory.session_id AS session_id,
					memory.source_count AS source_count,
					memory.created_at AS created_at
					ORDER BY memory.created_at DESC
					LIMIT $limit
					""",
					{
						"owner_id": owner_id,
						"memory_scope": str(memory_scope or "session"),
						"query": query,
						"limit": bounded_limit,
					},
				)
				for row in memory_result:
					memory_rows.append(
						{
							"id": str(row.get("id") or ""),
							"content": str(row.get("content") or ""),
							"kind": str(row.get("kind") or "memory-consolidation"),
							"candidate_kind": str(row.get("candidate_kind") or "promotion"),
							"bucket_id": str(row.get("bucket_id") or bucket_id),
							"session_id": str(row.get("session_id") or bucket_id),
							"source_count": int(row.get("source_count") or 0),
							"tier": "world-graph",
							"at": str(row.get("created_at") or ""),
						}
					)

				topic_result = session.run(
					"""
					MATCH (owner:KnowledgeOwner {id: $owner_id})-[:RELATES_TO_TOPIC]->(topic:KnowledgeTopic)
					RETURN topic.id AS id,
					topic.name AS name,
					topic.weight AS weight
					ORDER BY topic.weight DESC, topic.name ASC
					LIMIT $limit
					""",
					{
						"owner_id": owner_id,
						"limit": bounded_limit,
					},
				)
				for row in topic_result:
					topic_rows.append(
						{
							"id": str(row.get("id") or ""),
							"name": str(row.get("name") or ""),
							"weight": int(row.get("weight") or 0),
						}
					)
		except Exception:  # noqa: BLE001
			return {"memories": [], "topics": [], "relations": []}

		relations = [
			{
				"type": "RELATES_TO_TOPIC",
				"from": owner_id,
				"to": str(topic.get("id") or ""),
			}
			for topic in topic_rows
			if str(topic.get("id") or "")
		]
		return {
			"memories": memory_rows,
			"topics": topic_rows,
			"relations": relations,
		}
