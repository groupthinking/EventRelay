#!/usr/bin/env python3
"""
DAG Executor - Parallel execution engine for pipeline stages.

Upgrades the sequential pipeline into a DAG (Directed Acyclic Graph) that runs
independent stages concurrently via asyncio.gather(), while respecting dependency
ordering via topological sort.

Think of it like a highway interchange vs a single-lane road:
- Sequential: A → B → C → D → E → F (each waits for the previous)
- DAG: A → [B, C, D] → E → F (B/C/D run simultaneously after A finishes)

The existing sequential pipeline remains the fallback - this layer sits on top.
"""

import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Coroutine, Optional

logger = logging.getLogger(__name__)


@dataclass
class StageDefinition:
    """Defines a single pipeline stage with its dependencies.

    Attributes:
        stage_id: Unique identifier for this stage
        dependencies: List of stage_ids that must complete before this one starts
        executor: Async callable that performs the stage's work
        description: Human-readable description for observability
        timeout_seconds: Max execution time before the stage is cancelled
    """

    stage_id: str
    dependencies: list[str] = field(default_factory=list)
    executor: Optional[Callable[..., Coroutine]] = None
    description: str = ""
    timeout_seconds: float = 300.0  # 5 minute default


@dataclass
class StageResult:
    """Result from executing a single stage."""

    stage_id: str
    success: bool
    data: dict[str, Any]
    duration_ms: float
    error: Optional[str] = None
    batch_index: int = 0  # Which parallel batch this ran in


class DAGValidationError(Exception):
    """Raised when the DAG has cycles or invalid dependencies."""

    pass


