import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

from app.extensions import db
from app.models import FestivalUser, ParticipationApplication


def make_init_data(user_id: int = 42) -> str:
    params = {
        "auth_date": str(int(time.time())),
        "chat": json.dumps({"id": 123, "type": "DIALOG"}, separators=(",", ":")),
        "query_id": "test-query",
        "user": json.dumps(
            {
                "id": user_id,
                "first_name": "Иван",
                "last_name": "Иванов",
                "username": "ivan",
            },
            separators=(",", ":"),
            ensure_ascii=False,
        ),
    }
    check_string = "\n".join(f"{key}={value}" for key, value in sorted(params.items()))
    secret_key = hmac.new(
        b"WebAppData",
        b"test-bot-token",
        hashlib.sha256,
    ).digest()
    params["hash"] = hmac.new(
        secret_key,
        check_string.encode(),
        hashlib.sha256,
    ).hexdigest()
    return urlencode(params)


def post_application(client, payload: dict, init_data: str | None = None):
    headers = {}
    if init_data is not None:
        headers["X-Max-WebApp-Data"] = init_data
    return client.post(
        "/max/miniapp/applications",
        json=payload,
        headers=headers,
    )


def test_ride_application_is_saved(client, app):
    response = post_application(
        client,
        {
            "activity": "ride",
            "first_name": "Иван",
            "last_name": "Иванов",
            "age": 24,
            "equipment": "scooter",
        },
        make_init_data(),
    )

    assert response.status_code == 201
    assert response.json["status"] == "created"

    with app.app_context():
        application = db.session.get(
            ParticipationApplication,
            response.json["application_id"],
        )
        assert application.max_user_id == 42
        assert application.activity == "ride"
        assert application.age == 24
        assert application.equipment == "scooter"
        assert application.equipment_other is None
        assert db.session.get(FestivalUser, 42).chat_id == 123


def test_removed_ride_equipment_is_rejected(client):
    for equipment in ("skate", "other"):
        response = post_application(
            client,
            {
                "activity": "ride",
                "first_name": "Иван",
                "last_name": "Иванов",
                "age": 24,
                "equipment": equipment,
            },
            make_init_data(),
        )

        assert response.status_code == 422


def test_stars_application_is_saved(client, app):
    response = post_application(
        client,
        {
            "activity": "stars",
            "first_name": "Анна",
            "last_name": "Петрова",
            "phone": "+7 999 123-45-67",
            "performance_description": "Вокальный номер с живой музыкой",
        },
        make_init_data(),
    )

    assert response.status_code == 201

    with app.app_context():
        application = db.session.get(
            ParticipationApplication,
            response.json["application_id"],
        )
        assert application.activity == "stars"
        assert application.phone == "+7 999 123-45-67"
        assert application.performance_description.startswith("Вокальный")
        assert application.age is None


def test_user_can_load_saved_applications(client):
    init_data = make_init_data()
    post_application(
        client,
        {
            "activity": "ride",
            "first_name": "Иван",
            "last_name": "Иванов",
            "age": 24,
            "equipment": "bicycle",
        },
        init_data,
    )

    response = client.get(
        "/max/miniapp/applications",
        headers={"X-Max-WebApp-Data": init_data},
    )

    assert response.status_code == 200
    assert response.json["applications"] == [
        {
            "id": response.json["applications"][0]["id"],
            "activity": "ride",
            "first_name": "Иван",
            "last_name": "Иванов",
            "age": 24,
            "equipment": "bicycle",
            "equipment_other": None,
            "phone": None,
            "performance_description": None,
            "status": "new",
            "created_at": response.json["applications"][0]["created_at"],
        }
    ]


def test_user_cannot_load_another_users_applications(client):
    post_application(
        client,
        {
            "activity": "ride",
            "first_name": "Иван",
            "last_name": "Иванов",
            "age": 24,
            "equipment": "bicycle",
        },
        make_init_data(user_id=42),
    )

    response = client.get(
        "/max/miniapp/applications",
        headers={"X-Max-WebApp-Data": make_init_data(user_id=43)},
    )

    assert response.status_code == 200
    assert response.json == {"applications": []}


def test_duplicate_activity_is_rejected(client):
    payload = {
        "activity": "ride",
        "first_name": "Иван",
        "last_name": "Иванов",
        "age": 24,
        "equipment": "bicycle",
    }
    init_data = make_init_data()

    assert post_application(client, payload, init_data).status_code == 201
    response = post_application(client, payload, init_data)

    assert response.status_code == 409
    assert response.json["error"] == "duplicate_application"


def test_application_requires_valid_max_init_data(client):
    response = post_application(
        client,
        {
            "activity": "ride",
            "first_name": "Иван",
            "last_name": "Иванов",
            "age": 24,
            "equipment": "bicycle",
        },
    )

    assert response.status_code == 401

    get_response = client.get("/max/miniapp/applications")
    assert get_response.status_code == 401


def test_activity_specific_fields_are_required(client):
    response = post_application(
        client,
        {
            "activity": "stars",
            "first_name": "Анна",
            "last_name": "Петрова",
        },
        make_init_data(),
    )

    assert response.status_code == 422
