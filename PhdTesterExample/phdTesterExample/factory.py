import logging
import subprocess
import pandas as pd

from typing import Dict, List, Any

from phdTester import default_models, commons, masks, options
from phdTester.datasources import filesystem_sources
from phdTester.datasources.filesystem_sources import FileSystem
from phdTester.default_models import SimpleTestContextRepo
from phdTester.image_computer import aggregators
from phdTester.ks001.ks001 import KS001
from phdTester.model_interfaces import IDataSource, ITestingEnvironment, IUnderTesting, ITestingGlobalSettings, \
    ITestContext, ITestContextMask, ITestContextMaskOption, ICsvRow, ITestContextRepo
from phdTester.options_builder import OptionGraph, OptionBuilder
from phdTester.paths import ImportantPaths
from phdTester.specific_research_field import AbstractSpecificResearchFieldFactory
from phdTesterExample.models import SortEnvironmentMask, SortTestContext, SortAlgorithmMask, SortTestContextMask, \
    SortSettings, SortAlgorithm, SortEnvironment, PerformanceCsvRow


class SortResearchField(AbstractSpecificResearchFieldFactory):

    # TODO create defaul implementation
    def _get_ks001_colon(self, settings: "ITestingGlobalSettings") -> str:
        return ":"

    def _get_ks001_pipe(self, settings: "ITestingGlobalSettings") -> str:
        return "|"

    def _get_ks001_underscore(self, settings: "ITestingGlobalSettings") -> str:
        return "_"

    def _get_ks001_equal(self, settings: "ITestingGlobalSettings") -> str:
        return "="

    def generate_option_graph(self) -> OptionGraph:

        return OptionBuilder().add_under_testing_multiplexer(
            name="algorithm",
            possible_values=["BUBBLESORT", "MERGESORT", ],
            ahelp="""The algorithm we want to test""",
        ).add_environment_value(
            name="sequenceSize",
            option_type=options.Int,
            ahelp="""The size of the sequence to test""",
        ).add_environment_value(
            name="sequenceType",
            option_type=options.Str,
            ahelp="""The type of the sequence to test under""",
        ).add_environment_value(
            name="lowerBound",
            option_type=options.Int,
            ahelp="""lowerbound of any number generated in the sequence""",
        ).add_environment_value(
            name="upperBound",
            option_type=options.Int,
            ahelp="""upperbound of any number generated in the sequence""",
        ).add_environment_value(
            name="run",
            option_type=options.Int,
            ahelp="""number of runs to execute for each test context""",
        ).add_settings_value(
            name="outputDirectory",
            option_type=options.Str,
            ahelp="""the absolute path of the directory where everything will be generated"""
        ).get_option_graph()

    def _generate_datasource(self, settings: "SortSettings") -> "IDataSource":
        return self.filesystem_datasource

    # TODO might be default to datasource if _generate_datasource is a FileSystem
    def _generate_filesystem_datasource(self, settings: "SortSettings") -> "filesystem_sources.FileSystem":
        result = FileSystem(root=settings.outputDirectory)
        # orgqanize the filesystem as well
        result.make_folders("cwd")
        result.make_folders("csvs")
        # TODO bny default the file system cannot handle even csv... we should correct this
        result.register_resource_manager(
            resource_type="csv",
            manager=filesystem_sources.CsvFileSystem()
        )

        return result


    def generate_paths(self, settings: "SortSettings") -> ImportantPaths:
        # TODO remove it since it's not used anymore
        pass

    def generate_output_directory_structure(self, paths: "ImportantPaths", settings: "SortSettings"):
        # TODO remove it because it's dependent to file system data sourc
        pass

    def generate_environment(self) -> "ITestingEnvironment":
        return SortEnvironment()

    def generate_under_testing(self) -> "IUnderTesting":
        return SortAlgorithm()

    def generate_test_global_settings(self) -> "ITestingGlobalSettings":
        return SortSettings()

    # TODO maybe we can provide a default implementation....
    def generate_test_context(self, ut: IUnderTesting = None, te: ITestingEnvironment = None) -> "ITestContext":
        # TODO maybe we can ditch  it
        ut = ut if ut is not None else self.generate_under_testing()
        te = te if te is not None else self.generate_environment()
        return SortTestContext(ut=ut, te=te)

    #TODO make it such that one may avoid generating under_test, global_settings, environment and their mask entirely (they are there only to generate the content assist)
    def generate_stuff_under_test_mask(self) -> "SortAlgorithmMask":
        return SortAlgorithmMask()

    def generate_test_environment_mask(self) -> "SortEnvironmentMask":
        return SortEnvironmentMask()

    # TODO maybe we can create a signature similar to generate_test_context
    def generate_test_context_mask(self) -> "SortTestContextMask":
        return SortTestContextMask(ut=self.generate_stuff_under_test_mask(), te=self.generate_test_environment_mask())

    # todo remove. It's not used anywhere
    def generate_test_context_repo(self, paths: "ImportantPaths",
                                   settings: "ITestingGlobalSettings") -> "ITestContextRepo":
        return SimpleTestContextRepo()

    #TODO optional. Used only to execute code before the test
    def begin_perform_test(self, stuff_under_test_values: Dict[str, List[Any]],
                           test_environment_values: Dict[str, List[Any]], settings: "ITestingGlobalSettings"):
        pass

    # TODO optional. Used only to execute code after the test
    def end_perform_test(self, stuff_under_test_values: Dict[str, List[Any]],
                         test_environment_values: Dict[str, List[Any]], settings: "ITestingGlobalSettings"):
        pass

    #TODO paths should be removed
    def perform_test(self, paths: ImportantPaths, tc: SortTestContext, global_settings: "ITestingGlobalSettings"):
        output_template_ks001 = tc.to_ks001(identifier='main')
        performance_ks001 = output_template_ks001.append(
            KS001.from_template(output_template_ks001, label="kind", type="main"), in_place=False
        )
        performance_csv_output = performance_ks001.dump_filename(extension="csv")

        program = [
            "SortAlgorithmTester",
            f"--sequenceSize={tc.te.sequenceSize}",
            f"--sequenceType={tc.te.sequenceType}",
            f"--algorithm={tc.ut.algorithm}",
            f"--lowerBound={tc.te.lowerBound}",
            f"--upperBound={tc.te.upperBound}",
            f"--seed=0",
            f'--outputTemplate="{output_template_ks001.dump_str()}"',
            f'--runs={tc.te.run}'
        ]

        executor = commons.ProgramExecutor()
        try:
            executor.execute_external_program(
                program=' '.join(program),
                #TODO this should be moved to cwd
                working_directory=self.filesystem_datasource.get_path("cwd")
            )
        except subprocess.CalledProcessError as e:
            raise e

        # ok, save the csv in the datasource
        self.filesystem_datasource.move_to(
            self.datasource,
            from_path="cwd",
            from_ks001=performance_ks001.dump_str(),
            from_data_type='csv',
            to_path="csvs",
        )


    def generate_plots(self, paths: ImportantPaths, settings: "ITestingGlobalSettings",
                       under_test_values: Dict[str, List[Any]], test_environment_values: Dict[str, List[Any]]):

        def get_run_id(tc: "SortTestContext", path: str, data_type: str, content: pd.DataFrame, rowid: int, row: "PerformanceCsvRow") -> float:
            return row.run

        def get_time(tc: "SortTestContext", path: str, data_type: str, content: pd.DataFrame, rowid: int, row: "PerformanceCsvRow") -> float:
            return row.time

        def get_sequence_size(tc: "SortTestContext", path: str, data_type: str, content: pd.DataFrame, rowid: int, row: "PerformanceCsvRow") -> float:
            return tc.te.sequenceSize

        user_tcm = self.generate_test_context_mask()
        user_tcm.ut.algorithm = masks.TestContextMaskNeedsNotNull()

        # TODO generate an automatic generation of subtitle
        # TODO generate an interface for get_x_value function
        # TODO generate path function interface
        self.generate_batch_of_plots(
            xaxis_name="run id",
            yaxis_name="time (us)",
            title="time over run id",
            subtitle_function=lambda tc: "",
            get_x_value=get_run_id,
            get_y_value=get_time,
            y_aggregator=aggregators.SingleAggregator(),
            image_suffix="|image:type=time_over_runid",  # this should be a ks001 as well
            user_tcm=user_tcm,
            path_function=lambda tcm: "csvs",
        )

        user_tcm = self.generate_test_context_mask()
        user_tcm.te.sequenceSize = masks.TestContextMaskNeedsNotNull()

        self.generate_batch_of_plots(
            xaxis_name="sequence size",
            yaxis_name="avg time (us)",
            title="time over sequence size",
            subtitle_function=lambda tc: "",
            get_x_value=get_sequence_size,
            get_y_value=get_time,
            y_aggregator=aggregators.MeanAggregator(),
            image_suffix="|image:type=time_over_sequenceSize",
            user_tcm=user_tcm,
            path_function=lambda tcm: "csvs",
        )

    def generate_csvs(self, paths: ImportantPaths, settings: "ITestingGlobalSettings",
                      under_test_values: Dict[str, List[Any]], test_environment_values: Dict[str, List[Any]]):
        pass

    def generate_report(self, paths: ImportantPaths, settings: "ITestingGlobalSettings",
                        tests_performed: "ITestContextRepo", under_test_values: Dict[str, List[Any]],
                        test_environment_values: Dict[str, List[Any]]):
        pass

    # TODO allows multiple csv rows. This should be done by removing this method
    # TODO maybe we should also automatize the set of "d" set_options(d)
    def get_csv_row(self, d: Dict[str, str], ks_csv: "KS001") -> "PerformanceCsvRow":
        result = PerformanceCsvRow()
        result.set_options(d)
        return result







def main():
    factory = SortResearchField()
    factory.run()


if __name__ == "__main__":
    main()

