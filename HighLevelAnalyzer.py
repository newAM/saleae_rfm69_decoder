from typing import Iterable, Optional, Union
from saleae.analyzers import HighLevelAnalyzer, AnalyzerFrame

regs = {
    0x00: "Fifo",
    0x01: "OpMode",
    0x02: "DataMod",
    0x03: "BitrateMsb",
    0x04: "BitrateLsb",
    0x05: "FdevMsb",
    0x06: "FdevLsb",
    0x07: "FrfMsb",
    0x08: "FrfMid",
    0x09: "FrfLsb",
    0x10: "Version",
    0x11: "PaLevel",
    0x19: "RxBw",
    0x1A: "AfcBw",
    0x24: "RssiValue",
    0x25: "DioMapping1",
    0x27: "IrqFlags1",
    0x28: "IrqFlags2",
    0x2C: "PreambleMsb",
    0x2D: "PreambleLsb",
    0x2E: "SyncConfig",
    0x2F: "SyncValue1",
    0x37: "PacketConfig1",
    0x3C: "FifoThresh",
    0x3D: "PacketConfig2",
    0x3E: "AesKey1",
    0x4E: "Temp1",
    0x4F: "Temp2",
    0x5A: "TestPa1",
    0x5C: "TestPa2",
    0x6F: "TestDagc",
    0x55: "TestPa1Normal",
    0x5D: "TestPa1Boost",
    0x70: "TestPa2Normal",
    0x7C: "TestPa2Boost",
}


def get_reg_name(address: int) -> str:
    """ Get the register name by address. """
    try:
        return regs[address]
    except KeyError:
        return "INVALID"


class Hla(HighLevelAnalyzer):
    """ RFM69 High Level Analyzer. """

    result_types = {
        "address": {"format": "{{data.rw}} {{data.reg}}"},
        "read": {"format": "{{data.rw}} {{data.reg}} {{data.value}}"},
        "write": {"format": "{{data.rw}} {{data.reg}} {{data.value}}"},
    }

    def __init__(self):
        """ Initialize HLA. """

        # Previous frame type
        # https://support.saleae.com/extensions/analyzer-frame-types/spi-analyzer
        self._previous_type: str = ""
        # current address
        self._address: Optional[int] = None
        # current access type
        self._rw: str = ""

    def decode(
        self, frame: AnalyzerFrame
    ) -> Optional[Union[Iterable[AnalyzerFrame], AnalyzerFrame]]:
        """ Decode frames. """
        is_first_byte: bool = self._previous_type == "enable"
        self._previous_type: str = frame.type

        if frame.type != "result":
            return None

        mosi: bytes = frame.data["mosi"]
        miso: bytes = frame.data["miso"]

        if is_first_byte:
            try:
                self._address = mosi[0]
            except IndexError:
                return None

            self._rw = "Write" if self._address & 0x80 != 0 else "Read"

            # normalize the address, removing the write bit
            self._address &= 0x7F

            return AnalyzerFrame(
                "address",
                start_time=frame.start_time,
                end_time=frame.end_time,
                data={"reg": get_reg_name(self._address), "rw": self._rw},
            )
        else:
            if self._rw.lower() == "write":
                try:
                    byte = mosi[0]
                except IndexError:
                    return None
            else:
                try:
                    byte = miso[0]
                except IndexError:
                    return None

            ret = AnalyzerFrame(
                self._rw.lower(),
                start_time=frame.start_time,
                end_time=frame.end_time,
                data={
                    "reg": get_reg_name(self._address),
                    "rw": self._rw,
                    "value": f"0x{byte:02X}",
                },
            )

            self._address += 1
            self._address &= 0x7F
            return ret
