from typing import Optional
class MigrationPath:
    def __init__(self) -> None:
        self.paths: dict[int, MigrationPath] = {}




    def update_migration_path_details(self, path_id: int, **kwargs) -> None:
        pass
    def get_migration_path_details(self, path_id) -> dict:
        pass