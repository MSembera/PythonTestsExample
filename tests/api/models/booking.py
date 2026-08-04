from pydantic import BaseModel


class BookingDates(BaseModel):
    checkin: str
    checkout: str


class Booking(BaseModel):
    bookingid: int
    roomid: int
    firstname: str
    lastname: str
    depositpaid: bool
    bookingdates: BookingDates


class BookingList(BaseModel):
    bookings: list[Booking]
