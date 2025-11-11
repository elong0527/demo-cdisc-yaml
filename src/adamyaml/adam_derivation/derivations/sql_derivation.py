"""SQL-based derivation handling most CDISC patterns."""

import logging
from typing import Any

import polars as pl

from .base import BaseDerivation

logger = logging.getLogger(__name__)


class SQLDerivation(BaseDerivation):
    """
    Handles derivations using SQL expressions.
    Covers: constant, source, mapping, aggregation, cut patterns.
    """

    def derive(self) -> pl.Series:
        """Derive column using SQL expression."""

        derivation = self.col_spec.get("derivation", {})
        col_name = self.col_spec["name"]
        key_vars = self.col_spec.get("_key_vars", ["USUBJID"])

        # Dispatch to appropriate SQL generator
        if "constant" in derivation:
            return self._derive_constant(derivation["constant"])
        elif "source" in derivation:
            return self._derive_source(derivation, key_vars)
        elif "cut" in derivation:
            return self._derive_cut(derivation)
        else:
            raise ValueError(f"Unknown derivation type for {col_name}")

    def _derive_constant(self, value: Any) -> pl.Series:
        """Create a constant value column."""
        return pl.Series([value] * self.target_df.height)

    def _derive_source(self, derivation: dict[str, Any], key_vars: list[str]) -> pl.Series:
        """Derive from source with optional mapping, filter, and aggregation."""

        source = derivation["source"]

        # Parse source reference (e.g., "DM.AGE" or "AGE")
        if "." in source:
            dataset_name, column_name = source.split(".", 1)
            source_col = f"{dataset_name}.{column_name}"
        else:
            # Column from target dataset
            if source in self.target_df.columns:
                series = self.target_df[source]
            else:
                raise ValueError(f"Column {source} not found in target dataset")

            # Apply mapping if present
            if "mapping" in derivation:
                return self._apply_mapping(series, derivation["mapping"])
            return series

        # Build SQL query

        # Handle aggregation
        if "aggregation" in derivation:
            agg_spec = derivation["aggregation"]
            sql_query = self._build_aggregation_sql(
                source_col, agg_spec, derivation.get("filter"), key_vars
            )
        else:
            # Simple source with optional filter
            sql_query = self._build_source_sql(
                source_col, derivation.get("filter"), derivation.get("mapping"), key_vars
            )

        # Execute SQL using Polars SQL context
        return self._execute_sql(sql_query, key_vars)

    def _derive_cut(self, derivation: dict[str, Any]) -> pl.Series:
        """Derive using cut (categorization) logic."""

        source = derivation["source"]
        cuts = derivation["cut"]

        # Get source column
        if source in self.target_df.columns:
            self.target_df[source]
        else:
            raise ValueError(f"Source column {source} not found for cut")

        # Build CASE expression
        case_parts = []
        for condition, label in cuts.items():
            # Convert condition syntax to SQL
            sql_condition = condition.replace("and", "AND").replace("or", "OR")
            sql_condition = sql_condition.replace(">=", "___GTE___")
            sql_condition = sql_condition.replace("<=", "___LTE___")
            sql_condition = sql_condition.replace(">", "___GT___")
            sql_condition = sql_condition.replace("<", "___LT___")
            sql_condition = sql_condition.replace("=", "___EQ___")

            # Now replace back with source reference
            sql_condition = sql_condition.replace("___GTE___", f">= {source} AND {source} >=")
            sql_condition = sql_condition.replace("___LTE___", f"<= {source} AND {source} <=")
            sql_condition = sql_condition.replace("___GT___", f"> {source} AND {source} >")
            sql_condition = sql_condition.replace("___LT___", f"< {source} AND {source} <")
            sql_condition = sql_condition.replace("___EQ___", f"= {source} AND {source} =")

            # Clean up the condition
            # For patterns like "<18", ">=18 and <65", ">=65"
            if condition.startswith("<"):
                value = condition[1:].strip()
                case_parts.append(f"WHEN {source} < {value} THEN '{label}'")
            elif condition.startswith(">=") and " and " in condition.lower():
                parts = condition.split(" and ")
                lower = parts[0].replace(">=", "").strip()
                upper = parts[1].replace("<", "").strip()
                case_parts.append(f"WHEN {source} >= {lower} AND {source} < {upper} THEN '{label}'")
            elif condition.startswith(">="):
                value = condition[2:].strip()
                case_parts.append(f"WHEN {source} >= {value} THEN '{label}'")
            else:
                # Generic condition
                case_parts.append(f"WHEN {condition} THEN '{label}'")

        case_expr = "CASE " + " ".join(case_parts) + " ELSE NULL END"

        # Execute using Polars expressions
        ctx = pl.SQLContext(frame=self.target_df)
        result_df = ctx.execute(f"SELECT {case_expr} as result FROM frame")
        return result_df["result"]

    def _build_source_sql(
        self,
        source_col: str,
        filter_expr: str | None,
        mapping: dict[str, str] | None,
        key_vars: list[str],
    ) -> str:
        """Build SQL for simple source derivation."""

        # Handle mapping with CASE statement
        if mapping:
            case_parts = []
            for key, value in mapping.items():
                if key == "":
                    case_parts.append(f"WHEN {source_col} = '' THEN NULL")
                elif value == "Null" or value is None:
                    case_parts.append(f"WHEN {source_col} = '{key}' THEN NULL")
                else:
                    case_parts.append(f"WHEN {source_col} = '{key}' THEN '{value}'")

            select_expr = f"CASE {' '.join(case_parts)} ELSE NULL END as result"
        else:
            select_expr = f"{source_col} as result"

        # Build complete query
        sql = f"SELECT {', '.join(key_vars)}, {select_expr} FROM merged"

        if filter_expr:
            sql += f" WHERE {filter_expr}"

        return sql

    def _build_aggregation_sql(
        self,
        source_col: str,
        agg_spec: dict[str, Any],
        filter_expr: str | None,
        key_vars: list[str],
    ) -> str:
        """Build SQL for aggregation derivation."""

        function = agg_spec.get("function", "first")

        # Map aggregation functions to SQL
        if function == "first":
            agg_expr = f"FIRST({source_col}) as result"
            order_by = ""
        elif function == "last":
            agg_expr = f"LAST({source_col}) as result"
            order_by = ""
        elif function == "mean":
            agg_expr = f"AVG(CAST({source_col} AS FLOAT)) as result"
            order_by = ""
        elif function == "sum":
            agg_expr = f"SUM(CAST({source_col} AS FLOAT)) as result"
            order_by = ""
        elif function == "max":
            agg_expr = f"MAX({source_col}) as result"
            order_by = ""
        elif function == "min":
            agg_expr = f"MIN({source_col}) as result"
            order_by = ""
        elif function == "closest":
            # For closest, we need special handling as Polars SQL doesn't support ROW_NUMBER
            # We'll handle this with native Polars operations
            target = agg_spec.get("target")
            if not target:
                raise ValueError("'closest' aggregation requires 'target' field")

            # Return a special marker to handle in execute
            return f"CLOSEST:{source_col}:{target}:{filter_expr or ''}"
        else:
            raise ValueError(f"Unknown aggregation function: {function}")

        # Build query
        sql = f"SELECT {', '.join(key_vars)}, {agg_expr} FROM merged"

        if filter_expr:
            sql += f" WHERE {filter_expr}"

        sql += f" GROUP BY {', '.join(key_vars)}"

        if order_by:
            sql += f" ORDER BY {order_by}"

        return sql

    def _execute_sql(self, sql: str, key_vars: list[str]) -> pl.Series:
        """Execute SQL query and return result as Series."""

        # Check for special CLOSEST handling
        if sql.startswith("CLOSEST:"):
            return self._execute_closest(sql, key_vars)

        # Start with target DataFrame for context
        merged_df = self.target_df.clone()

        # Add source data if needed
        for dataset_name, df in self.source_data.items():
            # Check if this dataset is referenced in the SQL
            if dataset_name in sql or f'"{dataset_name}.' in sql:
                # Get available keys for joining
                available_keys = [k for k in key_vars if k in df.columns]
                if available_keys and dataset_name not in merged_df.columns:
                    # Join the source data
                    merged_df = merged_df.join(
                        df, on=available_keys, how="left", suffix=f"_{dataset_name.lower()}"
                    )

        # Create SQL context and execute
        # Use the column names as they are (already renamed with dots)
        ctx = pl.SQLContext(merged=merged_df)

        try:
            # Execute the SQL - wrap column names with dots in quotes
            # Replace DM.COLUMN with "DM.COLUMN" for proper SQL
            import re

            sql_quoted = re.sub(r"(\w+)\.(\w+)", r'"\1.\2"', sql)

            result_df = ctx.execute(sql_quoted).collect()

            # Handle result based on size
            if len(result_df) == len(self.target_df):
                # Direct assignment
                return result_df["result"]
            elif len(result_df) < len(self.target_df) and len(key_vars) > 0:
                # Need to join to get all rows
                final_df = self.target_df.select(key_vars).join(result_df, on=key_vars, how="left")
                return final_df["result"]
            else:
                # Fallback - ensure we return right number of rows
                return pl.Series([None] * self.target_df.height)

        except Exception as e:
            logger.warning(f"SQL execution failed: {e}, returning nulls")
            logger.debug(f"SQL: {sql}")
            logger.debug(f"Available columns: {merged_df.columns}")
            return pl.Series([None] * self.target_df.height)

    def _execute_closest(self, sql_spec: str, key_vars: list[str]) -> pl.Series:
        """Execute 'closest' aggregation using native Polars operations."""

        # Parse the CLOSEST spec
        parts = sql_spec.split(":", 3)
        source_col = parts[1]  # e.g., "VS.VSORRES"
        target_col = parts[2]  # e.g., "DM.RFSTDTC"
        filter_expr = parts[3] if len(parts) > 3 else None

        # Get dataset name from source column
        dataset_name = source_col.split(".")[0]

        # Build merged DataFrame with necessary data
        merged_df = self.target_df.clone()

        # Add source data
        for ds_name, df in self.source_data.items():
            if ds_name == dataset_name or ds_name in target_col:
                available_keys = [k for k in key_vars if k in df.columns]
                if available_keys:
                    merged_df = merged_df.join(df, on=available_keys, how="left")

        # Apply filter if present
        if filter_expr:
            try:
                # Use polars expressions for filtering
                # Convert SQL-like filter to Polars expression
                import re

                # Replace column references with pl.col()
                filter_polars = filter_expr
                # Handle column references with dots
                filter_polars = re.sub(
                    r"(\w+\.\w+)", lambda m: f'pl.col("{m.group(1)}")', filter_polars
                )
                # Use & for and in Polars
                filter_polars = filter_polars.replace(" and ", " & ")
                filter_polars = filter_polars.replace(" or ", " | ")
                filter_polars = filter_polars.replace("==", "=").replace("=", "==")
                # Add parentheses around all comparisons to fix operator precedence
                filter_polars = re.sub(
                    r'(pl\.col\("[^"]+"\)\s*[<>=!]+\s*(?:"[^"]*"|pl\.col\("[^"]+"\)))',
                    r"(\1)",
                    filter_polars,
                )
                # Apply filter
                filtered_df = merged_df.filter(eval(filter_polars))
            except Exception as e:
                logger.warning(f"Filter failed: {e}, using unfiltered data")
                filtered_df = merged_df
        else:
            filtered_df = merged_df

        # Get the date column for VS dataset
        date_col = f"{dataset_name}.VSDTC" if dataset_name == "VS" else f"{dataset_name}.DTC"

        # Find closest value for each subject
        result_list = []
        for subject in self.target_df[key_vars[0]].unique():
            subject_data = filtered_df.filter(pl.col(key_vars[0]) == subject)

            if subject_data.height > 0 and source_col in subject_data.columns:
                # Calculate distance to target date
                if target_col in subject_data.columns and date_col in subject_data.columns:
                    # Get target date (should be same for all rows of this subject)
                    target_date = subject_data[target_col][0]

                    # Calculate date differences and find closest
                    # Handle partial dates by using strptime with appropriate format
                    with_diff = subject_data.with_columns(
                        (
                            pl.col(date_col).str.strptime(pl.Date, "%Y-%m-%d", strict=False)
                            - pl.lit(target_date).str.strptime(pl.Date, "%Y-%m-%d", strict=False)
                        )
                        .dt.total_days()
                        .abs()
                        .alias("date_diff")
                    )

                    # Get the row with minimum difference
                    closest_row = with_diff.filter(
                        pl.col("date_diff") == with_diff["date_diff"].min()
                    )

                    if closest_row.height > 0:
                        result_list.append(closest_row[source_col][0])
                    else:
                        result_list.append(None)
                else:
                    # No date columns, just take first value
                    result_list.append(subject_data[source_col][0])
            else:
                result_list.append(None)

        # Create result series matching target_df order
        result_dict = dict(zip(self.target_df[key_vars[0]].to_list(), result_list, strict=False))
        result = [result_dict.get(subj) for subj in self.target_df[key_vars[0]].to_list()]

        logger.info(
            f"Applied closest aggregation, {sum(v is not None for v in result)} non-null values"
        )
        return pl.Series(result)

    def _apply_mapping(self, series: pl.Series, mapping: dict[str, str]) -> pl.Series:
        """Apply value mapping to a series."""

        # Build when/then chains
        result = series
        for old_val, new_val in mapping.items():
            if new_val == "Null" or new_val is None:
                result = pl.when(result == old_val).then(None).otherwise(result)
            else:
                result = pl.when(result == old_val).then(new_val).otherwise(result)

        return result  # pyre-ignore[7]
