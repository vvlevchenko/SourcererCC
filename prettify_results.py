#!/usr/bin/env python3

import datetime as dt
from argparse import ArgumentParser
import sys
import os
import re


def get_file_name(file_path):
    projects_dir = "tokenizer-sample-input"
    return re.sub(r"\.zip/[a-zA-Z0-9-.]+-master/", "/tree/master/", file_path.strip("\"")[len(projects_dir + "/"):].replace("--", "/"))


def get_file_lines(filename):
    with open(filename, "r", encoding="utf-8") as file_descr:
        for line in file_descr:
            yield line.strip("\n")


def merge_results(pairs):
    res = {}
    for x, y in pairs:
        if not x in res:
            res[x] = [y]
        else:
            res[x].append(y)
    return res


def filter_files(path, extension):
    res = set()
    if os.path.isdir(path):
        filtered_files = filter(lambda x: x.endswith(extension), os.listdir(path))
        res.update(map(lambda x: os.path.join(path, x), filtered_files))
    elif os.path.isfile(path):
        res.add(path)
    else:
        print("ERROR: '{}' not found!".format(path))
        sys.exit()
    return res


def get_projects_info(bookkeeping_files_path):
    files = filter_files(bookkeeping_files_path, ".projs")
    projects_info = []
    for bookkeeping_file in files:
        for line in get_file_lines(bookkeeping_file):
            project_info = {
                "project_id": line.split(",")[0],
                "project_path": line.split(",")[1]
            }
            projects_info.append(project_info)
    return projects_info


def get_results(results_file):
    results_pairs = []
    for line in get_file_lines(results_file):
        code_id_1 = line.split(",")[1]
        code_id_2 = line.split(",")[3]
        results_pairs.append((code_id_1, code_id_2))
    results = merge_results(results_pairs)
    return results


def print_results(results_file, stats_files, blocks_mode):
    stats = get_stats_info(stats_files, blocks_mode)
    results = get_results(results_file)
    formatted_titles = {}
    if blocks_mode:
        for code_id in stats.keys():
            if "start_line" in stats[code_id]:
                filename = get_file_name(stats[stats[code_id]["file_id"]]["file_path"])
                start_line = stats[code_id]["start_line"]
                end_line = stats[code_id]["end_line"]
                total_lines = end_line - start_line + 1
                formatted_titles[code_id] = f"{filename}(lines {start_line}-{end_line}, total {total_lines})"
    else:
        formatted_titles = {
            code_id: "{}({} SLOC)".format(get_file_name(stats[code_id]["file_path"]), stats[code_id]["SLOC"]) for code_id in stats.keys()
        }
    print("Results list:")
    for code_id, code_id_list in results.items():
        print("{} is similar to:".format(formatted_titles[code_id]))
        print("    " + "\n    ".join(map(lambda x: formatted_titles[x], code_id_list)))
        print()


def print_projects_list(bookkeeping_files):
    projects_info = get_projects_info(bookkeeping_files)
    print("Projects list:")
    for project in projects_info:
        project_lines = ["{}: {}".format(k, v) for k, v in project.items()]
        print("    " + "\n    ".join(project_lines))
        print()


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--blocks-mode", dest="blocks_mode", nargs="?", const=True, default=False, help="Specify if files produced in blocks-mode")
    parser.add_argument("-b", "--bookkeepingFiles", dest="bookkeeping_files", default=False, help="File or folder with bookkeeping files (*.projs).")
    parser.add_argument("-r", "--resultsFile", dest="results_file", default=False, help="File with results of SourcererCC (results.pairs).")

    options = parser.parse_args(sys.argv[1:])

    if len(sys.argv) == 1:
        print("No arguments were passed. Try running with '--help'.")
        sys.exit(0)

    p_start = dt.datetime.now()

    if options.results_file:
        if not options.stats_files:
            print("No stats files specified. Exiting")
            sys.exit(0)
        print_results(options.results_file, options.stats_files, options.blocks_mode)
    elif options.bookkeeping_files:
        print_projects_list(options.bookkeeping_files)

    print("Processed in {}".format(dt.datetime.now() - p_start))
