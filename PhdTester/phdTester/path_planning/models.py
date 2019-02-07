from typing import Iterable, List, Dict

from phdTester.default_models import AbstractStuffUnderTest, AbstractTestingEnvironment, AbstractTestContextMask, \
    AbstractStuffUnderTestMask, AbstractTestEnvironmentMask, AbstractTestingGlobalSettings, AbstractTestContext
from phdTester.ks001.ks001 import KS001
from phdTester.model_interfaces import ITestContext, ICsvRow, ITestContextMaskOption, IStuffUnderTestMask, \
    ITestEnvironmentMask
from phdTester.path_planning import constants as path_finding_constants
from phdTester.paths import ImportantPaths


class PathFindingPaths(ImportantPaths):

    def __init__(self, input_dir: str, output_dir: str, tmp_subdir: str, images_subdir: str, cwd_subdir: str, map_subdir: str, scenario_subdir: str, csv_subdir: str):
        ImportantPaths.__init__(self,
                                input_dir=input_dir,
                                output_dir=output_dir,
                                tmp_subdir=tmp_subdir,
                                cwd_subdir=cwd_subdir,
                                csv_subdir=csv_subdir,
                                image_subdir=images_subdir
                                )

        self.map_subdir = map_subdir
        self.scenario_subdir = scenario_subdir

    def get_perturbated_map_filename_template(self, test: "PathFindingTestContext") -> str:
        return self.generate_cwd_file(test.te.to_ks001())

    def get_map_absfilename(self, filename: str) -> str:
        return self.get_input(self.map_subdir, filename)

    def get_scenario_absfilename(self, filename: str) -> str:
        return self.get_input(self.scenario_subdir, filename)

    def get_csv_mainoutput_name_just_generated(self, test: ITestContext) -> str:
        ks = test.to_ks001() + KS001.get_from({"type": "mainOutput"})
        return self.generate_cwd_file(ks, extension="csv")

    def get_dynamicpathfindingtester_program_template(self, test: ITestContext) -> str:
        return self.generate_cwd_file(test.to_ks001())

    def get_csv_mainoutput_name(self, test: ITestContext) -> str:
        """

        :param test:
        :return: the absolute path of the CSV containing the performance timings
        """
        ks = test.to_ks001() + KS001.get_from({"type": "mainOutput"})
        return self.generate_csv_file(ks, extension='csv')

    def get_maps_per_query_of(self, tc: ITestContext) -> Iterable[str]:
        """
        get all the files inside CWD directory ending with "graph" compliant with the tc.te specification

        this is used because in perturbation kinds affecting a singular query (not the whole scenario) we temporary
        create perturbated map depending on the query. Then we need to remove therm (usually). This function allows
        us to get the list of them
        :param tc: the context involved
        :return:
        """
        image_dict = KS001()
        image_dict.add(i=0, dict=tc.te)

        for filename, ks001 in image_dict.get_phddictionaries_compliant_from_directory(
            index=0,
            directory=self.get_cwd_dir(),
            allowed_extensions=["graph"],
            alias_name_dict=tc.get_alias_name_dict()
        ):
            if ks001.has_key_in_dict(i=1, k="query"):
                yield self.get_cwd(filename)


class PathFindingTestContext(AbstractTestContext):

    def __init__(self, ut: "PathFindingStuffUnderTest", te: "PathFindingTestingEnvironment"):
        AbstractTestContext.__init__(self, ut, te)

    @property
    def ut(self) -> "PathFindingStuffUnderTest":
        return self._ut

    @property
    def te(self) -> "PathFindingTestingEnvironment":
        return self._te


class PathFindingStuffUnderTest(AbstractStuffUnderTest):

    def __init__(self, algorithm: str = None, heuristic: str = None, enable_upperbound: bool = None, enable_earlystop: bool = None, landmark_number: int = None, use_bound: bool = None, bound: float = None):
        AbstractStuffUnderTest.__init__(self)
        self.algorithm: str = algorithm
        self.heuristic: str = heuristic
        self.enable_upperbound: bool = enable_upperbound
        self.enable_earlystop: bool = enable_earlystop
        self.landmark_number: int = landmark_number
        self.use_bound: bool = use_bound
        self.bound: float = bound

    @property
    def key_alias(self) -> Dict[str, str]:
        return {
            "algorithm": "a",
            "heuristic": "h",
            "enable_upperbound": "eu",
            "enable_earlystop": "ee",
            "landmark_number": "ln",
            "use_bound": "ub",
            "bound": "b",
        }

    @property
    def value_alias(self) -> Dict[str, str]:
        return {}

    def get_label(self) -> str:
        val = []
        if self.algorithm in [path_finding_constants.ALG_ASTAR, path_finding_constants.ALG_WASTAR]:
            if self.algorithm == path_finding_constants.ALG_ASTAR:
                val.append("A*")
            elif self.algorithm == path_finding_constants.ALG_WASTAR:
                val.append("WA*")
            else:
                raise ValueError(f"invalid algorithm {self.algorithm}")

            # bound
            if self.use_bound and self.bound != 0.0:
                if self.algorithm == path_finding_constants.ALG_ASTAR:
                    val.append(f"B={self.bound:2.1f}")
                elif self.algorithm == path_finding_constants.ALG_WASTAR:
                    val.append(f"w={(1+ self.bound):2.1f}")
                else:
                    raise ValueError(f"invalid algorithm {self.algorithm}")

            # heuristic
            if self.heuristic in [path_finding_constants.HEU_CPD_CACHE, path_finding_constants.HEU_CPD_NO_CACHE]:
                if self.heuristic == path_finding_constants.HEU_CPD_CACHE:
                    val.append("cache")
                if self.enable_earlystop:
                    val.append("ES")
                if self.enable_upperbound:
                    val.append("UB")
            elif self.heuristic in [path_finding_constants.HEU_DIFFERENTIAL_HEURISTIC]:
                val.append(f"DH={self.landmark_number}")
            else:
                raise ValueError(f"invalid heuristic {self.heuristic}")
        elif self.algorithm == path_finding_constants.ALG_DIJKSTRA_EARLYSTOP:
            val.append("Dijkstra ES")
        else:
            raise ValueError(f"invalid algorithm {self.algorithm}")

        return ' '.join(val)


