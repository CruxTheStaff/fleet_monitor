import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List


class DataManager:
    def __init__(self):
        self.data_dir = Path("data")
        self.data_dir.mkdir(exist_ok=True)

        # Βασικά αρχεία δεδομένων
        self.voyages_file = self.data_dir / "voyages.json"
        self.maintenance_file = self.data_dir / "maintenance.json"
        self.vessels_file = self.data_dir / "vessels.json"

    def save_voyages(self, data: List[Dict[str, Any]]) -> None:
        """Αποθήκευση δεδομένων ταξιδιών"""
        self._save_to_json(self.voyages_file, data)

    def save_maintenance(self, data: List[Dict[str, Any]]) -> None:
        """Αποθήκευση δεδομένων συντήρησης"""
        self._save_to_json(self.maintenance_file, data)

    def save_vessels(self, data: List[Dict[str, Any]]) -> None:
        """Αποθήκευση δεδομένων πλοίων"""
        self._save_to_json(self.vessels_file, data)

    def load_voyages(self) -> List[Dict[str, Any]]:
        """Φόρτωση δεδομένων ταξιδιών"""
        return self._load_from_json(self.voyages_file)

    def load_maintenance(self) -> List[Dict[str, Any]]:
        """Φόρτωση δεδομένων συντήρησης"""
        return self._load_from_json(self.maintenance_file)

    def load_vessels(self) -> List[Dict[str, Any]]:
        """Φόρτωση δεδομένων πλοίων"""
        return self._load_from_json(self.vessels_file)

    def _save_to_json(self, file_path: Path, data: Any) -> None:
        """Αποθήκευση δεδομένων σε JSON αρχείο"""
        try:
            # Μετατροπή datetime objects σε string
            if isinstance(data, list):
                data = [{k: v.isoformat() if isinstance(v, datetime) else v
                         for k, v in item.items()} for item in data]

            with file_path.open('w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving data to {file_path}: {str(e)}")

    def _load_from_json(self, file_path: Path) -> List[Dict[str, Any]]:
        """Φόρτωση δεδομένων από JSON αρχείο"""
        try:
            if not file_path.exists():
                return []

            with file_path.open('r', encoding='utf-8') as f:
                data = json.load(f)

            # Μετατροπή string σε datetime objects
            if isinstance(data, list):
                for item in data:
                    for key in item:
                        if isinstance(item[key], str) and 'date' in key.lower():
                            try:
                                item[key] = datetime.fromisoformat(item[key])
                            except ValueError:
                                pass
            return data
        except Exception as e:
            print(f"Error loading data from {file_path}: {str(e)}")
            return []

    def backup_data(self) -> None:
        """Δημιουργία backup των δεδομένων"""
        backup_dir = self.data_dir / "backups"
        backup_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        for file in [self.voyages_file, self.maintenance_file, self.vessels_file]:
            if file.exists():
                backup_file = backup_dir / f"{file.stem}_{timestamp}.json"
                with file.open('r', encoding='utf-8') as src:
                    with backup_file.open('w', encoding='utf-8') as dst:
                        dst.write(src.read())