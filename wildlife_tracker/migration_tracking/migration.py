from typing import Any, List, Optional
from migration_path import MigrationPath
from habitat_management.habitat import Habitat

class Migration:
    def __init__(self,
            path_id: int,
            current_date: str,
            current_location: str,
            species: str,
            start_date: str,
            start_location: Habitat,
            status: str,
            destination: Habitat,
            migration_id: int,
            migration_path: MigrationPath,
            duration: Optional[int] = None,
            animals: Optional[List[int]] = None) -> None:
        self.path_id = path_id
        self.current_date = current_date
        self.current_location = current_location
        self.species = species
        self.start_date=start_date
        self.start_location=start_location
        self.status=status
        self.status="Scheduled"
        self.destination=destination
        self.migration_id=migration_id
        self.migration_path=migration_path
        self.duration=duration
        self.animals = animals or []
        
        # this is Pythonic for
        # if animals is not None:
        #   self.animals = animals
        # else:
        #   self.animals = []


    def update_migration_details(self, migration_id: int, **kwargs: Any) -> None:
        pass



    def get_migration_details(self, migration_id: int) -> dict[str, Any]:
        pass