class PathFindingTestingEnvironment(AbstractTestingEnvironment):

    def __init__(self, map_filename: str = None, scenario_file: str = None, perturbation_kind: str = None, perturbation_mode: str = None, perturbation_range: str = None, perturbation_density: str = None, terrains_to_alter: str = None, sequence_length: str = None, area_radius: str = None, optional_path_ratio: str = None):
        AbstractTestingEnvironment.__init__(self)
        self.map_filename: str = map_filename
        self.scenario_file: str = scenario_file
        self.perturbation_kind: str = perturbation_kind
        self.perturbation_mode: str = perturbation_mode
        self.perturbation_range: str = perturbation_range
        self.perturbation_density: str = perturbation_density
        self.terrains_to_alter: str = terrains_to_alter
        self.sequence_length: str = sequence_length
        self.area_radius: str = area_radius
        self.optimal_path_ratio: str = optional_path_ratio

    @property
    def key_alias(self) -> Dict[str, str]:
        return {
            "map_filename": "mp",
            "scenario_file": "sf",
            "perturbation_kind": "pk",
            "perturbation_mode": "pm",
            "perturbation_range": "pr",
            "perturbation_density": "pd",
            "terrains_to_alter": "tta",
            "sequence_length": "sl",
            "area_radius": "ar",
            "optimal_path_ratio": "opr",
        }

    @property
    def value_alias(self) -> Dict[str, str]:
        return {}

    def get_order_key(self) -> str:
        return "_".join(map(lambda o: f"{o}={str(self.get_option(o))}", self.options()))

    def get_label(self) -> str:
        return ""


class PathFindingTestingGlobalSettings(AbstractTestingGlobalSettings):

    def __init__(self):
        AbstractTestingGlobalSettings.__init__(self)
        self.map_directory: str = None
        self.scenario_directory: str = None
        self.tmp_directory: str = None
        self.cwd_directory: str = None
        self.csv_directory: str = None
        self.image_directory: str = None
        self.debug: bool = None
        self.generate_images_only_for: List[str] = None
        self.generate_only_latex: bool = None
        self.ignore_unperturbated_paths: bool = None


class PathFindingCsvRow(ICsvRow):

    def __init__(self):
        ICsvRow.__init__(self)
        self.experiment_id: int = None
        self.us_time: int = None
        self.path_revised_cost: int = None
        self.path_original_cost: int = None
        self.path_step_size: int = None
        self.expanded_nodes: int = None
        self.heuristic_time: int = None
        self.has_original_path_perturbated: bool = None


class PathFindingTestContextMask(AbstractTestContextMask):

    def __init__(self, ut: "IStuffUnderTestMask", te: "ITestEnvironmentMask"):
        AbstractTestContextMask.__init__(self, ut=ut, te=te)

    @property
    def ut(self) -> "PathFindingStuffUnderTestMask":
        return self._ut

    @property
    def te(self) -> "PathFindingTestEnvironmentMask":
        return self._te


class PathFindingStuffUnderTestMask(AbstractStuffUnderTestMask):

    def __init__(self):
        AbstractStuffUnderTestMask.__init__(self)
        self.algorithm: ITestContextMaskOption = None
        self.heuristic: ITestContextMaskOption = None
        self.enable_upperbound: ITestContextMaskOption = None
        self.enable_earlystop: ITestContextMaskOption = None
        self.landmark_number: ITestContextMaskOption = None
        self.use_bound: ITestContextMaskOption = None
        self.bound: ITestContextMaskOption = None


class PathFindingTestEnvironmentMask(AbstractTestEnvironmentMask):

    def __init__(self):
        AbstractTestEnvironmentMask.__init__(self)
        self.map_filename: ITestContextMaskOption = None
        self.scenario_file: ITestContextMaskOption = None
        self.perturbation_kind: ITestContextMaskOption = None
        self.perturbation_mode: ITestContextMaskOption = None
        self.perturbation_range: ITestContextMaskOption = None
        self.perturbation_density: ITestContextMaskOption = None
        self.terrains_to_alter: ITestContextMaskOption = None
        self.sequence_length: ITestContextMaskOption = None
        self.area_radius: ITestContextMaskOption = None
        self.optimal_path_ratio: ITestContextMaskOption = None
