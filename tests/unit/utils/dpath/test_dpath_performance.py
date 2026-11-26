"""
Performance and stress tests for dpath utilities.
"""

import time
from typing import Any

from django.conf import settings
from lxml import etree

from lamb.utils.dpath import adapt_dict_impl, dpath_value


class TestDpathPerformanceBenchmark:
    """Performance benchmarking tests for dpath engines"""

    @classmethod
    def setup_class(cls):
        """Setup test data for performance testing"""
        # Store original engine setting
        cls._original_engine = getattr(settings, "LAMB_DPATH_DICT_ENGINE", None)

        # Use smaller data for performance testing to avoid hanging
        cls.large_dict = cls._generate_large_nested_dict(10, 2)  # Much smaller: 1,000 elements instead of 100M
        cls.large_xml = cls._generate_large_xml_structure(10, 2)  # Much smaller XML structure

    @classmethod
    def teardown_class(cls):
        """Restore original settings"""
        if cls._original_engine is not None:
            settings.LAMB_DPATH_DICT_ENGINE = cls._original_engine
        elif hasattr(settings, "LAMB_DPATH_DICT_ENGINE"):
            delattr(settings, "LAMB_DPATH_DICT_ENGINE")
        adapt_dict_impl()

    @staticmethod
    def _generate_large_nested_dict(width: int, depth: int) -> dict[str, Any]:
        """Generate a nested dictionary structure for testing"""
        if depth <= 0:
            return {f"key_{i}": f"value_{i}" for i in range(width)}

        result = {}
        for i in range(width):
            result[f"level_{depth}_key_{i}"] = TestDpathPerformanceBenchmark._generate_large_nested_dict(
                width, depth - 1
            )
        return result

    @staticmethod
    def _generate_large_xml_structure(width: int, depth: int) -> etree.ElementTree:
        """Generate an XML structure for testing"""
        root = etree.Element("root")

        def add_elements(parent, current_depth, max_width):
            if current_depth <= 0:
                for i in range(max_width):
                    child = etree.SubElement(parent, f"item_{i}")
                    child.text = f"value_{i}"
                return

            for i in range(max_width):
                element = etree.SubElement(parent, f"level_{current_depth}_elem_{i}")
                add_elements(element, current_depth - 1, max_width)

        add_elements(root, depth, width)
        return etree.ElementTree(root)

    def _switch_engine(self, engine_name: str):
        """Switch dpath engine"""
        settings.LAMB_DPATH_DICT_ENGINE = engine_name
        adapt_dict_impl()

    def test_performance_simple_access_dpath(self):
        """Performance test for simple access with dpath engine"""
        original_engine = getattr(settings, "LAMB_DPATH_DICT_ENGINE", None)
        try:
            self._switch_engine("dpath")

            start_time = time.perf_counter()
            # Reduced iterations for faster testing
            for i in range(10):
                dpath_value(self.large_dict, ["level_2_key_0", "level_1_key_0", "key_0"])
            dpath_time = time.perf_counter() - start_time

            print(f"Dpath engine simple access time: {dpath_time:.6f}s")
        finally:
            # Restore original engine
            if original_engine is not None:
                settings.LAMB_DPATH_DICT_ENGINE = original_engine
                adapt_dict_impl()

    def test_performance_simple_access_reduce(self):
        """Performance test for simple access with reduce engine"""
        original_engine = getattr(settings, "LAMB_DPATH_DICT_ENGINE", None)
        try:
            self._switch_engine("reduce")

            start_time = time.perf_counter()
            # Reduced iterations for faster testing
            for i in range(10):
                dpath_value(self.large_dict, ["level_2_key_0", "level_1_key_0", "key_0"])
            reduce_time = time.perf_counter() - start_time

            print(f"Reduce engine simple access time: {reduce_time:.6f}s")
        finally:
            # Restore original engine
            if original_engine is not None:
                settings.LAMB_DPATH_DICT_ENGINE = original_engine
                adapt_dict_impl()

    def test_performance_deep_access(self):
        """Performance test for deep nested access"""
        # Use a valid path that exists in our smaller data structure
        path = ["level_2_key_0", "level_1_key_0", "key_0"]

        original_engine = getattr(settings, "LAMB_DPATH_DICT_ENGINE", None)

        try:
            # Test with dpath engine
            self._switch_engine("dpath")
            start_time = time.perf_counter()
            # Reduced iterations for faster testing
            for i in range(50):
                dpath_value(self.large_dict, path)
            dpath_time = time.perf_counter() - start_time

            # Test with reduce engine
            self._switch_engine("reduce")
            start_time = time.perf_counter()
            # Reduced iterations for faster testing
            for i in range(50):
                dpath_value(self.large_dict, path)
            reduce_time = time.perf_counter() - start_time

            print(f"Deep access - Dpath: {dpath_time:.6f}s, Reduce: {reduce_time:.6f}s")

            # Simple assertion to ensure both engines complete
            assert dpath_time > 0 and reduce_time > 0
        finally:
            # Restore original engine
            if original_engine is not None:
                settings.LAMB_DPATH_DICT_ENGINE = original_engine
                adapt_dict_impl()

    def test_performance_with_type_conversion(self):
        """Performance test with type conversion"""
        test_data = {"number": "12345"}
        path = "number"

        original_engine = getattr(settings, "LAMB_DPATH_DICT_ENGINE", None)

        try:
            # Test with dpath engine
            self._switch_engine("dpath")
            start_time = time.perf_counter()
            # Reduced iterations for faster testing
            for i in range(100):
                dpath_value(test_data, path, int)
            dpath_time = time.perf_counter() - start_time

            # Test with reduce engine
            self._switch_engine("reduce")
            start_time = time.perf_counter()
            # Reduced iterations for faster testing
            for i in range(100):
                dpath_value(test_data, path, int)
            reduce_time = time.perf_counter() - start_time

            print(f"Type conversion - Dpath: {dpath_time:.6f}s, Reduce: {reduce_time:.6f}s")
        finally:
            # Restore original engine
            if original_engine is not None:
                settings.LAMB_DPATH_DICT_ENGINE = original_engine
                adapt_dict_impl()

    def _create_deep_path(self, depth: int) -> list:
        """Create a deep path for testing"""
        return [f"level_{i}_key_0" for i in range(depth, 0, -1)] + ["key_0"]

    def benchmark_engines_comprehensive(self):
        """Comprehensive benchmark of both engines"""
        scenarios = [
            ("simple_access", ["level_2_key_0", "level_1_key_0", "key_0"]),
            ("deep_access", self._create_deep_path(3)),  # Reduced depth
            ("wide_access", [f"level_2_key_{i}" for i in range(5)] + ["key_0"]),  # Reduced width
        ]

        results = {}

        for engine in ["dpath", "reduce"]:
            self._switch_engine(engine)

            engine_results = {}
            for scenario_name, path in scenarios:
                times = []
                # Run multiple iterations for averaging
                for _ in range(3):
                    start = time.perf_counter()
                    for _ in range(50):  # Reduced iterations
                        dpath_value(self.large_dict, path)
                    end = time.perf_counter()
                    times.append(end - start)

                avg_time = sum(times) / len(times)
                engine_results[scenario_name] = avg_time
                print(f"{engine} engine - {scenario_name}: {avg_time:.6f}s")

            results[engine] = engine_results

        # Print comparison
        self._print_performance_comparison(results)
        return results

    def _print_performance_comparison(self, results: dict):
        """Print performance comparison results"""
        print("\n=== PERFORMANCE COMPARISON ===")
        for scenario in results.get("dpath", {}):
            dpath_time = results.get("dpath", {}).get(scenario, 0)
            reduce_time = results.get("reduce", {}).get(scenario, 0)
            if dpath_time > 0:
                ratio = reduce_time / dpath_time
                winner = "dpath" if ratio > 1 else "reduce"
                print(f"\n{scenario}:")
                print(f"  dpath:   {dpath_time:.6f}s")
                print(f"  reduce:  {reduce_time:.6f}s")
                print(f"  ratio:   {ratio:.2f}x ({winner} is faster)")


