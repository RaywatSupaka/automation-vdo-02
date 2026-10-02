from smartflow.native_host import main

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        # Native transport stdout/stderr must not leak raw exceptions or paths.
        raise SystemExit(1)
