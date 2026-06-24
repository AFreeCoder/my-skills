import json, sys, os, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
SCHEMA = os.path.join(HERE, "..", "review-schema.json")
FIX = os.path.join(HERE, "fixtures")

def load(p): return json.load(open(p))

def validate(inst):
    """返回 True=合法。优先用 jsonschema;无则回退关键字段冒烟校验。"""
    schema = load(SCHEMA)
    try:
        import jsonschema
        jsonschema.validate(inst, schema)
        return True
    except ImportError:
        if inst.get("verdict") not in ("approve", "needs-revision"): return False
        for k in ("findings", "prior_findings_status", "open_questions"):
            if not isinstance(inst.get(k), list): return False
        for f in inst.get("findings", []):
            if f.get("severity") not in ("blocker","major","minor"): return False
            for req in ("id","anchor","recommendation","category","title","detail"):
                if not f.get(req): return False
            c = f.get("confidence")
            if not isinstance(c,(int,float)) or not (0 <= c <= 1): return False
        return True
    except Exception:
        return False

def main():
    cases = [("valid-review.json", True),
             ("invalid-missing-anchor.json", False),
             ("invalid-bad-severity.json", False)]
    failed = 0
    for name, expected in cases:
        got = validate(load(os.path.join(FIX, name)))
        ok = (got == expected)
        print(f"{'ok' if ok else 'FAIL'}: {name} expected={expected} got={got}")
        if not ok: failed += 1
    sys.exit(1 if failed else 0)

if __name__ == "__main__":
    main()