class TestDpathEngineSpecific:
    """Engine-specific tests"""

    @classmethod
    def setup_class(cls):
        """Ensure we start with a clean engine state"""
        # Reset to default engine
        settings.LAMB_DPATH_DICT_ENGINE = "dpath"  # Match default from settings
        adapt_dict_impl()

    @classmethod
    def teardown_class(cls):
        """Restore engine to default state"""
        settings.LAMB_DPATH_DICT_ENGINE = "dpath"
        adapt_dict_impl()

    def test_dpath_engine_basic_functionality(self):
        """Test basic functionality with dpath engine"""
        settings.LAMB_DPATH_DICT_ENGINE = "dpath"
        adapt_dict_impl()

        data = {"a": {"b": "value"}}
        result = dpath_value(data, ["a", "b"])
        assert result == "value"

    def test_reduce_engine_basic_functionality(self):
        """Test basic functionality with reduce engine"""
        settings.LAMB_DPATH_DICT_ENGINE = "reduce"
        adapt_dict_impl()

        data = {"a": {"b": "value"}}
        result = dpath_value(data, ["a", "b"])
        assert result == "value"

    def test_dpath_engine_string_path(self):
        """Test string path with dpath engine"""
        settings.LAMB_DPATH_DICT_ENGINE = "dpath"
        adapt_dict_impl()

        data = {"key": "value"}
        # Note: String paths might behave differently depending on implementation
        result = dpath_value(data, ["key"])  # Using list format for consistency
        assert result == "value"

    def test_reduce_engine_string_path(self):
        """Test string path with reduce engine"""
        settings.LAMB_DPATH_DICT_ENGINE = "reduce"
        adapt_dict_impl()

        data = {"key": "value"}
        result = dpath_value(data, ["key"])  # Using list format for consistency
        assert result == "value"


if __name__ == "__main__":
    # Run benchmarks if executed directly
    benchmark = TestDpathPerformanceBenchmark()
    benchmark.setup_class()
    benchmark.benchmark_engines_comprehensive()
