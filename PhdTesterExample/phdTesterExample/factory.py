

from typing import Dict, List, Any

import subprocess
import pandas as pd
import phdTester as phd
from phdTesterExample.models import SortSettings, SortEnvironment, SortAlgorithm, SortTestContext, SortAlgorithmMask, \
    SortEnvironmentMask, SortTestContextMask, PerformanceCsvRow


class SortResearchField(phd.AbstractSpecificResearchFieldFactory):

    def _generate_option_graph(self) -> "phd.OptionGraph":

        return phd.OptionBuilder().add_under_testing_multiplexer(
            name="algorithm",
            possible_values=["BUBBLESORT", "MERGESORT", ],
            ahelp="""The algorithm we want to test""",
        ).add_environment_value(
            name="sequenceSize",
            option_type=phd.option_types.Int(),
            ahelp="""The size of the sequence to test""",
        ).add_environment_value(
            name="sequenceType",
            option_type=phd.option_types.Str(),
            ahelp="""The type of the sequence to test under""",
        ).add_environment_value(
            name="lowerBound",
            option_type=phd.option_types.Int(),
            ahelp="""lowerbound of any number generated in the sequence""",
        ).add_environment_value(
            name="upperBound",
            option_type=phd.option_types.Int(),
            ahelp="""upperbound of any number generated in the sequence""",
        ).add_environment_value(
            name="run",
            option_type=phd.option_types.Int(),
            ahelp="""number of runs to execute for each test context""",
        ).add_settings_value(
            name="outputDirectory",
            option_type=phd.option_types.Str(),
            ahelp="""the absolute path of the directory where everything will be generated"""
        ).get_option_graph()

    def _generate_filesystem_datasource(self, settings: "SortSettings") -> "phd.datasources.FileSystem":
        result = phd.datasources.FileSystem(root=settings.outputDirectory)
        # TODO bny default the file system cannot handle even csv... we should correct this
        result.register_resource_manager(
            resource_type=r"(c)?sv",  # we could have written r"csv" but it just to show off regex capabilities
            manager=phd.datasources.CsvFileSystemResourceManager()
        )

        return result

    def setup_filesystem_datasource(self, filesystem: "phd.datasources.FileSystem", settings: "SortSettings"):
        filesystem.make_folders("images")
        filesystem.make_folders("csvs")
        filesystem.make_folders("cwd")

    # def generate_environment(self) -> "phd.ITestEnvironment":
    #     return SortEnvironment()
    #
    # def generate_under_testing(self) -> "phd.IStuffUnderTest":
    #     return SortAlgorithm()
    #
    # def _generate_test_context(self, ut: "SortAlgorithm", te: "SortEnvironment") -> "phd.ITestContext":
    #     return SortTestContext(ut=ut, te=te)

    # def generate_stuff_under_test_mask(self) -> "SortAlgorithmMask":
    #     return SortAlgorithmMask()
    #
    # def generate_test_environment_mask(self) -> "SortEnvironmentMask":
    #     return SortEnvironmentMask()
    #
    # def _generate_test_context_mask(self, ut: "SortAlgorithmMask", te: "SortEnvironmentMask") -> "SortTestContextMask":
    #     return SortTestContextMask(ut=self.generate_stuff_under_test_mask(), te=self.generate_test_environment_mask())

    def perform_test(self, tc: "phd.ITestContext", global_settings: "phd.IGlobalSettings"):
        output_template_ks001 = tc.to_ks001(identifier='main')
        performance_ks001 = output_template_ks001.append(
            phd.KS001.from_template(output_template_ks001, label="kind", type="main"), in_place=False
        )

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

        executor = phd.ProgramExecutor()
        try:
            executor.execute_external_program(
                program=' '.join(program),
                # TODO this should be moved to cwd
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

    def generate_plots(self, settings: "phd.IGlobalSettings",
                       under_test_values: Dict[str, List[Any]], test_environment_values: Dict[str, List[Any]]):

        def get_run_id(tc: "phd.ITestContext", path: str, data_type: str, content: pd.DataFrame, rowid: int, row: "PerformanceCsvRow") -> float:
            return row.run

        def get_time(tc: "phd.ITestContext", path: str, data_type: str, content: pd.DataFrame, rowid: int, row: "PerformanceCsvRow") -> float:
            return row.time

        def get_sequence_size(tc: "phd.ITestContext", path: str, data_type: str, content: pd.DataFrame, rowid: int, row: "PerformanceCsvRow") -> float:
            return tc.te.sequenceSize

        user_tcm = self.generate_test_context_mask()
        user_tcm.ut.algorithm = phd.masks.CannotBeNull()

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
            y_aggregator=phd.aggregators.SingleAggregator(),
            image_suffix=phd.KS001.single_labelled("image", type="time-over-runid"),
            user_tcm=user_tcm,
            path_function=lambda tcm: "csvs",
        )

        user_tcm = self.generate_test_context_mask()
        user_tcm.te.sequenceSize = phd.masks.CannotBeNull()

        self.generate_batch_of_plots(
            xaxis_name="sequence size",
            yaxis_name="avg time (us)",
            title="time over sequence size",
            subtitle_function=lambda tc: "",
            get_x_value=get_sequence_size,
            get_y_value=get_time,
            y_aggregator=phd.aggregators.MeanAggregator(),
            image_suffix=phd.KS001.single_labelled("image", type="time-over-sequencesize"),
            user_tcm=user_tcm,
            path_function=lambda tcm: "csvs",
        )

    def generate_csvs(self, settings: "phd.IGlobalSettings",
                      under_test_values: Dict[str, List[Any]], test_environment_values: Dict[str, List[Any]]):
        pass

    def generate_report(self, settings: "phd.IGlobalSettings",
                        tests_performed: "phd.ITestContextRepo", under_test_values: Dict[str, List[Any]],
                        test_environment_values: Dict[str, List[Any]]):
        pass

    # TODO allows multiple csv rows. This should be done by removing this method
    # TODO maybe we should also automatize the set of "d" set_options(d)
    def get_csv_row(self, d: Dict[str, str], ks_csv: "phd.KS001") -> "PerformanceCsvRow":
        result = PerformanceCsvRow()
        result.set_options(d)
        return result


def main():
    factory = SortResearchField()
    factory.run()


if __name__ == "__main__":
    main()

