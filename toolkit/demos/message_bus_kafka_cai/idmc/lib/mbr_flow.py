"""mbr_flow.py - step builder for CAI PROCESS.xml flows (generic; offline, standard library only).

The grammar comes from genuine designer exports and the agent's process model (PROVEN in an earlier form: these exact
element shapes published and ran on a Secure Agent in 2026-10). A step is (sid, render): render(next_id) returns the
step XML with a link to next_id. chain() links a list of steps. Containers (Decision = exclusive, Parallel, the catch
eventContainer) render nested <flow> elements whose last step links back to the container with a containerLink,
unless the last step is terminal (End / Jump To).

Rules encoded here (see BUILD.md Gotchas):
- IPD stores '' as an EMPTY field, so `$temp.x = ''` is false on an unset field: sx() wraps simple field references
  in string() (L-CAI pattern, proven).
- A Decision whose branches all end must have NO outgoing link, else publish fails with 'Link definition error'
  (L-CAI-135).
- Wait with a period from a field: <duration source="formula"><expression>concat('PT', x, 'S')</expression>
  (L-CAI-134).
- Subprocess outputs need an explicit output mapping; a callee fault is caught by an eventContainer around the
  Subprocess step (L-CAI-137).
"""
from __future__ import annotations

import html
import itertools
import re

E = lambda s: html.escape(str(s), quote=True)  # noqa: E731
_ids = itertools.count(1)
PREFIX = "m"

JS_TMPL = r"""concat('"', replace(replace(replace(string(EXPR), '\p{Cc}', ' '), '\\', '\\\\'), '"', '\\"'), '"')"""


def js(expr: str) -> str:
    """XQuery expression -> JSON string literal (control chars -> space; backslash and quote escaped)."""
    return JS_TMPL.replace("EXPR", expr)


def jobj(pairs) -> str:
    """XQuery concat() building a flat JSON object. pairs: (key, xquery) -> JSON string; (key, xquery, 'raw') -> the
    expression is inserted as JSON text (an array or object built elsewhere)."""
    parts = []
    for i, p in enumerate(pairs):
        k, v = p[0], p[1]
        parts.append("'%s\"%s\":'" % ("{" if i == 0 else ",", k))
        parts.append(v if len(p) > 2 else js(v))
    return "concat(" + ", ".join(parts) + ", '}')"


_FIELD = re.compile(r"\$(temp|input)\.([A-Za-z_][A-Za-z0-9_]*)(?![A-Za-z0-9_/\[])")


def sx(expr: str) -> str:
    """Wrap every simple $temp.x / $input.x in string() (the event input stays a node)."""
    return _FIELD.sub(lambda m: m.group(0) if m.group(2) == "event" else f"string(${m.group(1)}.{m.group(2)})", expr)


def nid(kind="n"):
    return f"{PREFIX}{kind}{next(_ids)}"


class Step:
    def __init__(self, sid, render, terminal=False):
        self.sid, self.render, self.terminal = sid, render, terminal


def _link(sid, nxt):
    return f'<link id="{sid}_x{next(_ids)}" targetId="{nxt}"/>' if nxt else ""


def chain(steps, last_next=None):
    out = []
    for i, s in enumerate(steps):
        nxt = steps[i + 1].sid if i + 1 < len(steps) else last_next
        out.append(s.render(None if s.terminal else nxt))
    return "".join(out)


# ------------------------------------------------------------------ simple steps
def op(to, expr):
    """Assignment operation: field <- XQuery formula."""
    return f'<operation source="formula" to="{to}"><expression language="XQuery">{E(sx(expr))}</expression></operation>'


def opf(to, field):
    """Assignment operation: field <- another field (also used for service/subflow output mapping)."""
    return f'<operation source="field" to="{to}">{field}</operation>'


def opc(to, const):
    return f'<operation source="constant" to="{to}">{E(const)}</operation>'


def assign(title, ops, sid=None):
    sid = sid or nid("as")
    return Step(sid, lambda nxt: f'<assignment id="{sid}"><title>{E(title)}</title>{"".join(ops)}{_link(sid, nxt)}</assignment>')


def setv(**kv):
    return [op(f"temp.{k}", v) for k, v in kv.items()]


def _params(inputs):
    xs = []
    for n, kind, v in inputs:
        if kind == "field":
            xs.append(f'<parameter name="{n}" source="field" updatable="true">{v}</parameter>')
        elif kind == "const":
            xs.append(f'<parameter name="{n}" source="constant">{E(v)}</parameter>')
        else:
            xs.append(f'<parameter name="{n}" source="formula"><expression language="XQuery">{E(sx(v))}</expression></parameter>')
    return "".join(xs)


def service(title, conn, conn_guid, action, inputs=(), outputs=(), sid=None):
    """Service step: a REST action of an app connection (<conn>:<action>) or a Kafka producer (<conn>:<eventTarget>).
    inputs [(param, 'field'|'const'|'formula', value)]; outputs [(to_field, service_output_field)]."""
    sid = sid or nid("sv")
    outs = "".join(opf(t, f) for t, f in outputs)

    def r(nxt):
        return (f'<service id="{sid}"><title>{E(title)}</title><serviceName>{conn}:{action}</serviceName>'
                f'<serviceGUID>{conn_guid}</serviceGUID><serviceInput>{_params(inputs)}</serviceInput>'
                + (f"<serviceOutput>{outs}</serviceOutput>" if outs else "<serviceOutput/>") + _link(sid, nxt) + "</service>")
    return Step(sid, r)


