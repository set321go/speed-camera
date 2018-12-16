from datetime import datetime

import pytest
import config
from speedcam.storage import CSVStorageService
from speedcam.tracking.motion import TrackingBox


@pytest.fixture
def mock_config(mocker):
    config_mock = mocker.MagicMock(spec=config.config.Config)
    return config_mock


def test_given_valid_data_format_output(mock_config):
    mock_config.log_data_to_CSV = True
    mock_config.data_dir = 'dummy'
    mock_config.get_speed_units.return_value = 'kph'
    service = CSVStorageService(mock_config)

    now = datetime.now()
    box = TrackingBox(10, 10, 50, 50)
    result = service.format_data(now, 'csv_file.csv', 'R2L', 50.32, box)
    assert result == '"{}{}{}","{:0>2d}","{:0>2d}",50.32,"kph","csv_file.csv",10,10,50,50,2500,"R2L"'\
        .format(now.year, now.month, now.day, now.hour, now.minute)

