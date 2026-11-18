"""Expression with window functions (LAG, LEAD, running aggregates over a partition/order frame).

    {"type": "expression", "name": "EXP_W",
     "window": {"partitionBy": ["customer_id"], "orderBy": ["order_ts", "-order_id"],
                "startOffset": -1, "endOffset": 0, "allRowsPreceding": false, "allRowsFollowing": false,
                "allowUnsupported": true},
     "fields": [{"name": "prev_amount", "type": "NUMERIC", "expr": "LAG(amount, 1, 0)"}]}

Measured on a Secure Agent (standard CDI mapping): the package imports and the mapping reads as valid, but the
run fails at DTM start with "Invalid reference to LAG found" / "invalid function reference". Window functions
only run in elastic (at-scale) and SQL-ELT mappings, which this generator does not produce. So this node refuses
to build unless the window dict says "allowUnsupported": true (for experiments).

What works on a standard mapping instead: a Sorter on (partition keys, order keys) followed by an Expression
whose VARIABLE ports keep the previous row's values (examples/probes/m_probe_lookup_running.json, EXP_RUNNING):
    v_same      = IIF(customer_id = v_prev_cust, 1, 0)        # reads v_prev_cust BEFORE it is updated
    v_run       = IIF(v_same = 1, v_run + amount, amount)     # running total
    v_lag       = IIF(v_same = 1, v_prev_amt, NULL)           # LAG(amount)
    v_prev_amt  = amount
    v_prev_cust = customer_id
    running_total (OUTPUT) = v_run ; prev_amount (OUTPUT) = v_lag

The window's allowUnsupported / allRowsPreceding / allRowsFollowing are booleans (true / false, "true" / "false" in
any case, 0 / 1: "allowUnsupported": "false" used to build); partitionBy / orderBy are lists of field names (text);
startOffset / endOffset are whole numbers (default 0; int() used to turn 1.5 into 1 and true into 1).
``window_options`` reads them all, for the build and the lint hook (nodes/expression.py ``lint_problems``) alike.
"""
from .. import values
from .expression import expression_fields


def window_options(nd):
    """The window's options as build_window reads them (SpecError naming the node and the option for a value it refuses,
    and the refusal of window functions unless allowUnsupported)."""
    from ..spec import SpecError
    name, w = nd["name"], nd["window"]
    if not isinstance(w, dict):
        raise SpecError("expression %r: window must be an object {partitionBy, orderBy, startOffset, endOffset, ...}, got %s"
                        % (name, values.brief(w)))
    # the window's options as "window.<key>" of the node, so messages name both
    wnd = dict({"window." + k: v for k, v in w.items()}, type="expression", name=name)
    if not values.flag(wnd, "window.allowUnsupported"):
        raise SpecError("expression %r uses window functions, which fail at run time on a standard CDI mapping "
                        "(\"Invalid reference to LAG\"). Use a Sorter + VARIABLE ports (see nodes/expression_window.py), "
                        "or set window.allowUnsupported=true to build it anyway." % name)
    return {"following": values.flag(wnd, "window.allRowsFollowing"), "preceding": values.flag(wnd, "window.allRowsPreceding"),
            "partition": values.text_list(wnd, "window.partitionBy"), "orderBy": values.text_list(wnd, "window.orderBy"),
            "endOffset": values.as_whole(w.get("endOffset"), values.where(wnd, "window.endOffset"), None, 0, "0"),
            "startOffset": values.as_whole(w.get("startOffset"), values.where(wnd, "window.startOffset"), None, 0, "0")}


def build_window(ctx, nd):
    b = ctx.b; name = nd["name"]
    o = window_options(nd)
    following, preceding, partition, order_by = o["following"], o["preceding"], o["partition"], o["orderBy"]
    g = b.group("DefaultGroup", True, True)
    fl = expression_fields(b, nd["fields"], nd)
    order = [b.new("SortEntry", ascending="false" if k.startswith("-") else "true", fieldName=k.lstrip("-"))
             for k in order_by]
    tx = b.new("TmplExpression", augmented="false", createTime=ctx.now, name=name,
               advancedProperties=b.adv([("Tracing Level", "Normal")]), groups=[g], additionalFields="",
               windowConfigurationEnabled="true", fields=fl,
               windowSpec=b.new("TmplExpressionWindowSpec",
                                allRowsFollowing=values.imf_bool(following), allRowsPreceding=values.imf_bool(preceding),
                                endOffset=o["endOffset"], startOffset=o["startOffset"],
                                partitionKeys=partition, orderKeys=order))
    ctx.out(name, g); ctx.inp(name, g)
    return tx
