from pydantic import BaseModel


class Room(BaseModel):
    roomid: int
    roomName: str
    type: str
    accessible: bool
    description: str
    features: list[str]
    roomPrice: int
    image: str | None = None


class RoomList(BaseModel):
    rooms: list[Room]
