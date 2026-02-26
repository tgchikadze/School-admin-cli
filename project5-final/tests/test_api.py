"""
tests/test_api.py — тесты для routers/students.py

Запуск:
    cd project5-final
    pytest tests/ -v
"""


# ═══════════════════════════════════════════════════
#  POST /api/students
# ═══════════════════════════════════════════════════

class TestCreateStudent:

    def test_create_ok(self, client):
        r = client.post("/api/students", json={
            "fio": "Иванов Иван Иванович",
            "contract_number": "ДОГ-001",
            "class_id": "9",
            "monthly_payment": 7000,
            "compensation": "мат. капитал",
        })
        assert r.status_code == 201, r.text
        data = r.json()
        assert data["id"] == "001"
        assert data["fio"] == "Иванов Иван Иванович"
        assert data["class_id"] == "9"
        assert data["monthly_payment"] == 7000
        assert data["compensation"] == "мат. капитал"

    def test_create_auto_price_fixed(self, client):
        """Для fixed-класса: если payment=0, ставится base_price."""
        r = client.post("/api/students", json={
            "fio": "Петров Пётр Петрович",
            "contract_number": "ДОГ-002",
            "class_id": "8",
        })
        assert r.status_code == 201
        assert r.json()["monthly_payment"] == 8000  # base_price класса 8

    def test_create_class_7_price(self, client):
        r = client.post("/api/students", json={
            "fio": "Тест Семь", "contract_number": "К-7", "class_id": "7",
        })
        assert r.json()["monthly_payment"] == 8500

    def test_create_class_11_zero_price(self, client):
        """Для 11 класса per_subject: payment=0 остаётся 0 (считается отдельно)."""
        r = client.post("/api/students", json={
            "fio": "Одиннадцатиклассник", "contract_number": "К-11", "class_id": "11",
        })
        assert r.status_code == 201
        # per_subject → payment НЕ подставляется автоматически
        assert r.json()["monthly_payment"] == 0

    def test_create_duplicate_fio(self, client):
        client.post("/api/students", json={
            "fio": "Дубликат ФИО", "contract_number": "ДОГ-100", "class_id": "9",
        })
        r = client.post("/api/students", json={
            "fio": "Дубликат ФИО", "contract_number": "ДОГ-999", "class_id": "9",
        })
        assert r.status_code == 409
        assert "уже существует" in r.json()["detail"]

    def test_create_duplicate_contract(self, client):
        client.post("/api/students", json={
            "fio": "Один", "contract_number": "ДОГ-DUP", "class_id": "9",
        })
        r = client.post("/api/students", json={
            "fio": "Другой", "contract_number": "ДОГ-DUP", "class_id": "9",
        })
        assert r.status_code == 409

    def test_create_invalid_class(self, client):
        """class_id=12 — не пройдёт Pydantic-валидацию."""
        r = client.post("/api/students", json={
            "fio": "Тест", "contract_number": "Т-001", "class_id": "12",
        })
        assert r.status_code == 422

    def test_create_empty_fio(self, client):
        r = client.post("/api/students", json={
            "fio": "", "contract_number": "Т-002", "class_id": "9",
        })
        assert r.status_code == 422

    def test_id_autoincrement(self, client):
        client.post("/api/students", json={
            "fio": "Первый", "contract_number": "К-1", "class_id": "7",
        })
        r = client.post("/api/students", json={
            "fio": "Второй", "contract_number": "К-2", "class_id": "7",
        })
        assert r.json()["id"] == "002"

        r = client.post("/api/students", json={
            "fio": "Третий", "contract_number": "К-3", "class_id": "7",
        })
        assert r.json()["id"] == "003"


# ═══════════════════════════════════════════════════
#  GET /api/students
# ═══════════════════════════════════════════════════

class TestListStudents:

    def _seed_3(self, client):
        for fio, contract, cls in [
            ("Иванов Иван", "Д-1", "9"),
            ("Петрова Мария", "Д-2", "11"),
            ("Сидоров Алексей", "Д-3", "9"),
        ]:
            client.post("/api/students", json={
                "fio": fio, "contract_number": contract, "class_id": cls,
            })

    def test_list_all(self, client):
        self._seed_3(client)
        r = client.get("/api/students")
        assert r.status_code == 200
        assert len(r.json()) == 3

    def test_filter_by_class(self, client):
        self._seed_3(client)
        r = client.get("/api/students?class_id=9")
        data = r.json()
        assert len(data) == 2
        assert all(s["class_id"] == "9" for s in data)

    def test_filter_by_class_11(self, client):
        self._seed_3(client)
        r = client.get("/api/students?class_id=11")
        assert len(r.json()) == 1

    def test_search_by_fio(self, client):
        self._seed_3(client)
        r = client.get("/api/students?search=петров")
        data = r.json()
        assert len(data) == 1
        assert data[0]["fio"] == "Петрова Мария"

    def test_search_case_insensitive(self, client):
        self._seed_3(client)
        r = client.get("/api/students?search=ИВАНОВ")
        assert len(r.json()) == 1

    def test_search_and_filter(self, client):
        self._seed_3(client)
        r = client.get("/api/students?search=сидоров&class_id=9")
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
#  GET /api/students/{id}
# ═══════════════════════════════════════════════════

