# import os
#
# from phdTester.commons import FileWriter, ProgramExecutor, ExternalProgramFailureError
# from phdTester.report_generator.model_interfaces import ILatexNode, ILatexLeafNode
#
#
# class LatexVisitor:
#
#     def __init__(self):
#         pass
#
#     def generate_latex(self, name: str, root: ILatexNode, paths: "ImportantPaths", run_latex: bool):
#         with FileWriter(paths.get_output(f"{name}.tex"), mode="w") as f:
#             self._generate_latex(f=f, node=root)
#
#         # https://tex.stackexchange.com/a/387/145331
#         if run_latex:
#             executor = ProgramExecutor()
#
#             try:
#                 executor.execute_external_program(
#                     program=f"pdflatex -interaction=nonstopmode -halt-on-error -shell-escape {name}.tex",
#                     working_directory=paths.get_output_dir()
#                 )
#                 executor.execute_external_program(
#                     program=f"pdflatex -interaction=nonstopmode -halt-on-error -shell-escape {name}.tex",
#                     working_directory=paths.get_output_dir()
#                 )
#                 for file_to_remove in [f"{name}.out", f"{name}.lof", f"{name}.toc", f"{name}.tex", f"{name}.log", f"{name}.aux", f"texput.log"]:
#                     try:
#                         os.remove(paths.get_output(file_to_remove))
#                     except OSError:
#                         pass
#             except ExternalProgramFailureError as e:
#                 raise e
#
#     def _generate_latex(self, f: FileWriter, node: ILatexNode):
#         if isinstance(node, ILatexNode):
#             node.begin_process(f, {})
#             for i, child in enumerate(node):
#                 node.begin_direct_child(f, i, child, node.children_number, i == 0, (i + 1) == node.children_number, {})
#                 self._generate_latex(f, child)
#                 node.end_direct_child(f, i, child, node.children_number, i == 0, (i + 1) == node.children_number, {})
#             node.end_process(f, {})
#         elif isinstance(node, ILatexLeafNode):
#             node.begin_process(f, {})
#             node.end_process(f, {})
#         else:
#             raise TypeError(f"invalid node type {type(node)}")
#
#
#
#