def subflow(title, callee, callee_guid, inputs=(), out_fields=(), out_map=(), sid=None):
    """Subprocess step. out_fields = the callee's output names (outputDef); out_map [(to_field, callee_output)]."""
    sid = sid or nid("sp")
    odef = "".join(f'<field name="{n}" type="string"><options><option name="required">false</option></options></field>'
                   for n in out_fields)
    omap = "".join(opf(t, f) for t, f in out_map)

    def r(nxt):
        return (f'<subflow id="{sid}"><title>{E(title)}</title><subflowGUID>{callee_guid}</subflowGUID>'
                f'<subflowPath>{callee}</subflowPath><runForEach>false</runForEach><input>{_params(inputs)}</input>'
                f'<outputDef>{odef}</outputDef>' + (f"<output>{omap}</output>" if omap else "") + _link(sid, nxt) + "</subflow>")
    return Step(sid, r)


def wait(title, seconds=None, expr=None, sid=None):
    """Wait a fixed number of seconds, or expr = an XQuery returning seconds (PROVEN both ways)."""
    sid = sid or nid("wt")

    def r(nxt):
        if expr:
            inner = sx("concat('PT', string(" + expr + "), 'S')")
            dur = f'<duration source="formula"><expression language="XQuery">{E(inner)}</expression></duration>'
        else:
            dur = (f'<duration source="formula"><function name="duration_expression"><arg name="value">{int(seconds)}</arg>'
                   f'<arg name="scale">S</arg><arg name="businessDays"/></function></duration>')
        return f'<wait id="{sid}"><title>{E(title)}</title>{dur}{_link(sid, nxt)}</wait>'
    return Step(sid, r)


def jump(target_sid, sid=None):
    sid = sid or nid("jp")
    return Step(sid, lambda nxt: f'<jumpTo id="{sid}"><link id="{sid}_j" targetId="{target_sid}"/></jumpTo>', terminal=True)


def end(sid=None):
    sid = sid or nid("en")
    return Step(sid, lambda nxt: f'<end id="{sid}"/>', terminal=True)


def milestone(title="reply", status=200, sid=None):
    """Milestone with an HTTP status: replies to the REST caller with every output field (L-CAI-144)."""
    sid = sid or nid("ms")
    return Step(sid, lambda nxt: f'<milestone id="{sid}"><title>{E(title)}</title><httpStatus>{status}</httpStatus>{_link(sid, nxt)}</milestone>')


# ------------------------------------------------------------------ containers
def _branch_flow(cid, fid, steps):
    body = chain(steps)
    back = "" if (steps and steps[-1].terminal) else f'<link id="{fid}_b" targetId="{cid}" type="containerLink"/>'
    return f'<flow id="{fid}">{body}{back}</flow>'


def decision(title, branches, sid=None):
    """branches [(xquery_condition or None for 'otherwise', [steps])]; the otherwise branch must be last."""
    sid = sid or nid("dc")
    fids = [f"{sid}_f{i}" for i in range(len(branches))]

    def r(nxt):
        flows = "".join(_branch_flow(sid, fid, steps) for fid, (_, steps) in zip(fids, branches))
        links = ""
        for i, (fid, (cond, _)) in enumerate(zip(fids, branches)):
            if cond is None:
                links += f'<link id="{sid}_c{i}" targetId="{fid}" type="containerLink"/>'
            else:
                links += (f'<link id="{sid}_c{i}" targetId="{fid}" type="containerLink"><condition source="formula">'
                          f'<expression language="XQuery">{E(sx(cond))}</expression></condition></link>')
        return f'<container id="{sid}" type="exclusive"><title>{E(title)}</title>{flows}{links}{_link(sid, nxt)}</container>'
    return Step(sid, r, terminal=all(steps and steps[-1].terminal for _, steps in branches))


def parallel(title, branches, sid=None):
    sid = sid or nid("pr")
    fids = [f"{sid}_f{i}" for i in range(len(branches))]

    def r(nxt):
        flows = "".join(_branch_flow(sid, fid, steps) for fid, steps in zip(fids, branches))
        links = "".join(f'<link id="{sid}_c{i}" targetId="{fid}" type="containerLink"/>' for i, fid in enumerate(fids))
        return f'<container id="{sid}" type="parallel"><title>{E(title)}</title>{flows}{links}{_link(sid, nxt)}</container>'
    return Step(sid, r)


def catching(wrapped: Step, ok_steps, fault_steps, fault_field="faultInfo", sid=None):
    """eventContainer around ONE service/subflow step: ok_steps on success, fault_steps on a fault
    ($output.faultInfo[1]/code and /reason carry the fault)."""
    sid = sid or nid("ec")
    ok = ok_steps or [assign("ok", [])]

    def r(nxt):
        return (f'<eventContainer id="{sid}">{wrapped.render(None)}'
                + _branch_flow(sid, f"{sid}_ok", ok) + _branch_flow(sid, f"{sid}_ft", fault_steps)
                + f'<link id="{sid}_s" targetId="{sid}_ok" type="containerLink"/>{_link(sid, nxt)}'
                f'<events><catch faultField="{fault_field}" id="{sid}_c" interrupting="true">'
                f'<link id="{sid}_cl" targetId="{sid}_ft" type="containerLink"/></catch></events></eventContainer>')
    return Step(sid, r)


def flow(steps):
    """Top-level flow: start -> steps (the last step must be End or a Jump)."""
    return f'<flow id="a"><start id="b"><link id="b_l" targetId="{steps[0].sid}"/></start>' + chain(steps) + "</flow>"
