from .utils import Config

def test_config():
    config = Config(pc_ip="0.0.0.0", pc_username="admin", pc_password="nutanix/4u")
    assert isinstance(config, Config)
