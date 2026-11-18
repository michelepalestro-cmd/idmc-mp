"""IMF class names and the field-type map shared by every node builder.

CLS maps the short class name used by the builders to the fully qualified Java class that IDMC expects in
``metadata.$$classInfo``. It is the union of every class the legacy generators used. A build copies it
(``imf.B.fq``), so a ``generic`` node can register extra classes without leaking into the next build.
"""

CLS = {
    "Template": "com.informatica.metadata.template.common.Template",
    "GenericAnnotation": "com.informatica.metadata.common.genericannotation.GenericAnnotation",
    "Description": "com.informatica.metadata.common.description.Description",
    "TmplLink": "com.informatica.metadata.template.common.TmplLink",
    "TmplGroup": "com.informatica.metadata.template.common.TmplGroup",
    "TmplSource": "com.informatica.metadata.template.tx.tmplsource.TmplSource",
    "TmplTarget": "com.informatica.metadata.template.tx.tmpltarget.TmplTarget",
    "TmplExpression": "com.informatica.metadata.template.tx.tmplexpression.TmplExpression",
    "TmplExpressionField": "com.informatica.metadata.template.tx.tmplexpression.TmplExpressionField",
    "TmplExpressionWindowSpec": "com.informatica.metadata.template.tx.tmplexpression.TmplExpressionWindowSpec",
    "TmplRouter": "com.informatica.metadata.template.tx.tmplrouter.TmplRouter",
    "GroupFilterCondition": "com.informatica.metadata.template.tx.tmplrouter.GroupFilterCondition",
    "TmplFilter": "com.informatica.metadata.template.tx.tmplfilter.TmplFilter",
    "TmplJoiner": "com.informatica.metadata.template.tx.tmpljoiner.TmplJoiner",
    "TmplAggregator": "com.informatica.metadata.template.tx.tmplaggregator.TmplAggregator",
    "TmplAggregatorField": "com.informatica.metadata.template.tx.tmplaggregator.TmplAggregatorField",
    "TmplAggregatorGroupByFields": "com.informatica.metadata.template.tx.tmplaggregator.TmplAggregatorGroupByFields",
    "TmplAggregatorGroupByField": "com.informatica.metadata.template.tx.tmplaggregator.TmplAggregatorGroupByField",
    "NameValuePair": "com.informatica.metadata.common.genericannotation.NameValuePair",
    "TxAdvancedProperty": "com.informatica.metadata.template.common.TxAdvancedProperty",
    "BaseAdapter": "com.informatica.metadata.template.ext.da.cloud.common.BaseAdapter",
    "TxField": "com.informatica.metadata.template.common.field.TxField",
    "BaseAdapterField": "com.informatica.metadata.template.ext.da.cloud.common.BaseAdapterField",
    "DataType": "com.informatica.metadata.common.typesystem.DataType",
    "FieldMappings": "com.informatica.metadata.template.tx.tmpltarget.FieldMappings",
    "StringValue": "com.informatica.metadata.common.types.StringValue",
    "BooleanValue": "com.informatica.metadata.common.types.BooleanValue",
    "DataObject": "com.informatica.metadata.template.ext.da.cloud.common.DataObject",
    "RuntimeAttributes": "com.informatica.metadata.template.ext.da.cloud.common.RuntimeAttributes",
    "RuntimeAttribute": "com.informatica.metadata.template.ext.da.cloud.common.RuntimeAttribute",
    "ReadOptions": "com.informatica.metadata.template.ext.da.cloud.common.ReadOptions",
    "TmplAllRule": "com.informatica.metadata.template.common.rule.TmplAllRule",
    "BulkOptions": "com.informatica.metadata.template.ext.da.cloud.common.BulkOptions",
    "WriteOptions": "com.informatica.metadata.template.ext.da.cloud.common.WriteOptions",
    "Option": "com.informatica.metadata.template.ext.da.cloud.common.Option",
    "TmplNameRule": "com.informatica.metadata.template.common.rule.TmplNameRule",
    "TmplNameRuleEntry": "com.informatica.metadata.template.common.rule.TmplNameRuleEntry",
    "JoinCondition": "com.informatica.metadata.template.tx.tmpljoiner.JoinCondition",
    "TmplSorter": "com.informatica.metadata.template.tx.tmplsorter.TmplSorter",
    "SortEntry": "com.informatica.metadata.template.tx.tmplsorter.SortEntry",
    "FlatFileAttrs": "com.informatica.metadata.template.ext.da.cloud.common.FlatFileAttrs",
    "TmplUnion": "com.informatica.metadata.template.tx.tmplunion.TmplUnion",
    "TmplRank": "com.informatica.metadata.template.tx.tmplrank.TmplRank",
    "TmplCleanse": "com.informatica.metadata.template.tx.tmplcleanse.TmplCleanse",
    "TmplDQGroup": "com.informatica.metadata.template.tx.tmpldq.TmplDQGroup",
    "DQFields": "com.informatica.metadata.template.tx.tmpldq.DQFields",
    "TmplDedup": "com.informatica.metadata.template.tx.tmpldedup.TmplDedup",
    "DedupField": "com.informatica.metadata.template.tx.tmpldedup.DedupField",
    "TmplRuleSpecification": "com.informatica.metadata.template.tx.tmplrulespec.TmplRuleSpecification",
    "TmplRuleSpecificationGroup": "com.informatica.metadata.template.tx.tmplrulespec.TmplRuleSpecificationGroup",
    "RuleSpecificationFields": "com.informatica.metadata.template.tx.tmplrulespec.RuleSpecificationFields",
    "TmplDmo": "com.informatica.metadata.template.tx.tmpldmo.TmplDmo",
    "DmoTxField": "com.informatica.metadata.template.tx.tmpldmo.DmoTxField",
    "MaskingData": "com.informatica.metadata.template.tx.tmpldmo.MaskingData",
    "TmplLookup": "com.informatica.metadata.template.tx.tmpllookup.TmplLookup",
    "LookupCondition": "com.informatica.metadata.template.tx.tmpllookup.LookupCondition",
    "TmplRankGroupByFields": "com.informatica.metadata.template.tx.tmplrank.TmplRankGroupByFields",
    "TmplRankGroupByField": "com.informatica.metadata.template.tx.tmplrank.TmplRankGroupByField",
    "TmplGenerator": "com.informatica.metadata.template.tx.tmplgenerator.TmplGenerator",
    "GeneratorState": "com.informatica.metadata.template.tx.tmplgenerator.GeneratorState",
    "TmplUnionGroup": "com.informatica.metadata.template.tx.tmplunion.TmplUnionGroup",
    "FieldMapping": "com.informatica.metadata.template.common.field.FieldMapping",
    "TxFieldMapping": "com.informatica.metadata.template.common.field.TxFieldMapping",
    "TmplFlowOrderEntry": "com.informatica.metadata.template.common.TmplFlowOrderEntry",
}

