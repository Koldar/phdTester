import logging
import logging
import os
import re
import shutil
import subprocess
import time
from typing import Dict, Any, List, Tuple

from phdTester import commons, masks
from phdTester.common_types import PercentageInt, IntList, Bool, Int, Float, Str
from phdTester.commons import run_process
from phdTester.default_models import SimpleTestContextRepo
from phdTester.exceptions import ValueToIgnoreError
from phdTester.image_computer import aggregators, curves_changers
from phdTester.ks001.ks001 import KS001
from phdTester.model_interfaces import ITestingEnvironment, IUnderTesting, ITestContextRepo, \
    ITestContextMask, IStuffUnderTestMask, ITestEnvironmentMask
from phdTester.options_builder import OptionGraph, OptionBuilder
from phdTester.path_planning import constants
from phdTester.path_planning.constants import *
from phdTester.path_planning.models import PathFindingStuffUnderTest, PathFindingTestingEnvironment, PathFindingPaths, \
    PathFindingTestContext, PathFindingTestingGlobalSettings, PathFindingCsvRow, PathFindingTestContextMask, \
    PathFindingStuffUnderTestMask, PathFindingTestEnvironmentMask
from phdTester.report_generator.latex_visitor import LatexVisitor
from phdTester.report_generator.nodes import LatexDocument, LatexSection, LatexText, LatexUnorderedList, \
    LatexSubSection, LatexSimpleImage, LatexSubSubSection, LatexParagraph
from phdTester.specific_research_field import AbstractSpecificResearchFieldFactory, IgnoreCSVRowError