class TestGetStudentById:

    def test_get_ok(self, client):
        client.post("/api/students", json={
            "fio": "Тест", "contract_number": "Т-1", "class_id": "10",
        })
        r = client.get("/api/students/001")
        assert r.status_code == 200
        assert r.json()["fio"] == "Тест"
        assert r.json()["class_id"] == "10"

    def test_not_found(self, client):
        r = client.get("/api/students/999")
        assert r.status_code == 404
        assert "не найден" in r.json()["detail"]


# ═══════════════════════════════════════════════════
#  PUT /api/students/{id}
# ═══════════════════════════════════════════════════

class TestUpdateStudent:

    def test_update_fio(self, client):
        client.post("/api/students", json={
            "fio": "Старое ФИО", "contract_number": "К-1", "class_id": "9",
        })
        r = client.put("/api/students/001", json={"fio": "Новое ФИО"})
        assert r.status_code == 200
        assert r.json()["fio"] == "Новое ФИО"
        assert r.json()["contract_number"] == "К-1"  # не менялось

    def test_update_payment(self, client):
        client.post("/api/students", json={
            "fio": "Тест", "contract_number": "К-1", "class_id": "9",
        })
        r = client.put("/api/students/001", json={"monthly_payment": 9999})
        assert r.json()["monthly_payment"] == 9999

    def test_update_multiple_fields(self, client):
        client.post("/api/students", json={
            "fio": "Тест", "contract_number": "К-1", "class_id": "9",
        })
        r = client.put("/api/students/001", json={
            "fio": "Новое", "compensation": "50%",
        })
        assert r.json()["fio"] == "Новое"
        assert r.json()["compensation"] == "50%"

    def test_update_not_found(self, client):
        r = client.put("/api/students/999", json={"fio": "X"})
        assert r.status_code == 404

    def test_update_dup_contract(self, client):
        client.post("/api/students", json={
            "fio": "А", "contract_number": "К-1", "class_id": "9",
        })
        client.post("/api/students", json={
            "fio": "Б", "contract_number": "К-2", "class_id": "9",
        })
        r = client.put("/api/students/002", json={"contract_number": "К-1"})
        assert r.status_code == 409


# ═══════════════════════════════════════════════════
#  DELETE /api/students/{id}
# ═══════════════════════════════════════════════════

class TestDeleteStudent:

    def test_delete_ok(self, client):
        client.post("/api/students", json={
            "fio": "Удаляемый", "contract_number": "У-1", "class_id": "9",
        })
        r = client.delete("/api/students/001")
        assert r.status_code == 200
        assert "001" in r.json()["detail"]
        # Проверяем что удалён
        assert client.get("/api/students/001").status_code == 404

    def test_delete_not_found(self, client):
        r = client.delete("/api/students/999")
        assert r.status_code == 404

    def test_delete_doesnt_affect_others(self, client):
        client.post("/api/students", json={
            "fio": "А", "contract_number": "К-1", "class_id": "9",
        })
        client.post("/api/students", json={
            "fio": "Б", "contract_number": "К-2", "class_id": "9",
        })
        client.delete("/api/students/001")
        r = client.get("/api/students")
        assert len(r.json()) == 1
        assert r.json()[0]["fio"] == "Б"


# ═══════════════════════════════════════════════════
#  DELETE /api/students  (clear all)
# ═══════════════════════════════════════════════════

class TestClearAll:

    def test_clear(self, client):
        for i in range(3):
            client.post("/api/students", json={
                "fio": f"Тест {i}", "contract_number": f"К-{i}", "class_id": "9",
            })
        r = client.delete("/api/students")
        assert r.status_code == 200
        assert "3" in r.json()["detail"]
        assert client.get("/api/students").json() == []

    def test_clear_empty(self, client):
        r = client.delete("/api/students")
        assert r.status_code == 200
        assert "0" in r.json()["detail"]


# ═══════════════════════════════════════════════════
#  GET /api  (info endpoint)
# ═══════════════════════════════════════════════════

class TestApiInfo:

    def test_api_info(self, client):
        r = client.get("/api")
        assert r.status_code == 200
        data = r.json()
        assert data["app"] == "Биотех225 Admin"
        assert "students" in data["endpoints"]
        assert data["version"] == "5.0.0"
