from enum import StrEnum
from typing import Any, NotRequired, Optional, Self, TypedDict

from grafana_foundation_sdk.cog import builder
from grafana_foundation_sdk.cog import runtime as cogruntime
from grafana_foundation_sdk.cog import variants as cogvariants


class QueryFormat(StrEnum):
    TABLE = "table"
    TIMESERIES = "timeseries"
    LOGS = "logs"
    TRACE = "trace"
    NODE_GRAPH_NODES = "node-graph-nodes"
    NODE_GRAPH_EDGES = "node-graph-edges"
    DATAFRAME = "dataframe"
    AS_IS = "as-is"


class ParserType(StrEnum):
    SIMPLE = "simple"
    BACKEND = "backend"
    JQ_BACKEND = "jq-backend"
    UQL = "uql"
    GROQ = "groq"


class ColumnFormat(StrEnum):
    STRING = "string"
    NUMBER = "number"
    TIMESTAMP = "timestamp"
    TIMESTAMP_EPOCH = "timestamp_epoch"
    TIMESTAMP_EPOCH_S = "timestamp_epoch_s"
    BOOLEAN = "boolean"


class QuerySources(StrEnum):
    URL = "url"
    INLINE = "inline"
    AZURE_BLOB = "azure-blob"
    REFERENCE = "reference"
    RANDOM_WALK = "random-walk"
    EXPRESSION = "expression"


class QueryType(StrEnum):
    JSON = "json"
    GRAPHQL = "graphql"
    CSV = "csv"
    TSV = "tsv"
    XML = "xml"
    HTML = "html"
    UQL = "uql"
    GROQ = "groq"
    GLOBAL = "global"
    GOOGLE_SHEETS = "google-sheets"
    TRANSFORMATIONS = "transformations"
    SERIES = "series"


class Column(TypedDict):
    selector: str
    text: str
    type: ColumnFormat
    timestampFormat: NotRequired[str]


class InfinityQuery(cogvariants.Dataquery):
    # ref_id and hide are expected on all queries
    ref_id: Optional[str]
    hide: Optional[bool]

    parser: ParserType = ParserType.SIMPLE
    source: QuerySources = QuerySources.URL
    type: QueryType = QueryType.JSON
    format: QueryFormat = QueryFormat.TABLE
    columns: list[Column]
    additional_fields: dict

    def __init__(
        self,
        ref_id: Optional[str] = None,
        hide: Optional[bool] = None,
    ):
        self.ref_id = ref_id
        self.hide = hide
        self.columns = []
        self.additional_fields = {}

    def to_json(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "parser": self.parser,
            "source": self.source,
            "format": self.format,
            "type": self.type,
            "columns": self.columns,
        }
        payload.update(self.additional_fields)
        if self.ref_id is not None:
            payload["refId"] = self.ref_id
        if self.hide is not None:
            payload["hide"] = self.hide
        return payload

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> Self:
        args: dict[str, Any] = {}

        possible_fields = ["parser", "columns", "source", "format", "url", "type"]
        for pf in possible_fields:
            if pf in data:
                args[pf] = data[pf]
        if "refId" in data:
            args["ref_id"] = data["refId"]
        if "hide" in data:
            args["hide"] = data["hide"]

        return cls(**args)


def custom_query_variant_config() -> cogruntime.DataqueryConfig:
    return cogruntime.DataqueryConfig(
        # datasource plugin ID
        identifier="custom-query",
        from_json_hook=InfinityQuery.from_json,
    )


class InfinityQueryBuilder(builder.Builder[InfinityQuery]):
    __internal: InfinityQuery

    def __init__(
        self,
    ):
        self.__internal = InfinityQuery()

    def with_parser(self, parser: ParserType):
        self.__internal.parser = parser
        return self

    def with_url(self, url: str, method: str):
        self.__internal.additional_fields["url"] = url
        self.__internal.additional_fields["url_options"] = {"method": method}
        return self

    def with_columns(self, columns: list[Column]):
        self.__internal.columns = columns
        return self

    def with_format(self, format: QueryFormat):
        self.__internal.format = format
        return self

    def build(self) -> InfinityQuery:
        return self.__internal

    def ref_id(self, ref_id: str) -> Self:
        self.__internal.ref_id = ref_id

        return self

    def hide(self, hide: bool) -> Self:
        self.__internal.hide = hide

        return self
