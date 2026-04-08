import unittest

from plusso_app.svs import SvsInput, compute_svs


class ComputeSvsTests(unittest.TestCase):
    def test_compute_with_risk_and_benchmark(self):
        result = compute_svs(
            SvsInput(
                total_costs=120000,
                productive_hours_per_employee=1600,
                employee_count=4,
                risk_buffer_pct=5,
                regional_avg=18,
            )
        )
        self.assertEqual(result.base_svs, 18.75)
        self.assertEqual(result.final_svs, 19.69)
        self.assertEqual(result.risk_buffer_amount, 0.94)
        self.assertEqual(result.benchmark_delta, 1.69)
        self.assertEqual(result.benchmark_trend, "über Benchmark")

    def test_negative_costs_invalid(self):
        with self.assertRaises(ValueError):
            compute_svs(SvsInput(total_costs=-1, productive_hours_per_employee=1000, employee_count=2))


if __name__ == "__main__":
    unittest.main()