# Spec field type -> (platform type, default precision, default scale, javaType).
# The spec types are the BigQuery names; other connectors reuse them with a nativeType override (field tuple fd[3]).
# DATE: the javaType of a date column is java.sql.Timestamp in every UI-authored mapping (BigQuery, Snowflake, C360,
# 29/9); java.sql.Date fails every run with "Unknown native type for field (Field: x, Type: DATE)" (BigQuery and
# PostgreSQL alike).
TYPES = {
    "STRING": ("string", 4000, 0, "java.lang.String"),
    "INTEGER": ("bigint", 19, 0, "java.lang.Long"),
    "NUMERIC": ("decimal", 28, 9, "java.math.BigDecimal"),
    "FLOAT": ("double", 15, 0, "java.lang.Double"),
    "TIMESTAMP": ("date/time", 29, 9, "java.sql.Timestamp"),
    "DATE": ("date/time", 29, 9, "java.sql.Timestamp"),
    "BOOLEAN": ("string", 10, 0, "java.lang.Boolean"),
    "INT32": ("integer", 10, 0, "java.lang.Integer"),
}

PLATFORM_TYPE_SID = "smd:com.informatica.metadata.seed.platform.Platform.typesystem/"


def typeinfo(t):
    """(platform type, precision, scale, javaType) for a spec field type, with a clear error for unknown names."""
    try:
        return TYPES[t]
    except KeyError:
        from .spec import SpecError
        raise SpecError("unknown field type %r (known: %s)" % (t, ", ".join(TYPES))) from None
