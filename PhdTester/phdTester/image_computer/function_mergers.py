from typing import Dict

from phdTester.model_interfaces import AbstractDictionaryMergerTemplate


class MergingNotAllowedMerger(AbstractDictionaryMergerTemplate):

    def __init__(self):
        AbstractDictionaryMergerTemplate.__init__(self)

    def handle_key_missing_in_old(self, building_dict: Dict[float, float], new_k: float, new_value: float):
        building_dict[new_k] = new_value

    def handle_key_missing_in_new(self, building_dict: Dict[float, float], removed_k: float, old_value: float):
        raise ValueError(f"the key {removed_k} was present in the old dictionary but it is not present in the new one!")

    def handle_key_merging(self, building_dict: Dict[float, float], k: float, old_value: float, new_value: float):
        if old_value != new_value:
            raise ValueError(f"""we forbid the merging of dictionaries!
                key={k}
                old_value={old_value}
                new_value={new_value}
            """)
