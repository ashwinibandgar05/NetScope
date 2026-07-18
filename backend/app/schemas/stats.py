from typing import List

from pydantic import BaseModel


class ProtocolCount(BaseModel):
    protocol: str
    count: int


class IpCount(BaseModel):
    ip: str
    count: int


class PortCount(BaseModel):
    port: int
    count: int


class DashboardStats(BaseModel):
    total_packets: int
    tcp_packets: int
    udp_packets: int
    icmp_packets: int
    unknown_packets: int
    packets_per_second: float
    bandwidth_bytes_per_second: float


class TrafficStats(BaseModel):
    protocol_distribution: List[ProtocolCount]
    top_source_ips: List[IpCount]
    top_destination_ips: List[IpCount]
    most_active_ports: List[PortCount]
    total_bandwidth_bytes: int


class TimeSeriesPoint(BaseModel):
    label: str
    value: float


class ThroughputSeries(BaseModel):
    points: List[TimeSeriesPoint]
