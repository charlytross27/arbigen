"""The exported-data notebook runs without Arbigen's backend or external services."""

import json
import os
import subprocess
import sys
from pathlib import Path


NOTEBOOK = Path(__file__).resolve().parents[2] / "notebooks" / "arbigen_ciencia_de_datos.ipynb"


def test_notebook_runs_from_an_isolated_directory_with_only_exported_json(tmp_path: Path) -> None:
    dataset = tmp_path / "arbigen-dataset-standalone.json"
    dataset.write_text(json.dumps({
        "country": "MX",
        "snapshot": {
            "items": [{
                "id": "MLM1", "title": "Producto de prueba", "price": "150", "currency": "MXN",
                "permalink": None, "image_url": None,
                "signals": {"free_shipping": True, "sold_quantity": 12},
            }],
            "reported_total_results": 991,
        },
        "trends": [],
    }), encoding="utf-8")
    script = """
import json
import sys
from pathlib import Path

notebook = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
namespace = {'__name__': '__main__'}
for index, cell in enumerate(notebook['cells']):
    if cell['cell_type'] == 'code':
        exec(compile(''.join(cell['source']), f'cell {index}', 'exec'), namespace)
assert namespace['quality'].included_count == 1
assert namespace['coverage']['sold_quantity'] == 1
assert namespace['score_report'].status == 'incomplete'
assert not any(name == 'app' or name.startswith('app.') for name in sys.modules)
"""
    env = os.environ.copy()
    env["ARBIGEN_DATASET_PATH"] = str(dataset)
    env.pop("ARBIGEN_SCENARIO_PATH", None)
    result = subprocess.run(
        [sys.executable, "-I", "-c", script, str(NOTEBOOK)],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stderr
