"""
Rules Engine for EDMC VKB Connector.

Implements the rule schema with:
- Signal-based conditions (no raw flags/fields in rules)
- Edge-triggered evaluation
- Array-based action lists
- Catalog-driven validation
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from . import plugin_logger
from .signal_derivation import SignalDerivation
from .signals_catalog import SignalsCatalog, generate_id_from_title

logger = plugin_logger(__name__)


class RuleValidationError(Exception):
    """Raised when a rule fails validation."""
    pass


class RuleMatchResult(str, Enum):
    """Result of evaluating a rule."""
    MATCH = "match"
    NO_MATCH = "no_match"


@dataclass
class MatchResult:
    """Result of evaluating a rule against current state."""
    rule_id: str
    rule_title: str
    matched: bool
    prev_matched: Optional[bool]
    actions_to_execute: List[Dict[str, Any]]


class RuleValidator:
    """
    Validates rules against the catalog.
    """
    
    def __init__(self, catalog: SignalsCatalog) -> None:
        self.catalog = catalog
    
    def validate_rule(self, rule: Dict[str, Any], rule_index: int) -> None:
        """
        Validate a single rule.
        
        Args:
            rule: Rule dict
            rule_index: Rule position in list (for error messages)
            
        Raises:
            RuleValidationError: If rule is invalid
        """
        # Validate title (required)
        if "title" not in rule:
            raise RuleValidationError(f"Rule at index {rule_index}: 'title' is required")
        
        title = rule.get("title")
        if not isinstance(title, str) or not title.strip():
            raise RuleValidationError(
                f"Rule at index {rule_index}: 'title' must be a non-empty string"
            )
        
        # Validate when clause
        when = rule.get("when")
        if when is not None:
            if not isinstance(when, dict):
                raise RuleValidationError(
                    f"Rule '{title}': 'when' must be a dictionary"
                )
            self._validate_when_clause(title, when)
        
        # Validate then/else actions
        for action_key in ["then", "else"]:
            actions = rule.get(action_key)
            if actions is not None:
                if not isinstance(actions, list):
                    raise RuleValidationError(
                        f"Rule '{title}': '{action_key}' must be a list of actions"
                    )
                self._validate_actions(title, actions, action_key)
    
    def _validate_when_clause(self, title: str, when: Dict[str, Any]) -> None:
        """Validate when clause structure and conditions."""
        # Validate all/any blocks
        for block_type in ["all", "any"]:
            block = when.get(block_type)
            if block is not None:
                if not isinstance(block, list):
                    raise RuleValidationError(
                        f"Rule '{title}': when.{block_type} must be a list"
                    )
                for i, condition in enumerate(block):
                    self._validate_condition(title, condition, f"{block_type}[{i}]")
    
    def _validate_condition(
        self,
        title: str,
        condition: Dict[str, Any],
        path: str
    ) -> None:
        """
        Validate a single condition.
        
        Args:
            title: Rule title
            condition: Condition dict { signal, op, value }
            path: Path for error messages
        """
        if not isinstance(condition, dict):
            raise RuleValidationError(
                f"Rule '{title}': condition at {path} must be a dictionary"
            )
        
        # Validate signal exists
        signal = condition.get("signal")
        if not signal:
            raise RuleValidationError(
                f"Rule '{title}': condition at {path} missing 'signal'"
            )
        
        if not self.catalog.signal_exists(signal):
            raise RuleValidationError(
                f"Rule '{title}': unknown signal '{signal}' at {path}"
            )
        
        # Validate operator exists
        op = condition.get("op")
        if not op:
            raise RuleValidationError(
                f"Rule '{title}': condition at {path} missing 'op'"
            )
        
        if not self.catalog.operator_exists(op):
            raise RuleValidationError(
                f"Rule '{title}': unknown operator '{op}' at {path}"
            )
        
        # Validate value based on operator
        self._validate_condition_value(title, signal, op, condition, path)
    
    def _validate_condition_value(
        self,
        title: str,
        signal: str,
        op: str,
        condition: Dict[str, Any],
        path: str
    ) -> None:
        """Validate condition value based on signal type and operator."""
        value = condition.get("value")
        signal_type = self.catalog.get_signal_type(signal)
        
        # Operators that require a value
        value_required_ops = ["eq", "ne", "in", "nin", "lt", "lte", "gt", "gte", "contains"]
        
        if op in value_required_ops:
            if value is None:
                raise RuleValidationError(
                    f"Rule '{title}': condition at {path} with op '{op}' requires 'value'"
                )
            
            # Validate value type based on signal type
            if signal_type == "bool":
                if op in ["eq", "ne"]:
                    if not isinstance(value, bool):
                        raise RuleValidationError(
                            f"Rule '{title}': bool signal '{signal}' at {path} "
                            f"requires boolean value, got {type(value).__name__}"
                        )
                else:
                    raise RuleValidationError(
                        f"Rule '{title}': bool signal '{signal}' at {path} "
                        f"only supports 'eq' or 'ne' operators, not '{op}'"
                    )
            
            elif signal_type == "enum":
                allowed_values = self.catalog.get_signal_values(signal)
                
                if op in ["eq", "ne"]:
                    if not isinstance(value, str):
                        raise RuleValidationError(
                            f"Rule '{title}': enum signal '{signal}' at {path} "
                            f"requires string value, got {type(value).__name__}"
                        )
                    if value not in allowed_values:
                        raise RuleValidationError(
                            f"Rule '{title}': invalid value '{value}' for signal '{signal}' "
                            f"at {path}. Allowed: {allowed_values}"
                        )
                
                elif op in ["in", "nin"]:
                    if not isinstance(value, list):
                        raise RuleValidationError(
                            f"Rule '{title}': op '{op}' at {path} requires list value"
                        )
                    for v in value:
                        if not isinstance(v, str):
                            raise RuleValidationError(
                                f"Rule '{title}': enum signal '{signal}' at {path} "
                                f"requires string values in list"
                            )
                        if v not in allowed_values:
                            raise RuleValidationError(
                                f"Rule '{title}': invalid value '{v}' in list for signal "
                                f"'{signal}' at {path}. Allowed: {allowed_values}"
                            )
    
    def _validate_actions(
        self,
        title: str,
        actions: List[Dict[str, Any]],
        action_type: str
    ) -> None:
        """Validate action list."""
        for i, action in enumerate(actions):
            if not isinstance(action, dict):
                raise RuleValidationError(
                    f"Rule '{title}': {action_type}[{i}] must be a dictionary"
                )
            # Basic action validation - could be expanded
            # For now, just check it's a dict with at least one key
            if not action:
                raise RuleValidationError(
                    f"Rule '{title}': {action_type}[{i}] is empty"
                )


class RuleEngine:
    """
     Rules Engine with signal-based evaluation and edge triggering.
    """
    
    def __init__(
        self,
        rules: List[Dict[str, Any]],
        catalog: SignalsCatalog,
        *,
        action_handler: Callable[[MatchResult], None],
    ) -> None:
        """
        Initialize rules engine.
        
        Args:
            rules: List of rule dicts
            catalog: Signals catalog
            action_handler: Callback for handling matched rules
        """
        self.catalog = catalog
        self.action_handler = action_handler
        self.signal_derivation = SignalDerivation(catalog._data)
        
        # Validate and normalize rules
        validator = RuleValidator(catalog)
        self.rules = []
        self.skipped_rules = []  # Track rules that failed validation
        used_ids: Set[str] = set()
        
        for i, rule in enumerate(rules):
            try:
                validator.validate_rule(rule, i)
                normalized = self._normalize_rule(rule, used_ids)
                self.rules.append(normalized)
            except RuleValidationError as e:
                logger.error(f"Rule validation failed: {e}")
                # Track skipped rule
                rule_title = rule.get("title", f"<rule at index {i}>")
                self.skipped_rules.append((i, rule_title, str(e)))
                # Skip invalid rules but continue loading others
        
        # Track previous match state for edge triggering
        # Key: (commander, is_beta, rule_id)
        self._prev_match_state: Dict[Tuple[str, bool, str], bool] = {}
    
    def _normalize_rule(self, rule: Dict[str, Any], used_ids: Set[str]) -> Dict[str, Any]:
        """
        Normalize a rule to standard format.
        
        - Generate ID if missing (using human-readable slugs)
        - Set default values for optional fields
        - Ensure consistent structure
        """
        normalized = dict(rule)
        
        # Generate ID from title if missing
        if "id" not in normalized or not normalized["id"]:
            title = normalized["title"]
            normalized["id"] = generate_id_from_title(title, used_ids)
        else:
            # User provided ID - add to used set
            used_ids.add(normalized["id"])
        
        # Set defaults
        if "enabled" not in normalized:
            normalized["enabled"] = True
        
        if "when" not in normalized:
            normalized["when"] = {"all": []}
        
        if "then" not in normalized:
            normalized["then"] = []
        
        if "else" not in normalized:
            normalized["else"] = []
        
        return normalized
    
    def on_notification(
        self,
        cmdr: str,
        is_beta: bool,
        source: str,
        event_type: str,
        entry: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Process a notification and evaluate all rules.
        
        Args:
            cmdr: Commander name
            is_beta: Beta flag
            source: Source (dashboard, journal, etc.)
            event_type: Event type
            entry: Raw event data
            context: Additional context (recent_events, trigger_source, etc.)
        """
        if context is None:
            context = {}
        
        # Enrich payload with notification metadata so catalog signals can
        # target source/event uniformly across journal, dashboard, and CAPI.
        enriched_entry = dict(entry)
        enriched_entry.setdefault("event", event_type)
        enriched_entry["__edmc_source"] = source
        enriched_entry["__edmc_event_type"] = event_type

        # Derive all signals from entry (pass context for recent operator)
        signals = self.signal_derivation.derive_all_signals(enriched_entry, context)
        
        # Evaluate each rule
        for rule in self.rules:
            if not rule.get("enabled", True):
                continue
            
            try:
                result = self._evaluate_rule(cmdr, is_beta, rule, signals)
                if result:
                    self.action_handler(result)
            except Exception as e:
                rule_id = rule.get("id", "<unknown>")
                logger.error(f"Error evaluating rule '{rule_id}': {e}")
    
    def _evaluate_rule(
        self,
        cmdr: str,
        is_beta: bool,
        rule: Dict[str, Any],
        signals: Dict[str, Any]
    ) -> Optional[MatchResult]:
        """
        Evaluate a single rule with edge triggering.
        
        Args:
            cmdr: Commander name
            is_beta: Beta flag
            rule: Normalized rule dict
            signals: Derived signal values
            
        Returns:
            Match result with actions to execute, or None if no state change
        """
        rule_id = rule["id"]
        rule_title = rule["title"]
        
        # Check current match state
        current_matched = self._check_rule_conditions(rule, signals)
        
        # Get previous match state
        state_key = (cmdr, is_beta, rule_id)
        prev_matched = self._prev_match_state.get(state_key)
        
        # Update state
        self._prev_match_state[state_key] = current_matched
        
        # Edge triggering: only execute actions on state transitions
        actions_to_execute = []
        
        if prev_matched is False and current_matched:
            # Transition: false -> true, execute 'then'
            actions_to_execute = rule.get("then", [])
        elif prev_matched is True and not current_matched:
            # Transition: true -> false, execute 'else'
            actions_to_execute = rule.get("else", [])
        elif prev_matched is None:
            # First evaluation
            if current_matched:
                actions_to_execute = rule.get("then", [])
            else:
                actions_to_execute = rule.get("else", [])
        
        # Only return result if there are actions to execute
        if actions_to_execute:
            return MatchResult(
                rule_id=rule_id,
                rule_title=rule_title,
                matched=current_matched,
                prev_matched=prev_matched,
                actions_to_execute=actions_to_execute,
            )
        
        return None
    
    def _check_rule_conditions(
        self,
        rule: Dict[str, Any],
        signals: Dict[str, Any]
    ) -> bool:
        """
        Check if rule conditions match current signals.
        
        Implements (ALL) AND (ANY) logic:
        - If all present: all conditions in 'all' AND at least one in 'any'
        - If only 'all': all conditions must match
        - If only 'any': at least one condition must match
        - If neither: matches (empty condition = always true)
        """
        when = rule.get("when", {})
        all_conditions = when.get("all", [])
        any_conditions = when.get("any", [])
        
        # Check 'all' conditions
        if all_conditions:
            for condition in all_conditions:
                if not self._check_condition(condition, signals):
                    return False
        
        # Check 'any' conditions
        if any_conditions:
            any_matched = False
            for condition in any_conditions:
                if self._check_condition(condition, signals):
                    any_matched = True
                    break
            if not any_matched:
                return False
        
        # If we get here, all checks passed
        return True
    
    def _check_condition(
        self,
        condition: Dict[str, Any],
        signals: Dict[str, Any]
    ) -> bool:
        """
        Check if a single condition matches.
        
        Args:
            condition: Condition dict { signal, op, value }
            signals: Current signal values
            
        Returns:
            True if condition matches
        """
        signal = condition["signal"]
        op = condition["op"]
        value = condition.get("value")
        
        # Get current signal value
        signal_value = signals.get(signal)
        
        # Apply operator
        if op == "eq":
            return signal_value == value
        elif op == "ne":
            return signal_value != value
        elif op == "in":
            return signal_value in value
        elif op == "nin":
            return signal_value not in value
        elif op == "lt":
            return signal_value < value
        elif op == "lte":
            return signal_value <= value
        elif op == "gt":
            return signal_value > value
        elif op == "gte":
            return signal_value >= value
        elif op == "contains":
            if isinstance(signal_value, (list, str)):
                return value in signal_value
            return False
        elif op == "exists":
            # Signal always exists in our derived signals dict
            return True
        else:
            logger.warning(f"Unknown operator: {op}")
            return False

