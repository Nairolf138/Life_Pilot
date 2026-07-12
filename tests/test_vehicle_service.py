from datetime import date, timedelta
from types import SimpleNamespace
from uuid import uuid4

import asyncio

from app.services.vehicle_service import VehicleService


class FakeSession:
    def __init__(self):
        self.calls = []

    async def execute(self, statement, params=None):
        self.calls.append((str(statement), params or {}))
        return SimpleNamespace()


def reminder_inserts(session):
    return [
        params
        for statement, params in session.calls
        if "INSERT INTO reminders" in statement
    ]


def test_technical_inspection_sync_creates_expected_future_reminders():
    session = FakeSession()
    service = VehicleService(session)
    user_id = uuid4()
    vehicle_id = uuid4()
    due_date = date.today() + timedelta(days=120)
    vehicle = SimpleNamespace(
        id=vehicle_id,
        brand="Renault",
        model="Clio",
        technical_inspection_due_date=due_date,
    )

    asyncio.run(service._sync_technical_inspection_reminders(user_id, vehicle))

    inserts = reminder_inserts(session)
    assert len(inserts) == 5
    assert [item["reminder_date"] for item in inserts] == [
        due_date - timedelta(days=90),
        due_date - timedelta(days=60),
        due_date - timedelta(days=30),
        due_date - timedelta(days=15),
        due_date - timedelta(days=7),
    ]
    assert [item["severity"] for item in inserts] == [
        "warning",
        "warning",
        "warning",
        "urgent",
        "urgent",
    ]
    assert all(item["vehicle_id"] == vehicle_id for item in inserts)


def test_technical_inspection_sync_creates_critical_overdue_reminder():
    session = FakeSession()
    service = VehicleService(session)
    due_date = date.today() - timedelta(days=1)
    vehicle = SimpleNamespace(
        id=uuid4(),
        brand="Peugeot",
        model="208",
        technical_inspection_due_date=due_date,
    )

    asyncio.run(service._sync_technical_inspection_reminders(uuid4(), vehicle))

    inserts = reminder_inserts(session)
    assert len(inserts) == 1
    assert inserts[0]["severity"] == "critical"
    assert inserts[0]["due_date"] == due_date
    assert inserts[0]["reminder_date"] == date.today()
