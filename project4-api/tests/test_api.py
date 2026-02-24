class TestUniversities:

    def test_list(self, client):
        r = client.get("/api/universities")
        assert r.status_code == 200
        assert r.json()["total"] >= 1

    def test_filter_city(self, client):
        r = client.get("/api/universities?city=Testville")
        assert all("Testville" in u["city"] for u in r.json()["items"])

    def test_search(self, client):
        r = client.get("/api/universities?search=Test")
        assert r.json()["total"] >= 1

    def test_detail(self, client):
        r = client.get("/api/universities/test_uni")
        assert r.status_code == 200
        assert r.json()["id"] == "test_uni"
        assert len(r.json()["programs"]) >= 1

    def test_not_found(self, client):
        assert client.get("/api/universities/nope").status_code == 404


class TestPrograms:

    def test_list(self, client):
        assert client.get("/api/programs").json()["total"] >= 1

    def test_filter_okso(self, client):
        items = client.get("/api/programs?okso_code=09.03.01").json()["items"]
        assert all("09.03.01" in p["okso_code"] for p in items)

    def test_filter_university(self, client):
        items = client.get("/api/programs?university_id=test_uni").json()["items"]
        assert all(p["university_id"] == "test_uni" for p in items)

    def test_pagination(self, client):
        d = client.get("/api/programs?page=1&size=1").json()
        assert len(d["items"]) <= 1

    def test_sort(self, client):
        r = client.get("/api/programs?sort_by=program_name&order=asc")
        assert r.status_code == 200


class TestOlympiads:

    def test_list(self, client):
        assert client.get("/api/olympiads").status_code == 200

    def test_filter_reviewed(self, client):
        items = client.get("/api/olympiads?reviewed=false").json()["items"]
        assert all(o["reviewed"] is False for o in items)

    def test_create(self, client):
        r = client.post("/api/olympiads", json={
            "university_id": "test_uni",
            "olympiad_name": "New Olympiad",
            "olympiad_level": "2",
            "subject": "math",
            "benefit_type": "100 баллов",
        })
        assert r.status_code == 200
        assert r.json()["olympiad_name"] == "New Olympiad"
        assert r.json()["reviewed"] is False

    def test_update(self, client):
        items = client.get("/api/olympiads").json()["items"]
        oid = items[0]["id"]
        r = client.patch(f"/api/olympiads/{oid}", json={
            "subject": "updated_subject",
        })
        assert r.status_code == 200
        assert r.json()["subject"] == "updated_subject"

    def test_approve(self, client):
        items = client.get("/api/olympiads").json()["items"]
        oid = items[0]["id"]
        r = client.patch(f"/api/olympiads/{oid}", json={"reviewed": True})
        assert r.status_code == 200
        assert r.json()["reviewed"] is True

    def test_delete(self, client):
        created = client.post("/api/olympiads", json={
            "university_id": "test_uni",
            "olympiad_name": "To Delete",
        })
        oid = created.json()["id"]
        r = client.delete(f"/api/olympiads/{oid}")
        assert r.status_code == 200
        assert r.json()["status"] == "deleted"

    def test_update_not_found(self, client):
        r = client.patch("/api/olympiads/99999", json={"subject": "x"})
        assert r.status_code == 404

    def test_delete_not_found(self, client):
        assert client.delete("/api/olympiads/99999").status_code == 404


class TestAdmin:

    def test_status(self, client):
        d = client.get("/api/admin/status").json()
        assert "universities" in d
        assert "programs" in d
        assert "olympiads" in d


class TestPages:

    def test_index(self, client):
        assert client.get("/").status_code == 200

    def test_programs_page(self, client):
        assert client.get("/programs.html").status_code == 200

    def test_olympiads_page(self, client):
        assert client.get("/olympiads.html").status_code == 200

    def test_review_page(self, client):
        assert client.get("/review.html").status_code == 200

    def test_admin_page(self, client):
        assert client.get("/admin.html").status_code == 200
