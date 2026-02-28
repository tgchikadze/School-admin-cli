"""
tests/test_api.py — тесты для routers/students.py

Запуск:
cd project5-final
pytest tests/ -v
"""


def _get_class_id(client, name="9"):
    """Получить id класса по имени."""
    r = client.get("/api/classes")
    for c in r.json():
        if c["name"] == name:
            return c["id"]
    return None


# ═══════════════════════════════════════════════════
# POST /api/students
# ═══════════════════════════════════════════════════

class TestCreateStudent:

    def test_create_ok(self, client):
        cid = _get_class_id(client, "9")
        r = client.post("/api/students", json={
            "full_name": "Иванов Иван Иванович",
            "contract_number": "ДОГ-001",
            "class_id": cid,
        })
        assert r.status_code == 201, r.text
        data = r.json()
        assert data["full_name"] == "Иванов Иван Иванович"
        assert data["class_id"] == cid
        assert data["monthly_payment"] == 7000

    def test_create_auto_price_fixed(self, client):
        cid = _get_class_id(client, "8")
        r = client.post("/api/students", json={
            "full_name": "Петров Пётр Петрович",
            "contract_number": "ДОГ-002",
            "class_id": cid,
        })
        assert r.status_code == 201
        assert r.json()["monthly_payment"] == 8000

    def test_create_class_7_price(self, client):
        cid = _get_class_id(client, "7")
        r = client.post("/api/students", json={
            "full_name": "Тест Семь", "contract_number": "К-7", "class_id": cid,
        })
        assert r.json()["monthly_payment"] == 8500

    def test_create_class_11_zero_price(self, client):
        cid = _get_class_id(client, "11")
        r = client.post("/api/students", json={
            "full_name": "Одиннадцатиклассник", "contract_number": "К-11", "class_id": cid,
        })
        assert r.status_code == 201
        assert r.json()["monthly_payment"] == 0

    def test_create_duplicate_contract(self, client):
        cid = _get_class_id(client, "9")
        client.post("/api/students", json={
            "full_name": "Один", "contract_number": "ДОГ-DUP", "class_id": cid,
        })
        r = client.post("/api/students", json={
            "full_name": "Другой", "contract_number": "ДОГ-DUP", "class_id": cid,
        })
        assert r.status_code == 409

    def test_create_invalid_class(self, client):
        r = client.post("/api/students", json={
            "full_name": "Тест", "contract_number": "Т-001", "class_id": 99999,
        })
        assert r.status_code == 404

    def test_create_empty_name(self, client):
        cid = _get_class_id(client, "9")
        r = client.post("/api/students", json={
            "full_name": "", "contract_number": "Т-002", "class_id": cid,
        })
        assert r.status_code == 422


# ═══════════════════════════════════════════════════
# GET /api/students
# ═══════════════════════════════════════════════════

class TestListStudents:

    def _seed_3(self, client):
        c9 = _get_class_id(client, "9")
        c11 = _get_class_id(client, "11")
        for full_name, contract, cls in [
            ("Иванов Иван", "Д-1", c9),
            ("Петрова Мария", "Д-2", c11),
            ("Сидоров Алексей", "Д-3", c9),
        ]:
            client.post("/api/students", json={
                "full_name": full_name, "contract_number": contract, "class_id": cls,
            })

    def test_list_all(self, client):
        self._seed_3(client)
        r = client.get("/api/students")
        assert r.status_code == 200
        assert len(r.json()) == 3

    def test_filter_by_class(self, client):
        self._seed_3(client)
        c9 = _get_class_id(client, "9")
        r = client.get(f"/api/students?class_id={c9}")
        data = r.json()
        assert len(data) == 2
        assert all(s["class_id"] == c9 for s in data)

    def test_search_by_name(self, client):
        self._seed_3(client)
        r = client.get("/api/students?search=Петров")
        data = r.json()
        assert len(data) == 1
        assert data[0]["full_name"] == "Петрова Мария"

    def test_search_case_insensitive(self, client):
        self._seed_3(client)
        r = client.get("/api/students?search=Иванов")
        assert len(r.json()) == 1

    def test_search_no_results(self, client):
        self._seed_3(client)
        r = client.get("/api/students?search=несуществующий")
        assert r.json() == []

    def test_empty_db(self, client):
        r = client.get("/api/students")
        assert r.status_code == 200
        assert r.json() == []


