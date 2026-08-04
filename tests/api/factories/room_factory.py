from faker import Faker

fake = Faker()

ROOM_TYPES = ["Single", "Twin", "Double", "Family", "Suite"]
ROOM_FEATURES = ["WiFi", "TV", "Radio", "Refreshments", "Safe", "Views"]


def random_room_payload() -> dict:
    return {
        "roomName": str(fake.unique.random_int(min=500, max=99999)),
        "type": fake.random_element(ROOM_TYPES),
        "accessible": fake.boolean(),
        "roomPrice": fake.random_int(min=50, max=500),
        "description": fake.sentence(),
        "features": fake.random_elements(ROOM_FEATURES, length=2, unique=True),
    }
