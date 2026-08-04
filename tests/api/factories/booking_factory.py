from datetime import timedelta

from faker import Faker

fake = Faker()


def random_booking_payload(room_id: int) -> dict:
    checkin = fake.date_between(start_date="+30d", end_date="+90d")
    checkout = checkin + timedelta(days=fake.random_int(min=1, max=5))
    return {
        "roomid": room_id,
        "firstname": fake.first_name(),
        "lastname": fake.last_name(),
        "depositpaid": fake.boolean(),
        "bookingdates": {
            "checkin": checkin.isoformat(),
            "checkout": checkout.isoformat(),
        },
    }
