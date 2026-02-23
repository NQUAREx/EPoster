from models import AppSettings


def test_base_background_id_parses_as_positive_int():
    settings = AppSettings.from_dict({"base_background_id": "3"})
    assert settings.base_background_id == 3


def test_base_background_id_falls_back_to_one_on_invalid_values():
    settings_zero = AppSettings.from_dict({"base_background_id": 0})
    settings_bad = AppSettings.from_dict({"base_background_id": "bad"})
    assert settings_zero.base_background_id == 1
    assert settings_bad.base_background_id == 1



def test_sleep_mode_flag_is_parsed_from_settings():
    settings = AppSettings.from_dict({"sleep_mode": True})
    assert settings.sleep_mode is True


def test_sleep_mode_defaults_to_false():
    settings = AppSettings.from_dict({})
    assert settings.sleep_mode is False