class DAGExecutor:
    """
    Executes pipeline stages as a DAG with parallel batching.

    Stages are grouped into batches via topological sort. Within each batch,
    all stages run concurrently. Between batches, execution is sequential
    (batch N must finish before batch N+1 starts).

    Usage:
        executor = DAGExecutor()
        executor.add_stage("ingest", dependencies=[])
        executor.add_stage("architect", dependencies=["ingest"])
        executor.add_stage("blueprint", dependencies=["ingest"])  # parallel with architect
        executor.add_stage("codegen", dependencies=["architect"])

        results = await executor.execute(context={...})
    """

    def __init__(self, on_event: Optional[Callable] = None):
        self.stages: dict[str, StageDefinition] = {}
        self._on_event = on_event  # Callback for pipeline events (e.g. emitter.emit)

    def add_stage(
        self,
        stage_id: str,
        dependencies: Optional[list[str]] = None,
        executor: Optional[Callable[..., Coroutine]] = None,
        description: str = "",
        timeout_seconds: float = 300.0,
    ) -> "DAGExecutor":
        """Register a stage in the DAG. Returns self for chaining."""
        self.stages[stage_id] = StageDefinition(
            stage_id=stage_id,
            dependencies=dependencies or [],
            executor=executor,
            description=description or stage_id,
            timeout_seconds=timeout_seconds,
        )
        return self

    def topological_batches(self) -> list[list[str]]:
        """
        Sort stages into execution batches using Kahn's algorithm.

        Returns a list of batches. Stages within each batch have no dependencies
        on each other and can run in parallel. Batches execute sequentially.

        Raises DAGValidationError if cycles exist or dependencies reference
        unknown stages.
        """
        # Validate all dependencies reference known stages
        for stage_id, stage in self.stages.items():
            for dep in stage.dependencies:
                if dep not in self.stages:
                    raise DAGValidationError(
                        f"Stage '{stage_id}' depends on unknown stage '{dep}'"
                    )

        # Build in-degree map
        in_degree: dict[str, int] = {sid: 0 for sid in self.stages}
        dependents: dict[str, list[str]] = defaultdict(list)

        for stage_id, stage in self.stages.items():
            for dep in stage.dependencies:
                in_degree[stage_id] += 1
                dependents[dep].append(stage_id)

        # Kahn's algorithm - collect nodes layer by layer
        batches: list[list[str]] = []
        ready = [sid for sid, deg in in_degree.items() if deg == 0]

        processed = 0
        while ready:
            # Sort within batch for deterministic ordering
            batch = sorted(ready)
            batches.append(batch)
            processed += len(batch)

            next_ready = []
            for sid in batch:
                for dependent in dependents[sid]:
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        next_ready.append(dependent)
            ready = next_ready

        if processed != len(self.stages):
            remaining = [sid for sid, deg in in_degree.items() if deg > 0]
            raise DAGValidationError(
                f"Cycle detected in DAG. Stages involved: {remaining}"
            )

        return batches

    async def execute(
        self,
        context: Optional[dict[str, Any]] = None,
        continue_on_error: bool = False,
    ) -> dict[str, StageResult]:
        """
        Execute the full DAG.

        Args:
            context: Shared mutable dict passed to all stage executors.
                     Each stage writes its output here for downstream stages to read.
            continue_on_error: If True, keep running even if a stage fails.
                              Failed stage outputs won't be available to dependents.

        Returns:
            Dict mapping stage_id → StageResult
        """
        context = context if context is not None else {}
        results: dict[str, StageResult] = {}
        batches = self.topological_batches()

        await self._emit("dag.started", {
            "total_stages": len(self.stages),
            "total_batches": len(batches),
            "batch_plan": [[sid for sid in batch] for batch in batches],
        })

        for batch_idx, batch in enumerate(batches):
            batch_start = datetime.now()

            await self._emit("batch.started", {
                "batch_index": batch_idx,
                "stages": batch,
                "parallel_count": len(batch),
            })

            # Check if any stage in this batch has a failed dependency
            runnable = []
            skipped = []
            for stage_id in batch:
                stage = self.stages[stage_id]
                deps_ok = all(
                    results.get(dep, StageResult(dep, False, {}, 0)).success
                    for dep in stage.dependencies
                )
                if deps_ok or continue_on_error:
                    runnable.append(stage_id)
                else:
                    skipped.append(stage_id)
                    results[stage_id] = StageResult(
                        stage_id=stage_id,
                        success=False,
                        data={},
                        duration_ms=0,
                        error="Skipped: dependency failed",
                        batch_index=batch_idx,
                    )

            # Execute all runnable stages in parallel
            if len(runnable) == 1:
                # Single stage — no gather overhead
                result = await self._execute_stage(
                    runnable[0], context, batch_idx
                )
                results[runnable[0]] = result
            elif len(runnable) > 1:
                # Parallel execution
                coros = [
                    self._execute_stage(sid, context, batch_idx)
                    for sid in runnable
                ]
                batch_results = await asyncio.gather(*coros, return_exceptions=True)

                for sid, res in zip(runnable, batch_results):
                    if isinstance(res, Exception):
                        results[sid] = StageResult(
                            stage_id=sid,
                            success=False,
                            data={},
                            duration_ms=0,
                            error=str(res),
                            batch_index=batch_idx,
                        )
                    else:
                        results[sid] = res

            batch_duration = (datetime.now() - batch_start).total_seconds() * 1000
            await self._emit("batch.completed", {
                "batch_index": batch_idx,
                "duration_ms": batch_duration,
                "results": {
                    sid: {"success": results[sid].success, "error": results[sid].error}
                    for sid in batch
                },
            })

            # Check if we should abort
            if not continue_on_error:
                batch_failures = [
                    sid for sid in batch if not results[sid].success
                ]
                if batch_failures:
                    logger.warning(
                        f"Batch {batch_idx} had failures: {batch_failures}. "
                        f"Aborting remaining batches."
                    )
                    # Mark remaining stages as skipped
                    for remaining_batch in batches[batch_idx + 1 :]:
                        for sid in remaining_batch:
                            results[sid] = StageResult(
                                stage_id=sid,
                                success=False,
                                data={},
                                duration_ms=0,
                                error="Skipped: earlier batch failed",
                                batch_index=-1,
                            )
                    break

        await self._emit("dag.completed", {
            "total_stages": len(self.stages),
            "successful": sum(1 for r in results.values() if r.success),
            "failed": sum(1 for r in results.values() if not r.success),
            "total_duration_ms": sum(r.duration_ms for r in results.values()),
        })

        return results

    async def _execute_stage(
        self,
        stage_id: str,
        context: dict[str, Any],
        batch_index: int,
    ) -> StageResult:
        """Execute a single stage with timeout and error handling."""
        stage = self.stages[stage_id]
        start = datetime.now()

        await self._emit("stage.started", {
            "stage_id": stage_id,
            "description": stage.description,
            "batch_index": batch_index,
        })

        if stage.executor is None:
            return StageResult(
                stage_id=stage_id,
                success=False,
                data={},
                duration_ms=0,
                error=f"No executor registered for stage '{stage_id}'",
                batch_index=batch_index,
            )

        try:
            result_data = await asyncio.wait_for(
                stage.executor(context),
                timeout=stage.timeout_seconds,
            )

            duration = (datetime.now() - start).total_seconds() * 1000

            # Store output in shared context for downstream stages
            context[f"{stage_id}_output"] = result_data

            await self._emit("stage.completed", {
                "stage_id": stage_id,
                "duration_ms": duration,
                "batch_index": batch_index,
            })

            return StageResult(
                stage_id=stage_id,
                success=True,
                data=result_data if isinstance(result_data, dict) else {"result": result_data},
                duration_ms=duration,
                batch_index=batch_index,
            )

        except asyncio.TimeoutError:
            duration = (datetime.now() - start).total_seconds() * 1000
            error_msg = f"Stage '{stage_id}' timed out after {stage.timeout_seconds}s"
            logger.error(error_msg)

            await self._emit("stage.failed", {
                "stage_id": stage_id,
                "error": error_msg,
                "duration_ms": duration,
            })

            return StageResult(
                stage_id=stage_id,
                success=False,
                data={},
                duration_ms=duration,
                error=error_msg,
                batch_index=batch_index,
            )

        except Exception as e:
            duration = (datetime.now() - start).total_seconds() * 1000
            error_msg = f"Stage '{stage_id}' failed: {str(e)}"
            logger.exception(error_msg)

            await self._emit("stage.failed", {
                "stage_id": stage_id,
                "error": error_msg,
                "duration_ms": duration,
            })

            return StageResult(
                stage_id=stage_id,
                success=False,
                data={},
                duration_ms=duration,
                error=error_msg,
                batch_index=batch_index,
            )

    async def _emit(self, event_type: str, payload: dict[str, Any]) -> None:
        """Emit pipeline event through callback if configured."""
        if self._on_event:
            try:
                await self._on_event(event_type, payload)
            except Exception as e:
                logger.debug(f"Event emission failed: {e}")

    def get_execution_plan(self) -> dict[str, Any]:
        """Return a human-readable execution plan without running anything."""
        batches = self.topological_batches()
        return {
            "total_stages": len(self.stages),
            "total_batches": len(batches),
            "batches": [
                {
                    "batch_index": i,
                    "parallel_stages": [
                        {
                            "stage_id": sid,
                            "description": self.stages[sid].description,
                            "dependencies": self.stages[sid].dependencies,
                        }
                        for sid in batch
                    ],
                }
                for i, batch in enumerate(batches)
            ],
        }
