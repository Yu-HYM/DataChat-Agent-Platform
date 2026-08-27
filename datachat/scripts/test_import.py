import sys
sys.path.insert(0, ".")
try:
    import web.frontend
    print("import OK")
except Exception as e:
    print(f"ERROR: {e}")
