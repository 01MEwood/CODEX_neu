from dataclasses import dataclass


@dataclass(frozen=True)
class SvsInput:
    total_costs: float
    productive_hours_per_employee: float
    employee_count: int
    risk_buffer_pct: float = 0.0
    regional_avg: float = 0.0


@dataclass(frozen=True)
class SvsResult:
    base_svs: float
    final_svs: float
    risk_buffer_amount: float
    benchmark_delta: float | None
    benchmark_trend: str | None


def _benchmark_trend(delta: float | None) -> str | None:
    if delta is None:
        return None
    if delta > 0:
        return "über Benchmark"
    if delta < 0:
        return "unter Benchmark"
    return "auf Benchmark"


def compute_svs(data: SvsInput) -> SvsResult:
    if data.total_costs < 0:
        raise ValueError("Gesamtkosten dürfen nicht negativ sein.")
    if data.productive_hours_per_employee <= 0:
        raise ValueError("Produktive Stunden je Mitarbeiter müssen > 0 sein.")
    if data.employee_count <= 0:
        raise ValueError("Mitarbeiteranzahl muss > 0 sein.")
    if data.risk_buffer_pct < 0:
        raise ValueError("Risikopuffer darf nicht negativ sein.")

    base = data.total_costs / (data.productive_hours_per_employee * data.employee_count)
    final = base * (1 + data.risk_buffer_pct / 100.0)
    risk_amount = final - base

    rounded_final = round(final, 2)
    delta = round(rounded_final - data.regional_avg, 2) if data.regional_avg > 0 else None

    return SvsResult(
        base_svs=round(base, 2),
        final_svs=rounded_final,
        risk_buffer_amount=round(risk_amount, 2),
        benchmark_delta=delta,
        benchmark_trend=_benchmark_trend(delta),
    )