# ═══════════════════════════════════════════════════
# GET /api/students/{id}
# ═══════════════════════════════════════════════════

class TestGetStudentById:

    def test_get_ok(self, client):
        cid = _get_class_id(client, "10")
        r = client.post("/api/students", json={
            "full_name": "Тест", "contract_number": "Т-1", "class_id": cid,
        })
        sid = r.json()["id"]
        r = client.get(f"/api/students/{sid}")
        assert r.status_code == 200
        assert r.json()["full_name"] == "Тест"

    def test_not_found(self, client):
        r = client.get("/api/students/999")
        assert r.status_code == 404


# ═══════════════════════════════════════════════════
# PUT /api/students/{id}
# ═══════════════════════════════════════════════════

class TestUpdateStudent:

    def _create(self, client):
        cid = _get_class_id(client, "9")
        r = client.post("/api/students", json={
            "full_name": "Старое ФИО", "contract_number": "К-1", "class_id": cid,
        })
        return r.json()["id"]

    def test_update_name(self, client):
        sid = self._create(client)
        r = client.put(f"/api/students/{sid}", json={"full_name": "Новое ФИО"})
        assert r.status_code == 200
        assert r.json()["full_name"] == "Новое ФИО"
        assert r.json()["contract_number"] == "К-1"

    def test_update_compensation(self, client):
        sid = self._create(client)
        r = client.put(f"/api/students/{sid}", json={"compensation": 5000})
        assert r.json()["compensation"] == 5000

    def test_update_not_found(self, client):
        r = client.put("/api/students/999", json={"full_name": "X"})
        assert r.status_code == 404


# ═══════════════════════════════════════════════════
# DELETE /api/students/{id}
# ═══════════════════════════════════════════════════

class TestDeleteStudent:

    def test_delete_ok(self, client):
        cid = _get_class_id(client, "9")
        r = client.post("/api/students", json={
            "full_name": "Удаляемый", "contract_number": "У-1", "class_id": cid,
        })
        sid = r.json()["id"]
        r = client.delete(f"/api/students/{sid}")
        assert r.status_code == 200
        assert client.get(f"/api/students/{sid}").status_code == 404

    def test_delete_not_found(self, client):
        r = client.delete("/api/students/999")
        assert r.status_code == 404

    def test_delete_doesnt_affect_others(self, client):
        cid = _get_class_id(client, "9")
        r1 = client.post("/api/students", json={
            "full_name": "Аа", "contract_number": "К-1", "class_id": cid,
        })
        client.post("/api/students", json={
            "full_name": "Бб", "contract_number": "К-2", "class_id": cid,
        })
        client.delete(f"/api/students/{r1.json()['id']}")
        r = client.get("/api/students")
        assert len(r.json()) == 1
        assert r.json()[0]["full_name"] == "Бб"


# ═══════════════════════════════════════════════════
# EXAM CHOICES
# ═══════════════════════════════════════════════════

class TestExamChoices:

    def test_set_exams_recalc(self, client):
        cid = _get_class_id(client, "11")
        r = client.post("/api/students", json={
            "full_name": "ЕГЭшник", "contract_number": "Е-1", "class_id": cid,
        })
        sid = r.json()["id"]
        assert r.json()["monthly_payment"] == 0

        r = client.post(f"/api/students/{sid}/exams", json={
            "student_id": sid,
            "subjects": ["Химия", "Биология"],
        })
        assert r.status_code == 200
        assert len(r.json()) == 2

        r = client.get(f"/api/students/{sid}")
        assert r.json()["monthly_payment"] == 6000  # 2 * 3000
