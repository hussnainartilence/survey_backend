import json
from dataclasses import dataclass, field

from .. import settings

from .models import *


@dataclass
class FormMigrationDataBuilder:
    data_dir = settings.BASE_DIR
    

    def save(self):
        migration_data_dir = self.data_dir / "migration_tools/data"
        with open(migration_data_dir / "wis_attribute_prompt.json", "w") as f:
            json.dump(
                [row.dict() for row in self.wis_attribute_prompt],
                f,
                default=datetime.isoformat,
                indent=2,
            )
        with open(migration_data_dir / "wis_choice.json", "w") as f:
            json.dump(
                [row.dict() for row in self.wis_choice],
                f,
                default=datetime.isoformat,
                indent=2,
            )
        with open(migration_data_dir / "wis_column_def.json", "w") as f:
            json.dump(
                [row.dict() for row in self.wis_column_def],
                f,
                default=datetime.isoformat,
                indent=2,
            )
        with open(migration_data_dir / "wis_column_view.json", "w") as f:
            json.dump(
                [row.dict() for row in self.wis_column_view],
                f,
                default=datetime.isoformat,
                indent=2,
            )
        with open(migration_data_dir / "wis_table_def.json", "w") as f:
            json.dump(
                [row.dict() for row in self.wis_table_def],
                f,
                default=datetime.isoformat,
                indent=2,
            )
        with open(migration_data_dir / "wis_table_view.json", "w") as f:
            json.dump(
                [row.dict() for row in self.wis_table_view],
                f,
                default=datetime.isoformat,
                indent=2,
            )
