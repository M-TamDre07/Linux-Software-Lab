def test_desktop_module_imports_without_creating_a_window():
    # Importing the UI is a lightweight smoke test; no display server is required.
    import paketscope.app as desktop

    assert callable(desktop.main)
    assert desktop.MainWindow is not None
