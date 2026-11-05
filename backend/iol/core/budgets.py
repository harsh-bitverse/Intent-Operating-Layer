"""
Execution Budgets, Safety Constraints, and Cancellation Token Tracker.
Prevents infinite loops, runaway API costs, and handles graceful cancellation.
"""

import time
from typing import Callable, Optional
from backend.iol.core.models import ExecutionBudget


class BudgetExceededError(Exception):
    """Raised when an execution exceeds duration, step, or cost budgets."""
    pass


class TaskCancelledError(Exception):
    """Raised when a task cancellation is detected during execution."""
    pass


class BudgetTracker:
    """Tracks execution consumption against the task's budget."""

    def __init__(self, budget: ExecutionBudget, is_cancelled_callback: Optional[Callable[[], bool]] = None):
        self.budget = budget
        self.is_cancelled_callback = is_cancelled_callback
        self.start_time: float = time.time()
        self.steps_executed: int = 0
        self.accumulated_cost_usd: float = 0.0

    @property
    def elapsed_seconds(self) -> float:
        return time.time() - self.start_time

    def check_constraints(self) -> None:
        """Verify that the execution has not breached limits or been cancelled."""
        if self.is_cancelled_callback and self.is_cancelled_callback():
            raise TaskCancelledError("Task was cancelled by operator or system request.")

        if self.elapsed_seconds > self.budget.max_duration_seconds:
            raise BudgetExceededError(
                f"Execution duration ({self.elapsed_seconds:.1f}s) exceeded limit of {self.budget.max_duration_seconds}s."
            )

        if self.steps_executed >= self.budget.max_steps:
            raise BudgetExceededError(
                f"Execution steps ({self.steps_executed}) reached maximum allowance of {self.budget.max_steps} steps."
            )

        if self.accumulated_cost_usd > self.budget.max_cost_usd:
            raise BudgetExceededError(
                f"Accumulated spend (${self.accumulated_cost_usd:.3f}) exceeded budget of ${self.budget.max_cost_usd:.2f}."
            )

    def record_step(self, step_cost_usd: float = 0.0) -> None:
        """Record the completion of a capability step and its cost."""
        self.steps_executed += 1
        self.accumulated_cost_usd += step_cost_usd
        if self.steps_executed > self.budget.max_steps:
            raise BudgetExceededError(
                f"Execution steps ({self.steps_executed}) exceeded maximum allowance of {self.budget.max_steps} steps."
            )
        if self.accumulated_cost_usd > self.budget.max_cost_usd:
            raise BudgetExceededError(
                f"Accumulated spend (${self.accumulated_cost_usd:.3f}) exceeded budget of ${self.budget.max_cost_usd:.2f}."
            )
