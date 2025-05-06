from .utils import Utils

def test_printc():
    utils = Utils()
    assert utils.printc(level="INFO", text="Hello", color="BLUE") == "[INFO] Hello"