class PathFindingResearchField(AbstractSpecificResearchFieldFactory):

    def __init__(self):
        AbstractSpecificResearchFieldFactory.__init__(self)
        self.__previous_test_context_tested: "PathFindingTestContext" = None
        """
        the test context we have just testedin the previous test performed
        """

    def generate_environment(self) -> "ITestingEnvironment":
        result = PathFindingTestingEnvironment()
        return result

    def generate_under_testing(self) -> "IUnderTesting":
        result = PathFindingStuffUnderTest()
        return result

    def generate_test_global_settings(self) -> "PathFindingTestingGlobalSettings":
        return PathFindingTestingGlobalSettings()

    def generate_test_context(self, ut: PathFindingStuffUnderTest = None, te: PathFindingTestingEnvironment = None) -> "PathFindingTestContext":
        if ut is None:
            ut = self.generate_under_testing()
        if te is None:
            te = self.generate_environment()
        return PathFindingTestContext(ut, te)

    def generate_stuff_under_test_mask(self) -> "IStuffUnderTestMask":
        return PathFindingStuffUnderTestMask()

    def generate_test_environment_mask(self) -> "ITestEnvironmentMask":
        return PathFindingTestEnvironmentMask()

    def generate_test_context_mask(self) -> "PathFindingTestContextMask":
        result = PathFindingTestContextMask(
            ut=self.generate_stuff_under_test_mask(),
            te=self.generate_test_environment_mask()
        )
        return result

    def generate_test_context_repo(self, paths: "PathFindingTestContext", settings: "PathFindingTestingGlobalSettings") -> "SimpleTestContextRepo":
        return SimpleTestContextRepo()

    def generate_option_graph(self) -> OptionGraph:
        return OptionBuilder(

        ).add_environment_value(
            name="map_filename",
            option_type=Str,
            ahelp="List of files where it is contained the map",
        ).add_environment_value(
            name="scenario_file",
            option_type=Str,
            ahelp="""List of files where are contained several queries. 
                        Each scenario has the same position of the related file with map_filename""",

        ).add_under_testing_multiplexer(
            name="algorithm",
            possible_values=[ALG_ASTAR, ALG_DIJKSTRA_EARLYSTOP, ALG_WASTAR],
            ahelp="""python list of the algorithm to use to test. Either DIJKSTRA_EARLYSTOP or A*. If yu 
                                            choose A*, you need to specify -H option as well""",
        ).add_environment_multiplexer(
            name="perturbation_kind",
            possible_values=[
                KIND_PATH_RANDOM_ON_OPTIMAL,
                KIND_RANDOM,
                KIND_RANDOM_OPTIMAL,
                KIND_RANDOM_TERRAIN,
                KIND_RATIO_AREA,
                KIND_RATIO_PATH],
            ahelp="""Python code convertable in string containing types of perturbations you want for PER_MAP type.
                         See MapPerturbator --map_perturbation""",
        ).add_under_testing_multiplexer(
            name="heuristic",
            possible_values=[HEU_CPD_CACHE, HEU_CPD_NO_CACHE, HEU_DIFFERENTIAL_HEURISTIC],
            ahelp="python list of heuristics to use.",
        ).add_under_testing_value(
            name="enable_upperbound",
            option_type=Bool,
            ahelp="",
        ).add_under_testing_value(
            name="enable_earlystop",
            option_type=Bool,
            ahelp=""
        ).add_under_testing_value(
            name="landmark_number",
            option_type=Int,
            ahelp="""Python list of number of landmarks. Used only in DIFFERENTIAL_HEURISTIC heuristic""",
        ).add_under_testing_value(
            name="use_bound",
            option_type=Bool,
            ahelp="""Python list of whether the algorithm should have be switched to bounded mode"""
        ).add_under_testing_value(
            name="bound",
            option_type=Float,
            ahelp="""Python list of the bounds to use for the bounded algorithms"""
        ).add_environment_multiplexer(
            name="perturbation_mode",
            possible_values=[MODE_ADD, MODE_ASSIGN, MODE_TIMES],
            ahelp=""
        ).add_environment_value(
            name="perturbation_range",
            option_type=Str,
            ahelp="",
        ).add_environment_value(
            name="perturbation_density",
            option_type=PercentageInt,
            ahelp=""
        ).add_environment_value(
            name="terrains_to_alter",
            option_type=Int,
            ahelp="""List of lists containing the terrains to alter"""
        ).add_environment_value(
            name="sequence_length",
            option_type=Str,
            ahelp="""Python list of ranges of lengths. Used only for PATH_RANDOM_ON_OPTIMAL"""
        ).add_environment_value(
            name="area_radius",
            option_type=Str,
            ahelp="""Python list fo ranges of radius area. Used only for RANDOM_ON_AREA"""
        ).add_environment_value(
            name="optimal_path_ratio",
            option_type=Str,
            ahelp="""Python list of ratios. Used only for RATIO_ON_OPTIMAL_PATH"""
        ).add_settings_value(
            name="map_directory",
            option_type=Str,
            ahelp=""
        ).add_settings_value(
            name="scenario_directory",
            option_type=Str,
            ahelp=""
        ).add_settings_value(
            name="cwd_directory",
            option_type=Str,
            ahelp=""
        ).add_settings_value(
            name="csv_directory",
            option_type=Str,
            ahelp=""
        ).add_settings_value(
            name="image_directory",
            option_type=Str,
            ahelp="",
        ).add_settings_value(
            name="tmp_directory",
            option_type=Str,
            ahelp="",
        ).add_settings_flag(
            name="debug",
            ahelp="""
                    If present, we will generate images representing, per each query, the expanded nodes each algorithm has performed.
                    """
        ).add_settings_value(
            name="generate_images_only_for",
            option_type=IntList,
            default="[]",
            ahelp="""list of queries we need to generate image on"""
        ).add_settings_flag(
            name="generate_only_latex",
            ahelp=""
        ).add_settings_flag(
            name="ignore_unperturbated_paths",
            ahelp="""
            If this flag is enabled, the tester will generate images where we consider only paths 
            which have been perturbated at least once. This should make the problem much more challenging
            """
        ).option_can_be_used_only_when_other_string_satisfy(
            "scenario_file",
            "map_filename",
            condition=lambda s, m: f"{m}.scen" == s
        ).option_value_allows_other_option(
            "perturbation_kind",
            [KIND_RANDOM, KIND_PATH_RANDOM_ON_OPTIMAL, KIND_RANDOM_OPTIMAL, KIND_RANDOM_TERRAIN, KIND_RATIO_AREA, KIND_RATIO_PATH],
            "perturbation_mode",

        ).option_value_allows_other_option(
            "algorithm", [ALG_ASTAR, ALG_WASTAR], "heuristic"
        ).option_value_allows_other_option(
            "heuristic", [HEU_CPD_NO_CACHE, HEU_CPD_CACHE], "enable_upperbound"
        ).option_value_allows_other_option(
            "heuristic", [HEU_CPD_NO_CACHE, HEU_CPD_CACHE], "enable_earlystop"
        ).option_value_allows_other_option(
            "heuristic", [HEU_DIFFERENTIAL_HEURISTIC], "landmark_number"
        ).option_value_allows_other_option(
            "use_bound", [True], "bound",
        ).option_value_allows_other_option(
            "perturbation_kind",
            [KIND_RANDOM_TERRAIN, KIND_RANDOM, KIND_RANDOM_OPTIMAL, KIND_PATH_RANDOM_ON_OPTIMAL, KIND_RATIO_PATH, KIND_RATIO_AREA],
            "perturbation_range"
        ).option_value_allows_other_option(
            "perturbation_kind", [KIND_PATH_RANDOM_ON_OPTIMAL, KIND_RANDOM_OPTIMAL, KIND_RANDOM], "perturbation_density"
        ).option_value_allows_other_option(
            "perturbation_kind", [KIND_RANDOM_TERRAIN], "terrains_to_alter"
        ).option_value_allows_other_option(
            "perturbation_kind", [KIND_RATIO_PATH, KIND_PATH_RANDOM_ON_OPTIMAL], "sequence_length"
        ).option_value_allows_other_option(
            "perturbation_kind", [KIND_RATIO_AREA], "area_radius"
        ).option_value_allows_other_option(
            "perturbation_kind", [KIND_RATIO_PATH, KIND_RATIO_AREA], "optimal_path_ratio"
        ).get_option_graph()

    def generate_paths(self, settings: PathFindingTestingGlobalSettings) -> PathFindingPaths:
        return PathFindingPaths(
            input_dir=os.path.curdir,
            output_dir="build",
            tmp_subdir=settings.tmp_directory,
            csv_subdir=settings.csv_directory,
            scenario_subdir=settings.scenario_directory,
            map_subdir=settings.map_directory,
            images_subdir=settings.image_directory,
            cwd_subdir=settings.cwd_directory
        )

    def generate_output_directory_structure(self, paths: PathFindingPaths, settings: PathFindingTestingGlobalSettings):
        pass

    def generate_plots(self, paths: PathFindingPaths, settings: PathFindingTestingGlobalSettings, under_test_values: Dict[str, List[Any]], test_environment_values: Dict[str, List[Any]]):

        def get_query_id(tc: "PathFindingTestContext", csv_name: str, index: int, csv_row: PathFindingCsvRow):
            if settings.ignore_unperturbated_paths and csv_row.path_original_cost == csv_row.path_revised_cost:
                raise IgnoreCSVRowError()
            return csv_row.experiment_id

        def get_heuristic_ratio(tc: "PathFindingTestContext", csv_name: str, index: int, csv_row: PathFindingCsvRow):
            if settings.ignore_unperturbated_paths and csv_row.path_original_cost == csv_row.path_revised_cost:
                raise IgnoreCSVRowError()
            if tc.ut.algorithm == constants.ALG_DIJKSTRA_EARLYSTOP:
                # Dijkstra does not have heuristic
                return float(0)
            else:
                return float((csv_row.heuristic_time + 0.0)/csv_row.us_time)

        def get_expanded_nodes(tc: "PathFindingTestContext", csv_name: str, index: int, csv_row: PathFindingCsvRow):
            if settings.ignore_unperturbated_paths and csv_row.path_original_cost == csv_row.path_revised_cost:
                raise IgnoreCSVRowError()
            return csv_row.expanded_nodes

        def get_us_time(tc: "PathFindingTestContext", csv_name: str, index: int, csv_row: PathFindingCsvRow):
            if settings.ignore_unperturbated_paths and csv_row.path_original_cost == csv_row.path_revised_cost:
                raise IgnoreCSVRowError()
            return csv_row.us_time

        def get_original_path_length(tc: "PathFindingTestContext", csv_name: str, index: int, csv_row: PathFindingCsvRow):
            if settings.ignore_unperturbated_paths and csv_row.path_original_cost == csv_row.path_revised_cost:
                raise IgnoreCSVRowError()
            return csv_row.path_original_cost

        def get_is_perturbated_path(tc: "PathFindingTestContext", csv_name: str, index: int, csv_row: PathFindingCsvRow):
            if csv_row.path_revised_cost != csv_row.path_original_cost:
                return 1
            else:
                return 0

        def get_density(tc: "PathFindingTestContext", csv_name: str, index: int, csv_row: PathFindingCsvRow):
            if settings.ignore_unperturbated_paths and csv_row.path_original_cost == csv_row.path_revised_cost:
                raise IgnoreCSVRowError()
            if isinstance(tc.te.perturbation_density, str):
                return commons.parse_number(tc.te.perturbation_density)
            elif isinstance(tc.te.perturbation_density, int):
                return tc.te.perturbation_density
            else:
                raise TypeError(f"density can be either int or str")

        def get_optimal_path_ratio(tc: "PathFindingTestContext", csv_name: str, index: int, csv_row: PathFindingCsvRow):
            if settings.ignore_unperturbated_paths and csv_row.path_original_cost == csv_row.path_revised_cost:
                raise IgnoreCSVRowError()
            lb, ub, lb_included, ub_included = commons.parse_range(tc.te.optimal_path_ratio)
            if lb_included is False or ub_included is False or lb != ub:
                raise ValueError(f"The interval does not represent a single value! lb={lb}. ub={ub}, lb_included={lb_included}, ub_included={ub_included}")
            return lb

        def get_sequence_length(tc: "PathFindingTestContext", csv_name: str, index: int, csv_row: PathFindingCsvRow):
            if settings.ignore_unperturbated_paths and csv_row.path_original_cost == csv_row.path_revised_cost:
                raise IgnoreCSVRowError()
            lb, ub, lb_included, ub_included = commons.parse_range(tc.te.sequence_length)
            if lb_included is False or ub_included is False or lb != ub:
                raise ValueError(f"The interval does not represent a single value! lb={lb}. ub={ub}, lb_included={lb_included}, ub_included={ub_included}")
            return lb

        def get_upperbound_of_0_optimal_path_ratio(tc: "PathFindingTestContext", csv_name: str, index: int, csv_row: PathFindingCsvRow):
            if settings.ignore_unperturbated_paths and csv_row.path_original_cost == csv_row.path_revised_cost:
                raise IgnoreCSVRowError()
            lb, ub, lb_included, ub_included = commons.parse_range(tc.te.sequence_length)

            if lb_included is True and lb == 0 and ub_included is True and lb != ub:
                return ub
            else:
                raise ValueError(f"The interval does not represent an interval of type [0;x]! lb={lb}. ub={ub}, lb_included={lb_included}, ub_included={ub_included}")

        def get_upperbound_optimal_path_ratio(tc: "PathFindingTestContext", csv_name: str, index: int, csv_row: PathFindingCsvRow):
            if settings.ignore_unperturbated_paths and csv_row.path_original_cost == csv_row.path_revised_cost:
                raise IgnoreCSVRowError()
            lb, ub, lb_included, ub_included = commons.parse_range(tc.te.sequence_length)

            if ub_included is True:
                return ub
            else:
                raise ValueError(f"The interval does not represent an interval of type [0;x]! lb={lb}. ub={ub}, lb_included={lb_included}, ub_included={ub_included}")

        def get_area_radius(tc: "PathFindingTestContext", csv_name: str, index: int, csv_row: PathFindingCsvRow):
            if settings.ignore_unperturbated_paths and csv_row.path_original_cost == csv_row.path_revised_cost:
                raise IgnoreCSVRowError()
            lb, ub, lb_included, ub_included = commons.parse_range(tc.te.area_radius)
            if lb_included is False or ub_included is False or lb != ub:
                raise ValueError(f"The interval does not represent a single value! lb={lb}. ub={ub}, lb_included={lb_included}, ub_included={ub_included}")
            return lb

        def get_solution_cost(tc: "PathFindingTestContext", csv_name: str, index: int, csv_row: PathFindingCsvRow):
            if settings.ignore_unperturbated_paths and csv_row.path_original_cost == csv_row.path_revised_cost:
                raise IgnoreCSVRowError()
            return csv_row.path_revised_cost

        def set_params_mask_as_current_test_environment(te: "PathFindingTestingEnvironment", tcm: "ITestContextMask", name: str, visited: List["ITestContextMask"]) -> Dict[str, Any]:
            if te.perturbation_density is not None:
                if isinstance(te.perturbation_density, str):
                    if "%" in te.perturbation_density:
                        raise ValueToIgnoreError()
                elif isinstance(te.perturbation_density, int):
                    pass
                else:
                    raise TypeError(f"density can either be a int or str")
            return dict(current_test_environment=te, option_name=name)

        def generate_subtitle(tcm: "ITestContextMask") -> str:
            return tcm.get_have_value_string(ignore_some_tcm_keys=["map_filename", "scenario_file", "perturbation_kind"])

        # ############################# query ###########################################

        @run_process()
        def time_over_query():
            tcm = self.generate_test_context_mask()
            tcm.ut.use_bound = masks.TestContextMaskNeedToHaveValue(True)

            self.generate_batch_of_plots(
                xaxis_name="Query Id [#]",
                yaxis_name="time to complete query [us]",
                title="Performance over query id (times SORTED)",
                subtitle_function=generate_subtitle,
                get_x_value=get_query_id,
                get_y_value=get_us_time,
                aggregator=aggregators.SingleAggregator(),
                image_suffix="single_time_over_query",
                user_tcm=tcm,
                mask_options=None,
                # curve_changer=curves_changers.SortCrescentYValues(),
            )

        @run_process()
        def avg_partialtime_over_query():
            tcm = self.generate_test_context_mask()
            tcm.ut.use_bound = masks.TestContextMaskNeedToHaveValue(True)

            self.generate_batch_of_plots(
                xaxis_name="Query Id [#]",
                yaxis_name="avg heuristic/total time[ratio]",
                title="Partial time over query id",
                subtitle_function=generate_subtitle,
                get_x_value=get_query_id,
                get_y_value=get_heuristic_ratio,
                aggregator=aggregators.MeanAggregator(),
                image_suffix="avg_partialtime_over_query",
                user_tcm=tcm,
                mask_options=None,
                curve_changer=curves_changers.LowCurveRemoval(threshold=0, threshold_included=False),  # disjkstra is always 0
            )

        @run_process()
        def avg_expandednodes_over_query():
            tcm = self.generate_test_context_mask()
            tcm.ut.use_bound = masks.TestContextMaskNeedToHaveValue(True)

            self.generate_batch_of_plots(
                xaxis_name="Query Id [#]",
                yaxis_name="avg expanded nodes [#]",
                title="Expanded nodes over query id",
                subtitle_function=generate_subtitle,
                get_x_value=get_query_id,
                get_y_value=get_expanded_nodes,
                aggregator=aggregators.MeanAggregator(),
                image_suffix="avg_expandednodes_over_query",
                user_tcm=tcm,
                mask_options=None,
            )

        @run_process()
        def perturbatedPaths_over_query():
            tcm = self.generate_test_context_mask()

            self.generate_batch_of_plots(
                xaxis_name="Query Id [#]",
                yaxis_name="Perturbated path [#]",
                title="Optimal perturbated paths over query id",
                subtitle_function=generate_subtitle,
                get_x_value=get_query_id,
                get_y_value=get_is_perturbated_path,
                aggregator=aggregators.SingleAggregator(),
                image_suffix="single_perturbatedPaths_over_query",
                user_tcm=tcm,
                mask_options=None,
            )

        @run_process()
        def solutioncost_over_query():
            tcm = self.generate_test_context_mask()
            tcm.ut.use_bound = masks.TestContextMaskNeedToHaveValue(True)

            self.generate_batch_of_plots(
                xaxis_name="Query Id [#]",
                yaxis_name="solution cost [us]",
                title="Solution quality over query id",
                subtitle_function=generate_subtitle,
                get_x_value=get_query_id,
                get_y_value=get_solution_cost,
                aggregator=aggregators.SingleAggregator(),
                image_suffix="solutioncost_over_query",
                user_tcm=tcm,
                mask_options=None,
            )

        # ########################### path lengths ###############################

        @run_process()
        def avg_time_over_pathLengths():
            tcm = self.generate_test_context_mask()

            self.generate_batch_of_plots(
                xaxis_name="Original path length [#]",
                yaxis_name="avg time per query [us]",
                title="Average time a query needs to compute optimal revised path",
                subtitle_function=generate_subtitle,
                get_x_value=get_original_path_length,
                get_y_value=get_us_time,
                aggregator=aggregators.MeanAggregator(),
                image_suffix="avg_time_over_pathLengths",
                user_tcm=tcm,
                mask_options=None,
            )

        @run_process()
        def avg_perturbatedPaths_over_pathLengths():
            tcm = self.generate_test_context_mask()

            self.generate_batch_of_plots(
                xaxis_name="Original path length [#]",
                yaxis_name="avg Revised paths [#]",
                title="Number of perturbated paths in scenario over the original path length",
                subtitle_function=generate_subtitle,
                get_x_value=get_original_path_length,
                get_y_value=get_is_perturbated_path,
                aggregator=aggregators.MeanAggregator(),
                image_suffix="avg_perturbatedPaths_over_pathLengths",
                user_tcm=tcm,
                mask_options=None,
            )

        # ############################## sequence length ##############################

        @run_process()
        def avg_time_over_sequencelength():
            tcm = self.generate_test_context_mask()
            tcm.te.perturbation_kind = masks.TestContextMaskNeedToHaveValue(constants.KIND_RATIO_PATH)
            tcm.te.sequence_length = masks.TestContextMaskNeedsNotNull()
            tcm.ut.use_bound = masks.TestContextMaskNeedToHaveValue(True)

            self.generate_batch_of_plots(
                xaxis_name="Length of perturbation on optimal path[#]",
                yaxis_name="avg time [us]",
                title="Average of query time over length of perturbation over the optimal path",
                subtitle_function=generate_subtitle,
                get_x_value=get_upperbound_optimal_path_ratio,
                get_y_value=get_us_time,
                aggregator=aggregators.MeanAggregator(),
                image_suffix="avg_time_over_sequencelength",
                user_tcm=tcm,
                mask_options=set_params_mask_as_current_test_environment,
            )

        @run_process()
        def avg_solutioncost_over_sequencelength():
            tcm = self.generate_test_context_mask()
            tcm.ut.use_bound = masks.TestContextMaskNeedToHaveValue(True)
            tcm.te.perturbation_kind = masks.TestContextMaskNeedToHaveValue(constants.KIND_RATIO_PATH)
            tcm.te.sequence_length = masks.TestContextMaskNeedsNotNull()

            self.generate_batch_of_plots(
                xaxis_name="Length of perturbation on optimal path[#]",
                yaxis_name="avg solution cost [us]",
                title="Average of solution quality over length of perturbation over optimal path",
                subtitle_function=generate_subtitle,
                get_x_value=get_upperbound_optimal_path_ratio,
                get_y_value=get_solution_cost,
                aggregator=aggregators.MeanAggregator(),
                image_suffix="avg_solutioncost_over_sequencelength",
                user_tcm=tcm,
                mask_options=None,
            )

        @run_process()
        def samplevariance_solutioncost_over_sequencelength():
            tcm = self.generate_test_context_mask()
            tcm.ut.use_bound = masks.TestContextMaskNeedToHaveValue(True)
            tcm.te.perturbation_kind = masks.TestContextMaskNeedToHaveValue(constants.KIND_RATIO_PATH)
            tcm.te.sequence_length = masks.TestContextMaskNeedsNotNull()

            self.generate_batch_of_plots(
                xaxis_name="Length of perturbation on optimal path[#]",
                yaxis_name="sample variance solution cost [us]",
                title="Sample variance of solution quality over length of perturbation over optimal path",
                subtitle_function=generate_subtitle,
                get_x_value=get_upperbound_optimal_path_ratio,
                get_y_value=get_solution_cost,
                aggregator=aggregators.SampleVarianceAggregator(),
                image_suffix="samplevariance_solutioncost_over_sequencelength",
                user_tcm=tcm,
                mask_options=None,
            )

        # ############################ area radius ################################

        @run_process()
        def avg_time_over_arearadius():
            tcm = self.generate_test_context_mask()
            tcm.te.perturbation_kind = masks.TestContextMaskNeedToHaveValue(constants.KIND_RATIO_AREA)
            tcm.te.area_radius = masks.TestContextMaskNeedsNotNull()
            tcm.ut.use_bound = masks.TestContextMaskNeedToHaveValue(True)

            self.generate_batch_of_plots(
                xaxis_name="Radius of perturbated area[#]",
                yaxis_name="avg time [us]",
                title="Average of query time over perturbated area radius over the optimal path",
                subtitle_function=generate_subtitle,
                get_x_value=get_area_radius,
                get_y_value=get_us_time,
                aggregator=aggregators.MeanAggregator(),
                image_suffix="avg_time_over_arearadius",
                user_tcm=tcm,
                mask_options=set_params_mask_as_current_test_environment,
            )

        @run_process()
        def avg_solution_cost_over_arearadius():
            tcm = self.generate_test_context_mask()
            tcm.ut.use_bound = masks.TestContextMaskNeedToHaveValue(True)
            tcm.te.perturbation_kind = masks.TestContextMaskNeedToHaveValue(constants.KIND_RATIO_AREA)
            tcm.te.area_radius = masks.TestContextMaskNeedsNotNull()

            self.generate_batch_of_plots(
                xaxis_name="Radius of perturbated area[#]",
                yaxis_name="avg solution cost [us]",
                title="Average solution quality over perturbated area radius over optimal path",
                subtitle_function=generate_subtitle,
                get_x_value=get_area_radius,
                get_y_value=get_solution_cost,
                aggregator=aggregators.MeanAggregator(),
                image_suffix="avg_solutioncost_over_arearadius",
                user_tcm=tcm,
                mask_options=None,
            )

        @run_process()
        def samplevariance_solution_cost_over_arearadius():
            tcm = self.generate_test_context_mask()

            tcm.ut.use_bound = masks.TestContextMaskNeedToHaveValue(True)
            tcm.te.perturbation_kind = masks.TestContextMaskNeedToHaveValue(constants.KIND_RATIO_AREA)
            tcm.te.area_radius = masks.TestContextMaskNeedsNotNull()

            self.generate_batch_of_plots(
                xaxis_name="Radius of perturbated area[#]",
                yaxis_name="sample variance solution cost [us]",
                title="Solution quality over perturbated area radius over optimal path",
                subtitle_function=generate_subtitle,
                get_x_value=get_area_radius,
                get_y_value=get_solution_cost,
                aggregator=aggregators.SampleVarianceAggregator(),
                image_suffix="samplevariance_solutioncost_over_arearadius",
                user_tcm=tcm,
                mask_options=None,
            )

        # ############################ edges altered ####################################

        @run_process()
        def avg_partialtime_over_edgesaltered():
            tcm = self.generate_test_context_mask()
            tcm.te.perturbation_density = masks.TestContextMaskNeedsToFollowPattern(r"\d+")

            self.generate_batch_of_plots(
                xaxis_name="Edges altered [#]",
                yaxis_name="avg heuristic/total time [ratio]",
                title="Average Heuristic total time ratio over perturbation number",
                subtitle_function=generate_subtitle,
                get_x_value=get_density,
                get_y_value=get_heuristic_ratio,
                aggregator=aggregators.MeanAggregator(),
                image_suffix="avg_partialtime_over_edgesaltered",
                user_tcm=tcm,
                mask_options=set_params_mask_as_current_test_environment,
                curve_changer=curves_changers.LowCurveRemoval(threshold=0, threshold_included=False),
                # disjkstra is always 0
            )

        @run_process()
        def avg_expandednodes_over_edgesaltered():
            tcm = self.generate_test_context_mask()
            tcm.te.perturbation_density = masks.TestContextMaskNeedsToFollowPattern(r"\d+")

            self.generate_batch_of_plots(
                xaxis_name="Edge altered [#]",
                yaxis_name="avg expanded nodes [#]",
                title="Average expanded nodes over perturbations",
                subtitle_function=generate_subtitle,
                get_x_value=get_density,
                get_y_value=get_expanded_nodes,
                aggregator=aggregators.MeanAggregator(),
                image_suffix="avg_expandednodes_over_edgesaltered",
                user_tcm=tcm,
                mask_options=set_params_mask_as_current_test_environment,
            )

        @run_process()
        def sum_perturbatedPaths_over_edgesaltered():
            tcm = self.generate_test_context_mask()
            tcm.te.perturbation_density = masks.TestContextMaskNeedsToFollowPattern(r"\d+")

            self.generate_batch_of_plots(
                xaxis_name="Edges altered [#]",
                yaxis_name="sum perturbated paths [#]",
                title="Sum of all perturbated optimal paths over perturbation number",
                subtitle_function=generate_subtitle,
                get_x_value=get_density,
                get_y_value=get_is_perturbated_path,
                aggregator=aggregators.SumAggregator(),
                image_suffix="sum_perturbatedPaths_over_edgesaltered",
                user_tcm=tcm,
                mask_options=set_params_mask_as_current_test_environment,
            )

        @run_process()
        def sum_time_over_edgesAltered():
            # by customising the tcm on this way we're overwriting the
            tcm = self.generate_test_context_mask()
            tcm.te.perturbation_density = masks.TestContextMaskNeedsToFollowPattern(r"\d+")

            self.generate_batch_of_plots(
                xaxis_name="Edge altered [#]",
                yaxis_name="sum time per query [us]",
                title="time to complete the whole scenario over perturbation",
                subtitle_function=generate_subtitle,
                get_x_value=get_density,
                get_y_value=get_us_time,
                aggregator=aggregators.SumAggregator(),
                image_suffix="sum_time_over_edgesaltered",
                user_tcm=tcm,
                mask_options=set_params_mask_as_current_test_environment,
            )

        @run_process()
        def avg_time_over_edgesAltered():
            # by customising the tcm on this way we're overwriting the
            tcm = self.generate_test_context_mask()
            tcm.te.perturbation_density = masks.TestContextMaskNeedsToFollowPattern(r"\d+")

            self.generate_batch_of_plots(
                xaxis_name="Edge altered [#]",
                yaxis_name="avg time per query [us]",
                title="time to complete the whole scenario over perturbation",
                subtitle_function=generate_subtitle,
                get_x_value=get_density,
                get_y_value=get_us_time,
                aggregator=aggregators.MeanAggregator(),
                image_suffix="avg_time_over_edgesaltered",
                user_tcm=tcm,
                mask_options=set_params_mask_as_current_test_environment,
            )

        run_process.start_and_wait()

    def __get_number_of_queries_in_scenario(self, scenario_filename: str) -> int:
        """
        :param scenario_filename: the name of a scenario file
        :return:the number of path planning queries inside the given scenario filename
        """
        with open(scenario_filename) as f:
            version_number_str = f.readline()
            logging.debug(f"{version_number_str}")
            m = re.match(r"\s*version\s*(?P<number>\d+)", version_number_str)
            if m is None:
                raise ValueError(f"cannot determine version of scenario file {scenario_filename}!")
            version_number = int(m.group("number"))

            if version_number == 1:
                # all other lines are query:
                return len(f.readlines()) - 1
            else:
                raise ValueError(f"I don't know how to handle the version number {version_number}!")

    def generate_report(self, paths: PathFindingPaths, settings: "PathFindingTestingGlobalSettings", tests_performed: ITestContextRepo, under_test_values: Dict[str, List[Any]], test_environment_values: Dict[str, List[Any]]):

        standard_layout = """
                    Left plots hold linear Y axis while right plots  hold logarithmic (base 2) ones. Top plots 
                    display raw data while bottom plots show cumulative data.
                """
        image_dict = KS001()
        uts_to_show = []
        alg: PathFindingStuffUnderTest = self.generate_under_testing()
        alg.algorithm = constants.ALG_ASTAR
        alg.heuristic = constants.HEU_CPD_CACHE
        alg.enable_earlystop = True
        alg.enable_upperbound = False
        uts_to_show.append(alg)

        alg: PathFindingStuffUnderTest = self.generate_under_testing()
        alg.algorithm = constants.ALG_ASTAR
        alg.heuristic = constants.HEU_DIFFERENTIAL_HEURISTIC
        alg.landmark_number = 5
        uts_to_show.append(alg)

        alg: PathFindingStuffUnderTest = self.generate_under_testing()
        alg.algorithm = constants.ALG_DIJKSTRA_EARLYSTOP
        uts_to_show.append(alg)

        densities_to_show = [1, 2901]
        perturbation_ranges = ["[3,3]"]
        optimal_path_ratios = ["[0,25]", "[75,75]"]
        sequence_length = "[15,15]"
        area_radius = "[15,15]"

        # generate involved test context (which are only those coming from the image folder!)
        image_test_context_repo = self.generate_test_context_repo(paths, settings)
        for tc in self.parse_testcontexts_from_directory(
            directory=paths.get_image_dir(),
            stuff_under_test_dict_values=under_test_values,
            test_environment_dict_values=test_environment_values,
            afilter=lambda x: x.endswith(".eps") or x.endswith(".png"),
            alias_to_name_dict=self.generate_test_context().get_alias_name_dict(),
            index=0
        ):
            image_test_context_repo.append(tc)

        root = LatexDocument()

        introduction = root.add_child(LatexSection(text="Perturbation strategy", label=f"introduction"))
        introduction.add_leaf_child(LatexText(text="""
                The graphs are perturbated in the the following way:
                """))
        perturbation_policies = introduction.add_child(LatexUnorderedList())
        perturbation_policies.add_leaf_child(LatexText(
            """RANDOM policy: we pick k arcs in the graph totally randomly and we perturbate them;"""
        ))
        perturbation_policies.add_leaf_child(LatexText(
            """RANDOM_ON_OPTIMAL policy: for k number of times we do the following: we pick a path planning query inside the map scenario;
            we then compute the optimal path via Dijkstra algorithm on the building map. Then we choose randomly an arc to perturbate within
            the ones composing the optimal path just computed. We finally perturbate the chosen arc. Note that, if a path planning query
            is chosen multiple times, the optimal paths computed by Dijsktra may be  different;"""
        ))
        perturbation_policies.add_leaf_child(LatexText(
            """RANDOM_RATIO_PATH policy: For each query in the database we compute (with Dijkstra) the optimal path. Then we choose
            a location in the optimal which at a particular percentage (for example 25% means we will choose something in the first quarter
            of the path). The perturbation we will make is a contiguous perturbated subset of the path which length is "sequence". 
            """
        ))
        perturbation_policies.add_leaf_child(LatexText(
            """RANDOM_RATIO_AREA policy: For each query in the database we compute (with Dijkstra) the optimal path. Then we choose
            a location in the optimal which at a particular percentage (for example 25% means we will choose something in the first quarter
            of the path). The perturbation we will make is a contiguous area of the path which radius is "radius". 
            """
        ))

        if settings.ignore_unperturbated_paths:
            introduction.add_leaf_child(LatexText(r"""Furthermore keep in mind that \textbf{we have removed from every plot 
                all paths which were unaffected by the perturbations}."""
            ))

        tcm = self.generate_test_context_mask()

        # we order the tests by map name
        for map_filename, scenario_file in zip(test_environment_values["map_filename"], test_environment_values["scenario_file"]):

            section = root.add_child(LatexSection(
                text=f"Map = {map_filename}",
                label=f"map={map_filename}"
            ))

            # perturbation kind set to random and random on optimal
            tcm.clear()
            tcm.map_filename = masks.TestContextMaskNeedToHaveValue(map_filename)
            tcm.scenario_file = masks.TestContextMaskNeedToHaveValue(scenario_file)

            for perturbation_kind in [constants.KIND_RANDOM, ]:

                # show the images over density
                tcm.perturbation_kind = masks.TestContextMaskNeedToHaveValue(perturbation_kind)
                tcm.perturbation_range = masks.TestContextMaskNeedToBeInSet(perturbation_ranges)
                tcm.perturbation_density = masks.TestContextMaskNeedsNull()

                subsection = section.add_child(LatexSubSection(
                    text=f"Plots over number of perturbations with kind {perturbation_kind}",
                    label=f"map={tcm}_densities"
                ))

                tc = image_test_context_repo.query_by_finding_mask(tcm)

                # image_dict.clear()
                # image_dict.add(dict=tc.te)
                image_dict = tc.te.to_ks001() + KS001.get_from(label="image_info", d={
                    "image_type": "sum_time_over_edgesaltered",
                    "mode": "multi",
                })
                subsection.add_child(
                    LatexSimpleImage(paths.generate_image_file(image_dict, extension="eps"),
                                    short_caption="Total time over number of perturbations on RANDOM",
                                    caption=f"""
                                    Total time each algorithm took in order to successfully complete all the 
                                    queries in the associated scenario.
                                    X axis represents how many arcs have been perturbated while 
                                    Y axis represents the total time to complete all the queries.
                                    {standard_layout} 
                                    """,
                                    label=f"{image_dict.dump_str()}_label",
                                    paths=paths,
                                    ))

                image_dict = tc.te.to_ks001() + KS001.get_from(label="image_info", d={
                    "image_type": "avg_time_over_edgesaltered",
                    "mode": "multi",
                })
                subsection.add_child(
                    LatexSimpleImage(paths.generate_image_file(image_dict, extension="eps"),
                                     short_caption=f"Average query time over perturbation number for {perturbation_kind}",
                                     caption=f"""
                                    Average time each algorithm took in order to successfully complete a single 
                                    query in the associated scenario.
                                    X axis represents how many arcs have been perturbated while 
                                    Y axis represents the total time to complete all the queries.
                                    {standard_layout} 
                                    """,
                                     label=f"{image_dict.dump(aliases=tc.get_name_alias_dict())}_label",
                                     paths=paths,
                                     ))

                image_dict = tc.te.to_ks001() + KS001.get_from(label="image_info", d={
                    "image_type": "avg_expandedNodes_over_edgesaltered",
                    "mode": "multi",
                })
                LatexSimpleImage(paths.generate_image_file(image_dict, extension="eps"),
                                short_caption=f"average expanded nodes perturbation number for {perturbation_kind}",
                                caption=f"""
                                Average expanded nodes generated by the algorithm in the associated scenario.
                                X axis represents how many arcs have been perturbated while
                                Y axis represents the sum of all the nodes an algorithm expanded
                                over all the queries in the scenario. 
                                {standard_layout}  
                                """,
                                label=f"{image_dict.dump(aliases=tc.get_name_alias_dict())}_label",
                                paths=paths,
                                )

                image_dict.clear()
                image_dict.add(dict=tc.te)
                image_dict.add_key_value(1, "image_type", "avg_partialtime_over_edgesaltered")
                image_dict.add_key_value(2, "mode", "multi")
                subsection.add_child(
                    LatexSimpleImage(paths.generate_image_file(image_dict, extension="eps"),
                                     short_caption=f"Average heuristic ratio over total time over number of perturbations",
                                    caption=f"""
                                    Average ratio between heuristic time and total time. 
                                    X axis represents how many arcs have been perturbated while 
                                    Y axis represents the average ratio between the total time spent computing 
                                    heuristics over the total time spent by an algorithm over all the queries in the map scenario.  
                                    Algorithms not using an heuristic have their ratio set to 0.
                                    {standard_layout}
                                    """,
                                    label=f"{image_dict.dump(aliases=tc.get_name_alias_dict())}_label",
                                    paths=paths,
                                    ))

                image_dict.clear()
                image_dict.add(dict=tc.te)
                image_dict.add_key_value(1, "image_type", "sum_perturbatedPaths_over_edgesaltered")
                image_dict.add_key_value(2, "mode", "multi")
                subsection.add_child(
                    LatexSimpleImage(paths.generate_image_file(image_dict, extension="eps"),
                                     short_caption=f"Sum of perturbated paths over number of perturbations",
                                     caption=f"""
                                                    Sum of all the paths which were perturbated in the scenarios 
                                                    X axis represents how many arcs have been perturbated while 
                                                    Y axis represents the sum of the optimal paths which were actually 
                                                    perturbated.
                                                    {standard_layout}
                                                    """,
                                     label=f"{image_dict.dump(aliases=tc.get_name_alias_dict())}_label",
                                     paths=paths,
                                     ))

                for density in densities_to_show:
                    # show a particular density
                    tcm.perturbation_density = masks.TestContextMaskNeedToHaveValue(density)
                    subsubsection = subsection.add_child(LatexSubSubSection(
                        text=f"Plots with number of perturbations set to {density}",
                    ))

                    tc: PathFindingTestContext = image_test_context_repo.query_by_finding_mask(tcm)
                    image_dict.clear()
                    image_dict.add(dict=tc.te)
                    image_dict.add_key_value(1, "image_type", "single_time_over_query")
                    image_dict.add_key_value(2, "mode", "multi")
                    subsubsection.add_child(
                        LatexSimpleImage(paths.generate_image_file(image_dict, extension="eps"),
                        short_caption=f"time over query in {perturbation_kind} for density {density}",
                        caption=f"""
                        Algorithms performances over the queries in the scenario when the perturbation density were {density}.
                        X axis represents the single queries while 
                        Y axis represents the time the algorithm used to clear the query. 
                        {standard_layout}
                        """,
                        label=f"{image_dict.dump(aliases=tc.get_name_alias_dict())}_label",
                        paths=paths
                    ))

                    tc: PathFindingTestContext = image_test_context_repo.query_by_finding_mask(tcm)
                    image_dict.clear()
                    image_dict.add(dict=tc.te)
                    image_dict.add_key_value(1, "image_type", "single_perturbatedPaths_over_query")
                    image_dict.add_key_value(2, "mode", "multi")
                    subsubsection.add_child(
                        LatexSimpleImage(paths.generate_image_file(image_dict, extension="eps"),
                     short_caption=f"Perturbated optimal paths over query in {perturbation_kind} for density {density}",
                     caption=f"""
                        Optimal paths which were perturvated over the queries in the scenario when the perturbation density were {density}.
                        X axis represents the single queries while 
                        Y axis is 1 if the optimal path of the query was perturbated, 0 otherwise. 
                        {standard_layout}
                        """,
                     label=f"{image_dict.dump(aliases=tc.get_name_alias_dict())}_label",
                     paths=paths
                     ))

                    # show the most difficult path in that density
                    for ut in uts_to_show:
                        self._put_map_example(
                            ut=ut,
                            tc=tc,
                            paths=paths,
                            section=subsection
                        )

            # perturbation kind set to path and area

            tcm.clear()
            tcm.map_filename = masks.TestContextMaskNeedToHaveValue(map_filename)
            tcm.scenario_file = masks.TestContextMaskNeedToHaveValue(scenario_file)

            for perturbation_kind in [constants.KIND_RATIO_PATH, ]:
                subsection: LatexSubSection = section.add_child(LatexSubSection(
                    text=f"Plots over perturbations of kind {perturbation_kind}",
                ))

                for optimal_path_ratio in optimal_path_ratios:

                    subsubsection: LatexSubSection = subsection.add_child(LatexSubSection(
                        text=f"Plots when perturbation happened in {optimal_path_ratio}% of optimal path",
                    ))

                    tcm.clear()
                    tcm.map_filename = masks.TestContextMaskNeedToHaveValue(map_filename)
                    tcm.scenario_file = masks.TestContextMaskNeedToHaveValue(scenario_file)
                    tcm.perturbation_kind = masks.TestContextMaskNeedToHaveValue(perturbation_kind)
                    tcm.optimal_path_ratio = masks.TestContextMaskNeedToHaveValue(optimal_path_ratio)
                    tcm.sequence_length = masks.TestContextMaskNeedToHaveValue(sequence_length)

                    tc: PathFindingTestContext = image_test_context_repo.query_by_finding_mask(tcm)

                    image_dict.clear()
                    image_dict.add(dict=tc.te)
                    image_dict.add_key_value(1, "image_type", "single_time_over_query")
                    image_dict.add_key_value(2, "mode", "multi")
                    subsubsection.add_child(
                        LatexSimpleImage(paths.generate_image_file(image_dict, extension="eps"),
                            short_caption=f"time over query in {perturbation_kind} with ratio {optimal_path_ratio}",
                             caption=f"""
                            Time each query took in order to successfully fetch the optimal path when 
                            perturbated at {optimal_path_ratio}. 
                            X axis represents the query id while 
                            Y axis represents the time we needed said query
                            {standard_layout} 
                            """,
                             label=f"{image_dict.dump(aliases=tc.get_name_alias_dict())}_label",
                             paths=paths,
                        ))

                    tcm.clear()
                    tcm.map_filename = masks.TestContextMaskNeedToHaveValue(map_filename)
                    tcm.scenario_file = masks.TestContextMaskNeedToHaveValue(scenario_file)
                    tcm.perturbation_kind = masks.TestContextMaskNeedToHaveValue(perturbation_kind)
                    tcm.optimal_path_ratio = masks.TestContextMaskNeedToHaveValue(optimal_path_ratio)
                    # we need to say that the filename does not have sequence length
                    tcm.sequence_length = masks.TestContextMaskNeedsNull()

                    tc: PathFindingTestContext = image_test_context_repo.query_by_finding_mask(tcm)

                    image_dict.clear()
                    image_dict.add(dict=tc.te)
                    image_dict.add_key_value(1, "image_type", "avg_time_over_sequencelength")
                    image_dict.add_key_value(2, "mode", "multi")
                    subsubsection.add_child(
                        LatexSimpleImage(paths.generate_image_file(image_dict, extension="eps"),
                                        short_caption=f"Average time over sequence length in {perturbation_kind}",
                                        caption=f"""
                                        Average time each query took in order to successfully fetch the optimal path
                                        (perturbated at {optimal_path_ratio}). 
                                        X axis represents the length of the a contiguous subpath on the optimal path 
                                        which has been perturbated while 
                                        Y axis represents the average time we needed to complete a query.
                                        {standard_layout} 
                                        """,
                                        label=f"{image_dict.dump(aliases=tc.get_name_alias_dict())}_label",
                                        paths=paths,
                                        ))

                    tcm.sequence_length = masks.TestContextMaskNeedToHaveValue(sequence_length)
                    tc: PathFindingTestContext = image_test_context_repo.query_by_finding_mask(tcm)
                    image_dict.clear()
                    image_dict.add(dict=tc.te)
                    image_dict.add_key_value(1, "image_type", "single_perturbatedPaths_over_query")
                    image_dict.add_key_value(2, "mode", "multi")
                    subsubsection.add_child(
                        LatexSimpleImage(paths.generate_image_file(image_dict, extension="eps"),
                                         short_caption=f"Perturbated optimal paths over query in {perturbation_kind} for sequence length {sequence_length}",
                                         caption=f"""
                                            Optimal paths which were perturbated over the queries in the scenario when 
                                            the perturbation density when sequence length is {sequence_length}
                                            (perturbation occured at {optimal_path_ratio}).
                                            X axis represents the single queries while 
                                            Y axis is 1 if the optimal path of the query was perturbated, 0 otherwise. 
                                            {standard_layout}
                                            """,
                                         label=f"{image_dict.dump(aliases=tc.get_name_alias_dict())}_label",
                                         paths=paths
                                         ))

                    paragraph: LatexParagraph = subsubsection.add_child(LatexSubSubSection(text="Examples of algorithm behaviour"))
                    tc.te.sequence_length = sequence_length
                    for ut in uts_to_show:
                        self._put_map_example(
                            ut=ut,
                            tc=tc,
                            paths=paths,
                            section=paragraph
                        )

            tcm.clear()
            tcm.map_filename = masks.TestContextMaskNeedToHaveValue(map_filename)
            tcm.scenario_file = masks.TestContextMaskNeedToHaveValue(scenario_file)

            for perturbation_kind in [constants.KIND_RATIO_AREA, ]:
                subsection = section.add_child(LatexSubSection(
                    text=f"Plots over perturbations of kind {perturbation_kind}",
                ))

                for optimal_path_ratio in optimal_path_ratios:

                    subsubsection = subsection.add_child(LatexSubSection(
                        text=f"Plots when perturbations happen in {optimal_path_ratio}% of optimal path",
                    ))

                    tcm.clear()
                    tcm.map_filename = masks.TestContextMaskNeedToHaveValue(map_filename)
                    tcm.scenario_file = masks.TestContextMaskNeedToHaveValue(scenario_file)
                    tcm.perturbation_kind = masks.TestContextMaskNeedToHaveValue(perturbation_kind)
                    tcm.optimal_path_ratio = masks.TestContextMaskNeedToHaveValue(optimal_path_ratio)
                    tcm.area_radius = masks.TestContextMaskNeedToHaveValue(area_radius)

                    tc: PathFindingTestContext = image_test_context_repo.query_by_finding_mask(tcm)

                    image_dict.clear()
                    image_dict.add(dict=tc.te)
                    image_dict.add_key_value(1, "image_type", "single_time_over_query")
                    image_dict.add_key_value(2, "mode", "multi")
                    subsubsection.add_child(
                        LatexSimpleImage(paths.generate_image_file(image_dict, extension="eps"),
                                         short_caption=f"time over query in {perturbation_kind}",
                                        caption=f"""
                                        Time each query took in order to successfully fetch the optimal path. 
                                        X axis represents query id while 
                                        Y axis represents the average time we needed to complete a query.
                                        {standard_layout} 
                                        """,
                                        label=f"{image_dict.dump(aliases=tc.get_name_alias_dict())}_label",
                                        paths=paths,
                                        ))

                    tcm.area_radius = masks.TestContextMaskNeedToHaveValue(area_radius)
                    tc: PathFindingTestContext = image_test_context_repo.query_by_finding_mask(tcm)
                    image_dict.clear()
                    image_dict.add(dict=tc.te)
                    image_dict.add_key_value(1, "image_type", "single_perturbatedPaths_over_query")
                    image_dict.add_key_value(2, "mode", "multi")
                    subsubsection.add_child(
                        LatexSimpleImage(paths.generate_image_file(image_dict, extension="eps"),
                                         short_caption=f"Perturbated optimal paths over query in {perturbation_kind} for area radius is {area_radius}",
                                         caption=f"""
                                            Optimal paths which were perturbated over the queries in the scenario when 
                                            the perturbation density when area radius is {area_radius}.
                                            X axis represents the single queries while 
                                            Y axis is 1 if the optimal path of the query was perturbated, 0 otherwise. 
                                            {standard_layout}
                                            """,
                                         label=f"{image_dict.dump(aliases=tc.get_name_alias_dict())}_label",
                                         paths=paths
                                         ))

                    tcm.clear()
                    tcm.map_filename = masks.TestContextMaskNeedToHaveValue(map_filename)
                    tcm.scenario_file = masks.TestContextMaskNeedToHaveValue(scenario_file)
                    tcm.perturbation_kind = masks.TestContextMaskNeedToHaveValue(perturbation_kind)
                    tcm.perturbation_density = masks.TestContextMaskNeedsNull()
                    tcm.optimal_path_ratio = masks.TestContextMaskNeedToHaveValue(optimal_path_ratio)
                    tcm.area_radius = masks.TestContextMaskNeedsNull()

                    tc: PathFindingTestContext = image_test_context_repo.query_by_finding_mask(tcm)

                    image_dict.clear()
                    image_dict.add(dict=tc.te)
                    image_dict.add_key_value(1, "image_type", "avg_time_over_arearadius")
                    image_dict.add_key_value(2, "mode", "multi")
                    subsubsection.add_child(
                        LatexSimpleImage(paths.generate_image_file(image_dict, extension="eps"),
                                        short_caption="Average time over area radius",
                                        caption=f"""
                                        Average time each query took in order to successfully fetch the optimal path. 
                                        X axis represents the radius of an area perturbating the optimal path while 
                                        Y axis represents the average time we needed to complete a query.
                                        {standard_layout} 
                                        """,
                                        label=f"{image_dict.dump(aliases=tc.get_name_alias_dict())}_label",
                                        paths=paths,
                                        ))

                    paragraph = subsubsection.add_child(LatexSubSubSection(text="Examples of algorithm behaviour"))
                    tc.te.area_radius = area_radius  # set the radius in order to the map example to fetch data
                    for ut in uts_to_show:
                        self._put_map_example(
                            ut=ut,
                            tc=tc,
                            paths=paths,
                            section=paragraph
                        )

        visitor = LatexVisitor()
        visitor.generate_latex("summary", root, paths=paths, run_latex=(not settings.generate_only_latex))

    def _put_map_example(self, ut: "PathFindingStuffUnderTest", tc: "PathFindingTestContext", paths: "PathFindingPaths", section: "LatexSection"):
        image_dict = KS001()
        image_dict.add(i=0, dict=ut)
        image_dict.add(i=0, dict=tc.te)
        image_dict.add_key_value(1, "type", "expandedNodes")

        queries: List[Tuple[str, KS001]] = list(image_dict.get_phddictionaries_compliant_from_directory(
            index=0,
            directory=paths.get_cwd_dir(),
            alias_name_dict=tc.get_alias_name_dict(),
            allowed_extensions=["png"]
        ))
        if len(queries) != 1:
            raise ValueError("I cannot decide which figure among those {} I need to use! The KS001 was:\n{}\nThe queries obtained were:\n{}".format(len(queries), image_dict, "\n".join(map(lambda x: x[0], queries))))

        ppds = queries[0][1]
        tc: PathFindingTestContext = self.generate_test_context()
        tc.set_options(ppds[0])
        queryid = int(ppds.get_value_in_dict(i=1, k="query"))
        image_dict.add(1, "query", queryid)
        section.add_child(
            LatexSimpleImage(paths.generate_cwd_file(ppds, extension="eps"),
                                           short_caption=f"Example of {tc.ut.get_label()} on {tc.te.get_label()}",
                                              caption=f"""
                                    Display of {tc.ut.get_label()} algorithm when solving the query #{queryid} for
                                    map "{tc.te.map_filename}". Each cell is represented by a 3x3 pixel grid.
                                    White cells represent unexplored cell. Black cells represent untraversable cells.
                                    Dark Yellow cells mean cells which were expanded by {tc.te.map_filename}.
                                    The brown path is the optimal path. For our proposed method, light brow cells
                                    represents cells which were automatically fetched from the CPD. For landmarks, dark red
                                    cells represent landmark locations. Perturbation are marked with red pixels and are
                                    shown only for expanded cells.
                                    """,
                                      label=f"{image_dict.dump(aliases=tc.get_name_alias_dict())}_map_label",
                                      paths=paths,
                                      ))

    def _generate_map_perturbation(self, paths: PathFindingPaths, test: PathFindingTestContext, random_seed: int):
        perturbated_map_filename_template = paths.get_perturbated_map_filename_template(test)

        # we need to check if the previous test_environment was the same of this. Why?
        # For KIND_RATIO_PATH and KIND_RATIO_AREA we need to generate queries per test environment
        # and then use the same perturbated maps for each stuff under test.
        # So, we need to generate the maps for the first time we see a test environment and
        # delete the old ones just before running the next ones.

        if self.__previous_test_context_tested is not None:
            if self.__previous_test_context_tested.te != test.te:
                # we need to remove the old perturbated maps only if they were generated
                if self.__previous_test_context_tested.te.perturbation_kind in [constants.KIND_RATIO_PATH, constants.KIND_RATIO_AREA]:
                    # ok, we need to remove all the previous perturbated maps dependent on query
                    # ok, to reduce space consumption we need to remove all the perturbated maps depending on a single query.
                    # we have created maps depending on query. Remove them
                    for f in list(paths.get_maps_per_query_of(self.__previous_test_context_tested)):
                        os.remove(f)
                        os.remove(f"{f}.info.txt")
            elif self.__previous_test_context_tested.te == test.te:
                # ok, we already have generated the perturbated maps dependent on query. Return immediately
                return
            else:
                raise ValueError(f"""
                    invalid scenario previous = {self.__previous_test_context_tested.te}, current= {test.te}\n
                    equal was = {self.__previous_test_context_tested.te == test.te}
                    not equal as {self.__previous_test_context_tested.te != test.te}
                """)
        else:
            # ok this is the first time we generate a map. Continue generating the perturbated maps dependent on query
            pass

        self.__previous_test_context_tested = test

        # we need to call MapPerturbator program
        arguments = []
        arguments.extend([
            f'--map_file="{paths.get_map_absfilename(test.te.map_filename)}"',
            f'--scenario_file="{paths.get_scenario_absfilename(test.te.scenario_file)}"',
            f'--perturbation_mode="{test.te.perturbation_mode}"',
            f'--perturbation_range="{test.te.perturbation_range}"',
            f'--random_seed={random_seed}',
            f'--output_template="{perturbated_map_filename_template}"',
            f'--validate_changes',
        ])

        if test.te.perturbation_kind in [constants.KIND_RANDOM, constants.KIND_RANDOM_OPTIMAL, constants.KIND_PATH_RANDOM_ON_OPTIMAL]:

            arguments.extend([
                f'--map_perturbation="{test.te.perturbation_kind}"',
                f'--perturbation_density="{test.te.perturbation_density}"',
            ])
            if test.te.perturbation_kind in [constants.KIND_PATH_RANDOM_ON_OPTIMAL]:
                arguments.extend([
                    f'--perturbation_sequence="{test.te.sequence_length}"',
                ])

        elif test.te.perturbation_kind in [constants.KIND_RANDOM_TERRAIN]:
            arguments.extend([
                f'--map_perturbation="{test.te.perturbation_kind}"',
                f'--terrain_to_perturbate_set="{test.te.terrains_to_alter}"',
                f'--terrain_to_perturbate_number={len(test.te.terrains_to_alter)}',
            ])

        elif test.te.perturbation_kind in [constants.KIND_RATIO_PATH, constants.KIND_RATIO_AREA]:
            arguments.extend([
                f'--generate_perturbations_per_query',
                f'--location_chooser="RATIO_ON_OPTIMAL_PATH"',
                f'--optimal_path_ratio="{test.te.optimal_path_ratio}"',
            ])
            if test.te.perturbation_kind in [constants.KIND_RATIO_AREA]:
                arguments.extend([
                    f'--perturbation_radius_range="{test.te.area_radius}"',
                    f'--map_perturbation="QUERY_RANDOM_AREA"',
                ])
            elif test.te.perturbation_kind in [constants.KIND_RATIO_PATH]:
                arguments.extend([
                    f'--perturbation_sequence="{test.te.sequence_length}"',
                    f'--map_perturbation="QUERY_RANDOM_OPTIMAL_PATH"',
                ])
            else:
                raise ValueError(f"invalid perturbation {test.te.perturbation_kind}")

        else:
            raise ValueError(f"invalid perturbation kind {test.te.perturbation_kind}")

        program = ["MapPerturbator"] + arguments
        executor = commons.ProgramExecutor()
        try:
            executor.execute_external_program(
                program=program,
                working_directory=paths.get_cwd_dir()
            )
        except commons.ExternalProgramFailureError as e:
            raise e

    @staticmethod
    def get_random_seed() -> int:
        return int(time.time() / 10000)

    def _generate_mainoutput(self, paths: PathFindingPaths, test: PathFindingTestContext, random_seed: int, settings: PathFindingTestingGlobalSettings):
        tester_output_template = paths.get_dynamicpathfindingtester_program_template(test)

        perturbated_map_filename_template = paths.get_perturbated_map_filename_template(test)

        arguments = []
        arguments.extend([
            f'--map_file="{paths.get_map_absfilename(test.te.map_filename)}"',
            f'--scenario_file="{paths.get_scenario_absfilename(test.te.scenario_file)}"',
            f'--output_template="{tester_output_template}"',
            f'--algorithm="{test.ut.algorithm}"',
            f'--random_seed={random_seed}',
            f'--perturbated_map_filename_template="{perturbated_map_filename_template}"',
            f'--validate_paths',
        ])

        if settings.debug is True:
            arguments.extend([
                f'--draw_expandedmaps',
            ])
        if len(settings.generate_images_only_for) > 0:
            arguments.extend([
                f'--generate_images_only_for="{commons.convert_int_list_into_str(settings.generate_images_only_for)}"'
            ])

        if test.ut.use_bound:
            arguments.extend([
                f"--test_bounded_algorithms",
                f"--use_bounds",
            ])

        logging.debug(f"doing the test!")
        if test.ut.algorithm == constants.ALG_DIJKSTRA_EARLYSTOP:
            program = ["DynamicPathFindingTester"] + arguments
        elif test.ut.algorithm in [constants.ALG_ASTAR, constants.ALG_WASTAR]:

            if test.ut.use_bound:
                if test.ut.algorithm == constants.ALG_ASTAR:
                    arguments.extend([
                        f"--bounded={test.ut.bound}",
                        f"--h_weight=1.0",
                    ])
                elif test.ut.algorithm == constants.ALG_WASTAR:
                    arguments.extend([
                        # if the bound is 0.2, the weight needs to be 1.2 since h_weight directly multiply h
                        f"--h_weight={1 + test.ut.bound}"
                    ])
                else:
                    raise ValueError(f"invalid algorithm {test.ut.algorithm}!")
            else:
                if test.ut.algorithm == constants.ALG_ASTAR:
                    arguments.extend([
                        f"--h_weight=1.0"
                    ])
                elif test.ut.algorithm == constants.ALG_WASTAR:
                    raise ValueError(f"WA* cannot be used for unbounded search!")
                else:
                    raise ValueError(f"invalid algorithm {test.ut.algorithm}!")

            arguments = arguments + [
                f'--heuristic={test.ut.heuristic}',
            ]

            if test.ut.heuristic in [constants.HEU_CPD_CACHE, constants.HEU_CPD_NO_CACHE]:
                if test.ut.enable_upperbound:
                    arguments = arguments + [f'--enable_upperbound', ]
                if test.ut.enable_earlystop:
                    arguments = arguments + [f'--enable_earlystop', ]
            elif test.ut.heuristic in [constants.HEU_DIFFERENTIAL_HEURISTIC]:
                arguments = arguments + [f'--landmark_number={test.ut.landmark_number}']
            else:
                raise ValueError(f"invalid heuristic {test.ut.heuristic}")

            program = ["DynamicPathFindingTester"] + arguments
        else:
            raise ValueError(f"cannot detect algorithm!")

        executor = commons.ProgramExecutor()
        try:
            executor.execute_external_program(
                program=program,
                working_directory=paths.get_cwd_dir()
            )
        except subprocess.CalledProcessError as e:
            raise e

        # ok, we now move the csv to the csv directory. the csv at the  moment is in the cwd_directory
        logging.debug("copying the csv into the csv directory...")
        csv_in_cwd_directory = paths.get_csv_mainoutput_name_just_generated(test)
        csv_in_csv_directory = paths.get_csv_mainoutput_name(test)
        shutil.move(csv_in_cwd_directory, csv_in_csv_directory)

    def perform_test(self, path: PathFindingPaths, tc: PathFindingTestContext, global_settings: PathFindingTestingGlobalSettings):
        # check if the csv exist. If it doesn't exist we ignore we go to the next test to perform
        if os.path.exists(path.get_csv_mainoutput_name(tc)):
            return

        logging.info(f"testing {tc}")
        # ALWAYS generate the map perturbations
        self._generate_map_perturbation(path, tc, PathFindingResearchField.get_random_seed())
        # generate the csvs
        self._generate_mainoutput(path, tc, PathFindingResearchField.get_random_seed(), global_settings)

    def get_csv_row(self, d: Dict[str, str]) -> "PathFindingCsvRow":
        result = PathFindingCsvRow()
        result.path_step_size = int(d["Path Step Size"])
        result.us_time = int(d["Time"])
        result.path_revised_cost = int(d["PathRevisedCost"])
        result.path_original_cost = int(d["PathOriginalCost"])
        result.heuristic_time = int(d["HeuristicTime"])
        result.has_original_path_perturbated = bool(d["OriginalOptimalPathPerturbated"])
        result.experiment_id = int(d["ExperimentId"])
        result.expanded_nodes = int(d["NodesExpanded"])

        return result
