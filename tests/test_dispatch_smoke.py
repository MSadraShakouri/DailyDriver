import inspect

from dailydriver.cli.dispatcher import make_dispatch


def test_every_handler_accepts_repl_line_arg():
    dispatch = make_dispatch()
    failures = []
    for key, fn in dispatch.items():
        if key == "q":
            continue  # sys.exit(0) accepts optional arg
        try:
            inspect.signature(fn).bind("test")
        except TypeError as e:
            failures.append(f"  {key!r}: {e}")
    assert not failures, "Handlers with wrong arity:\n" + "\n".join(failures)
