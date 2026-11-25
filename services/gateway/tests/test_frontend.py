async def test_dashboard_and_assets(client) -> None:
    response = await client.get("/")
    assert response.status_code == 200
    assert 'lang="ru"' in response.text
    assert 'id="root"' in response.text
    assert 'type="module"' in response.text
    assert "/static/app.js" in response.text
    for path, content_type in (("app.js", "javascript"), ("app.css", "text/css")):
        asset = await client.get(f"/static/{path}")
        assert asset.status_code == 200
        assert content_type in asset.headers["content-type"]


async def test_static_does_not_expose_server_code(client) -> None:
    assert (await client.get("/static/../config.py")).status_code == 404
    assert (await client.get("/api/v1/projects")).status_code == 401
