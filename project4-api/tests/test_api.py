
class TestUniversities:
    def test_list(self, client):
        r = client.get("/api/universities")
        assert r.status_code == 200
        assert r.json()["total"] >= 1

    def test_filter_city(self, client):
        r = client.get("/api/universities?city=Testville")
        assert all("Testville" in u["city"] for u in r.json()["items"])

    def test_detail(self, client):
        r = client.get("/api/universities/test_uni")
        assert r.status_code == 200
        assert r.json()["id"] == "test_uni"
        assert len(r.json()["programs"]) >= 1

    def test_404(self, client):
        assert client.get("/api/universities/nope").status_code == 404


class TestPrograms:
    def test_list(self, client):
        assert client.get("/api/programs").json()["total"] >= 1

    def test_filter_okso(self, client):
        items = client.get("/api/programs?okso_code=09.03.01").json()["items"]
        assert all("09.03.01" in p["okso_code"] for p in items)

    def test_pagination(self, client):
        d = client.get("/api/programs?page=1&size=1").json()
        assert len(d["items"]) <= 1


class TestOlympiads:
    def test_list(self, client):
        assert client.get("/api/olympiads").status_code == 200

    def test_filter_benefit(self, client):
        items = client.get("/api/olympiads?benefit_type=BVI").json()["items"]
        assert all("BVI" in o["benefit_type"] for o in items)


class TestStats:
    def test_stats(self, client):
        d = client.get("/api/stats").json()
        assert "universities" in d and "programs" in d and "olympiads" in d
