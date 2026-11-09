from datetime import date
import pytest
from app.services import valid_stay, nights_overlap


def test_checkout_is_not_occupied():
    assert not nights_overlap(date(2027, 3, 1), date(2027, 3, 3), date(2027, 3, 3), date(2027, 3, 5))


def test_one_shared_night_is_overlap():
    assert nights_overlap(date(2027, 3, 1), date(2027, 3, 4), date(2027, 3, 3), date(2027, 3, 5))


def test_valid_stay_max_30_nights():
    assert valid_stay(date(2027, 3, 1), date(2027, 3, 31))
    with pytest.raises(ValueError):
        valid_stay(date(2027, 3, 1), date(2027, 4, 1))
    with pytest.raises(ValueError):
        valid_stay(date(2027, 3, 1), date(2027, 3, 1))
