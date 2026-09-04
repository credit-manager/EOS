"""
DYNAMIC QUERY PARSER
====================
Parses and validates filter/sort parameters for Dynamic CRUD.

Security chain:
  Request → Parse → Column Allowlist → Operator Allowlist →
  Type Validation → Tenant Scope → Parameterized SQL

NEVER allows raw user input in SQL.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any


class Operator(str, Enum):
    """Supported filter operators."""
    EQ = "eq"
    NEQ = "neq"
    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"
    LIKE = "like"
    IN = "in"
    IS_NULL = "is_null"
    IS_NOT_NULL = "is_not_null"


# Operator to SQL mapping (parameterized)
OPERATOR_SQL = {
    Operator.EQ: "{col} = :{param}",
    Operator.NEQ: "{col} != :{param}",
    Operator.GT: "{col} > :{param}",
    Operator.GTE: "{col} >= :{param}",
    Operator.LT: "{col} < :{param}",
    Operator.LTE: "{col} <= :{param}",
    Operator.LIKE: "{col} ILIKE :{param}",
    Operator.IN: "{col} IN :{param}",
    Operator.IS_NULL: "{col} IS NULL",
    Operator.IS_NOT_NULL: "{col} IS NOT NULL",
}

# Operators that don't need a value
NO_VALUE_OPERATORS = {Operator.IS_NULL, Operator.IS_NOT_NULL}

# Operators that accept multiple values (IN)
MULTI_VALUE_OPERATORS = {Operator.IN}


@dataclass
class FilterClause:
    """A single validated filter clause."""
    column: str           # Actual column name (validated)
    operator: Operator    # Validated operator
    value: Any = None     # Validated value
    param_name: str = ""  # Unique parameter name for SQL


@dataclass
class SortClause:
    """A single validated sort clause."""
    column: str           # Actual column name (validated)
    descending: bool      # True = DESC, False = ASC


@dataclass
class QueryFilter:
    """Parsed and validated query filters."""
    filters: list[FilterClause]
    sorts: list[SortClause]
    limit: int
    offset: int


class QueryParseError(Exception):
    """Raised when query parameters are invalid."""


class QueryParser:
    """
    Parses and validates query parameters.
    
    Security:
      - Column names validated against real_columns
      - Operators validated against allowlist
      - Values validated against type rules
      - All SQL is parameterized
    """
    
    # Configuration
    MAX_LIMIT = 500
    DEFAULT_LIMIT = 100
    MAX_OFFSET = 100000
    
    # Column names that are NEVER allowed in user filters
    BLOCKED_COLUMNS = {"id"}  # id is managed by system
    
    def __init__(self, real_columns: dict[str, str]):
        """
        Initialize parser with valid columns.
        
        Args:
            real_columns: {lowercase_name: actual_name} from DynamicVerificationEngine
        """
        # Build allowlist: lowercase -> actual name
        self.column_allowlist = {
            k.lower(): v for k, v in real_columns.items()
        }
    
    def _validate_column(self, column: str) -> str:
        """
        Validate column name against allowlist.
        
        Returns actual column name if valid.
        Raises QueryParseError if invalid.
        """
        if not column:
            raise QueryParseError("Column name is empty")
        
        col_lower = column.lower().strip()
        
        # Check blocked columns
        if col_lower in self.BLOCKED_COLUMNS:
            raise QueryParseError(f"Column '{column}' is not filterable")
        
        # Check allowlist
        if col_lower not in self.column_allowlist:
            raise QueryParseError(f"Invalid column: '{column}'")
        
        return self.column_allowlist[col_lower]
    
    def _validate_operator(self, op: str) -> Operator:
        """
        Validate operator against allowlist.
        
        Returns Operator enum if valid.
        Raises QueryParseError if invalid.
        """
        if not op:
            raise QueryParseError("Operator is empty")
        
        op_lower = op.lower().strip()
        
        try:
            return Operator(op_lower)
        except ValueError:
            valid_ops = ", ".join(o.value for o in Operator)
            raise QueryParseError(
                f"Invalid operator: '{op}'. Valid operators: {valid_ops}"
            )
    
    def _parse_value(self, value_str: str, operator: Operator) -> Any:
        """
        Parse and validate value based on operator.
        
        Returns parsed value.
        Raises QueryParseError if invalid.
        """
        if operator in NO_VALUE_OPERATORS:
            return None
        
        if not value_str:
            raise QueryParseError(
                f"Operator '{operator.value}' requires a value"
            )
        
        if operator == Operator.IN:
            # Parse pipe-separated values (not comma, which is filter separator)
            values = [v.strip() for v in value_str.split("|") if v.strip()]
            if not values:
                raise QueryParseError("IN operator requires at least one value")
            return tuple(values)
        
        if operator == Operator.LIKE:
            # LIKE value - basic sanitization
            # Remove SQL wildcards that aren't %
            sanitized = value_str.replace("'", "").replace(";", "")
            return f"%{sanitized}%"
        
        # For comparison operators, try to parse as number
        try:
            if "." in value_str:
                return float(value_str)
            return int(value_str)
        except ValueError:
            # Return as string if not a number
            return value_str
    
    def parse_filter(self, filter_str: str) -> FilterClause:
        """
        Parse a single filter string.
        
        Format: column:operator:value
        
        Examples:
          status:eq:active
          price:gte:100
          name:like:ahmed
          deleted_at:is_null
        """
        parts = filter_str.split(":", 2)
        
        if len(parts) < 2:
            raise QueryParseError(
                f"Invalid filter format: '{filter_str}'. "
                f"Expected: column:operator:value"
            )
        
        column = parts[0].strip()
        operator_str = parts[1].strip()
        value_str = parts[2].strip() if len(parts) > 2 else ""
        
        # Validate
        actual_column = self._validate_column(column)
        operator = self._validate_operator(operator_str)
        value = self._parse_value(value_str, operator)
        
        # Generate unique param name
        param_name = f"f_{column}_{operator.value}"
        
        return FilterClause(
            column=actual_column,
            operator=operator,
            value=value,
            param_name=param_name
        )
    
    def parse_filters(self, filters_str: str) -> list[FilterClause]:
        """
        Parse multiple filters from comma-separated string.
        
        Format: filter1,filter2,filter3
        
        Example: status:eq:active,price:gte:100,name:like:ahmed
        """
        if not filters_str or not filters_str.strip():
            return []
        
        filters = []
        for part in filters_str.split(","):
            part = part.strip()
            if part:
                filters.append(self.parse_filter(part))
        
        return filters
    
    def parse_sort(self, sort_str: str) -> list[SortClause]:
        """
        Parse sort string.
        
        Format: -column1,column2,column3
        
        - prefix = DESC
        No prefix = ASC
        
        Example: -created_at,name
        """
        if not sort_str or not sort_str.strip():
            return []
        
        sorts = []
        for part in sort_str.split(","):
            part = part.strip()
            if not part:
                continue
            
            descending = False
            col_name = part
            
            if part.startswith("-"):
                descending = True
                col_name = part[1:]
            
            actual_column = self._validate_column(col_name)
            
            sorts.append(SortClause(
                column=actual_column,
                descending=descending
            ))
        
        return sorts
    
    def parse_pagination(
        self,
        limit: int | None = None,
        offset: int | None = None
    ) -> tuple[int, int]:
        """
        Parse and validate pagination parameters.
        
        Returns (limit, offset) tuple.
        """
        # Validate limit
        if limit is None:
            limit = self.DEFAULT_LIMIT
        
        limit = max(1, min(limit, self.MAX_LIMIT))
        
        # Validate offset
        if offset is None:
            offset = 0
        
        offset = max(0, min(offset, self.MAX_OFFSET))
        
        return limit, offset
    
    def parse_query(
        self,
        filters_str: str | None = None,
        sort_str: str | None = None,
        limit: int | None = None,
        offset: int | None = None
    ) -> QueryFilter:
        """
        Parse all query parameters.
        
        Returns validated QueryFilter.
        """
        filters = self.parse_filters(filters_str)
        sorts = self.parse_sort(sort_str)
        limit, offset = self.parse_pagination(limit, offset)
        
        return QueryFilter(
            filters=filters,
            sorts=sorts,
            limit=limit,
            offset=offset
        )
    
    @staticmethod
    def build_where_clause(
        filters: list[FilterClause]
    ) -> tuple[str, dict[str, Any]]:
        """
        Build SQL WHERE clause from filters.
        
        Returns (where_sql, params_dict).
        """
        if not filters:
            return "", {}
        
        conditions = []
        params = {}
        
        for f in filters:
            if f.operator in NO_VALUE_OPERATORS:
                # IS NULL / IS NOT NULL - no parameter needed
                conditions.append(
                    OPERATOR_SQL[f.operator].format(col=f.column)
                )
            elif f.operator == Operator.IN:
                # IN - parameter is a tuple
                sql = OPERATOR_SQL[f.operator].format(
                    col=f.column, param=f.param_name
                )
                conditions.append(sql)
                params[f.param_name] = f.value
            else:
                # Standard comparison
                sql = OPERATOR_SQL[f.operator].format(
                    col=f.column, param=f.param_name
                )
                conditions.append(sql)
                params[f.param_name] = f.value
        
        where_sql = " AND ".join(conditions)
        return where_sql, params
    
    @staticmethod
    def build_order_clause(sorts: list[SortClause]) -> str:
        """
        Build SQL ORDER BY clause from sorts.
        
        Returns order_sql (no parameters needed - columns already validated).
        """
        if not sorts:
            return ""
        
        parts = []
        for s in sorts:
            direction = "DESC" if s.descending else "ASC"
            parts.append(f"{s.column} {direction}")
        
        return "ORDER BY " + ", ".join(parts)
