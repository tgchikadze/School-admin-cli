def test_override_check():
    from api.dependencies import get_db
    from api.main import app

    print(f"\nget_db id: {id(get_db)}")
    print(f"override keys ids: {[id(k) for k in app.dependency_overrides]}")
    print(f"get_db in overrides: {get_db in app.dependency_overrides}")

    assert get_db in app.dependency_overrides, "get_db NOT in overrides!"
