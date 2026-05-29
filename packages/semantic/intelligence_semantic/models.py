from pydantic import BaseModel, Field


class Dimension(BaseModel):
    """A dimension represents a categorical field or a time component."""

    name: str = Field(..., description="Unique name of the dimension")
    type: str = Field(
        ..., description="Data type of the dimension (e.g., string, datetime, boolean)"
    )
    description: str | None = Field(None, description="Human-readable description")
    expr: str | None = Field(None, description="SQL expression if this is a derived dimension")


class Metric(BaseModel):
    """A metric represents a quantitative measurement."""

    name: str = Field(..., description="Unique name of the metric")
    description: str | None = Field(None, description="Human-readable description")
    sql: str = Field(..., description="SQL expression for the metric (e.g., SUM(revenue))")
    type: str = Field(
        ..., description="Data type or classification (e.g., number, currency, percent)"
    )
    dimensions: list[str] = Field(
        default_factory=list,
        description="List of dimension names that can be used to slice this metric",
    )


class SemanticModel(BaseModel):
    """
    A semantic model groups related metrics and dimensions, typically bound to a table or view.
    """

    name: str = Field(..., description="Name of the semantic model (e.g., users, transactions)")
    description: str | None = Field(None, description="Human-readable description of the model")
    table: str = Field(..., description="The underlying database table or view")
    metrics: list[Metric] = Field(
        default_factory=list, description="Metrics available in this model"
    )
    dimensions: list[Dimension] = Field(
        default_factory=list, description="Dimensions available in this model"
    )
