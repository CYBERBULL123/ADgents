import server


def test_root_and_template_routes_are_registered_once():
    paths = [getattr(route, "path", None) for route in server.app.routes]

    assert paths.count("/") == 1
    assert paths.count("/api/templates") == 1