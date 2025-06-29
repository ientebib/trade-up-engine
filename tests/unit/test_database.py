import pytest
from unittest.mock import patch

from data import database


def test_get_car_by_id_uses_single_loader():
    car_data = {"car_id": "ABC123", "model": "Test"}
    with patch("data.database.data_loader.load_single_car_from_redshift", return_value=car_data) as mock_loader, \
         patch("data.database.get_all_inventory") as mock_get_all:
        result = database.get_car_by_id("ABC123")
        mock_loader.assert_called_once_with("ABC123")
        mock_get_all.assert_not_called()
        assert result == car_data
