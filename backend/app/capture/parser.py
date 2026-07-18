"""
Translates a raw scapy packet into the flat structure the rest of the
application works with. Keeping this isolated means the capture layer
and the API/service layers never need to import scapy directly.
"""
from __future__ import annotations

from typing import Any, Optional

from scapy.layers.inet import IP, TCP, UDP, ICMP
from scapy.layers.l2 import ARP
from scapy.packet import Packet as ScapyPacket

# Well-known ports used to guess the application-layer protocol for display.
_APP_PORT_MAP = {
    80: "HTTP",
    443: "HTTPS",
    53: "DNS",
    22: "SSH",
    21: "FTP",
    25: "SMTP",
    110: "POP3",
    143: "IMAP",
}

_TCP_FLAG_NAMES = {
    "F": "FIN",
    "S": "SYN",
    "R": "RST",
    "P": "PSH",
    "A": "ACK",
    "U": "URG",
    "E": "ECE",
    "C": "CWR",
}


def _guess_app_protocol(src_port: Optional[int], dst_port: Optional[int]) -> Optional[str]:
    for port in (src_port, dst_port):
        if port in _APP_PORT_MAP:
            return _APP_PORT_MAP[port]
    return None


def _decode_tcp_flags(flags_field) -> str:
    if not flags_field:
        return ""
    names = [_TCP_FLAG_NAMES.get(c, c) for c in str(flags_field)]
    return ",".join(names)


def parse_packet(pkt: ScapyPacket) -> Optional[dict[str, Any]]:
    """Return a flat dict describing the packet, or None if it should be
    ignored (protocols we don't care to show)."""

    length = len(pkt)

    if pkt.haslayer(ARP):
        arp = pkt[ARP]
        return {
            "src_ip": arp.psrc,
            "dst_ip": arp.pdst,
            "src_port": None,
            "dst_port": None,
            "protocol": "ARP",
            "app_protocol": None,
            "length": length,
            "ttl": None,
            "flags": "who-has" if arp.op == 1 else "is-at",
            "raw_summary": pkt.summary(),
        }

    if not pkt.haslayer(IP):
        return None

    ip_layer = pkt[IP]
    base = {
        "src_ip": ip_layer.src,
        "dst_ip": ip_layer.dst,
        "length": length,
        "ttl": ip_layer.ttl,
        "raw_summary": pkt.summary(),
    }

    if pkt.haslayer(TCP):
        tcp = pkt[TCP]
        base.update(
            src_port=int(tcp.sport),
            dst_port=int(tcp.dport),
            protocol="TCP",
            app_protocol=_guess_app_protocol(int(tcp.sport), int(tcp.dport)),
            flags=_decode_tcp_flags(tcp.flags),
        )
        return base

    if pkt.haslayer(UDP):
        udp = pkt[UDP]
        base.update(
            src_port=int(udp.sport),
            dst_port=int(udp.dport),
            protocol="UDP",
            app_protocol=_guess_app_protocol(int(udp.sport), int(udp.dport)),
            flags=None,
        )
        return base

    if pkt.haslayer(ICMP):
        icmp = pkt[ICMP]
        base.update(
            src_port=None,
            dst_port=None,
            protocol="ICMP",
            app_protocol=None,
            flags=f"type={icmp.type},code={icmp.code}",
        )
        return base

    base.update(src_port=None, dst_port=None, protocol="OTHER", app_protocol=None, flags=None)
    return base
