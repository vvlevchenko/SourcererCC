#!/usr/bin/env python3

import datetime as dt
import os
import sys
from multiprocessing import Process, Queue

from tokenizing.block_tokenizer import *


def process_projects(process_num, list_projects, base_file_id, global_queue, dirs_config):
    PATH_stats_file_folder = dirs_config["stats_file_folder"]
    PATH_bookkeeping_proj_folder = dirs_config["bookkeeping_proj_folder"]
    PATH_tokens_file_folder = dirs_config["tokens_file_folder"]

    tokens_file = os.path.join(PATH_tokens_file_folder, 'files-tokens-{}.tokens'.format(process_num))
    bookkeeping_file = os.path.join(PATH_bookkeeping_proj_folder, 'bookkeeping-proj-{}.projs'.format(process_num))
    stats_file = os.path.join(PATH_stats_file_folder, 'files-stats-{}.stats'.format(process_num))

    global file_count
    file_count = 0
    print("[INFO] Process {} starting".format(process_num))
    with open(tokens_file, 'a+', encoding="utf-8") as tokens_f, \
        open(bookkeeping_file, 'a+', encoding="utf-8") as bookkeeping_f, \
            open(stats_file, 'a+', encoding="utf-8") as stats_f:
        out_files = (tokens_f, bookkeeping_f, stats_f)
        p_start = dt.datetime.now()
        for proj_id, proj_path in list_projects:
            process_one_project(process_num, str(proj_id), proj_path, base_file_id, out_files)

    p_elapsed = (dt.datetime.now() - p_start).seconds
    print(f"[INFO] Process {process_num} finished. {file_count} files in {p_elapsed} s")

    # Let parent know
    global_queue.put((process_num, file_count))
    sys.exit(0)


def start_child(processes, global_queue, proj_paths, batch, dirs_config):
    # This is a blocking get. If the queue is empty, it waits
    pid, n_files_processed = global_queue.get()
    # OK, one of the processes finished. Let's get its data and kill it
    kill_child(processes, pid, n_files_processed)

    # Get a new batch of project paths ready
    paths_batch = proj_paths[:batch]
    del proj_paths[:batch]

    print("[INFO] Starting new process {}".format(pid))
    p = Process(name='Process ' + str(pid), target=process_projects, args=(pid, paths_batch, processes[pid][1], global_queue, dirs_config))
    processes[pid][0] = p
    p.start()


def kill_child(processes, pid, n_files_processed):
    global file_count
    file_count += n_files_processed
    if processes[pid][0] is not None:
        processes[pid][0] = None
        processes[pid][1] += n_files_processed
        print("[INFO] Process {} finished, {} files processed {}. Current total: {}".format(pid, n_files_processed, processes[pid][1], file_count))


def active_process_count(processes):
    return len([p for p in processes if p[0] is not None])


if __name__ == '__main__':
    # Need to bypass javalang syntax tree traverse limits
    sys.setrecursionlimit(3000)

    inner_config, dirs_config = read_config("block_config.ini")
    PATH_stats_file_folder = dirs_config["stats_file_folder"]
    PATH_bookkeeping_proj_folder = dirs_config["bookkeeping_proj_folder"]
    PATH_tokens_file_folder = dirs_config["tokens_file_folder"]
    N_PROCESSES = inner_config["N_PROCESSES"]
    PROJECTS_BATCH = inner_config["PROJECTS_BATCH"]
    init_file_id = inner_config["init_file_id"]

    p_start = dt.datetime.now()

    proj_paths = []
    with open(inner_config["FILE_projects_list"], "r", encoding="utf-8") as f:
        proj_paths = f.read().split("\n")
    proj_paths = list(enumerate(proj_paths, start=1))
    # it will diverge the process flow on process_file()

    if os.path.exists(PATH_stats_file_folder) or os.path.exists(PATH_bookkeeping_proj_folder) or os.path.exists(PATH_tokens_file_folder):
        print(f'[ERROR] - Folder [{PATH_stats_file_folder}] or [{PATH_bookkeeping_proj_folder}] or [{PATH_tokens_file_folder}] already exists!')
        sys.exit(1)
    else:
        os.makedirs(PATH_stats_file_folder)
        os.makedirs(PATH_bookkeeping_proj_folder)
        os.makedirs(PATH_tokens_file_folder)

    # Multiprocessing with N_PROCESSES
    # [process, file_count]
    processes = [[None, init_file_id] for i in range(N_PROCESSES)]
    # The queue for processes to communicate back to the parent (this process)
    # Initialize it with N_PROCESSES number of (process_id, n_files_processed)
    global_queue = Queue()
    for i in range(N_PROCESSES):
        global_queue.put((i, 0))

    print("[INFO] *** Starting regular projects...")
    while len(proj_paths) > 0:
        start_child(processes, global_queue, proj_paths, PROJECTS_BATCH, dirs_config)

    print("[INFO] *** No more projects to process. Waiting for children to finish...")
    while active_process_count(processes) > 0:
        pid, n_files_processed = global_queue.get()
        kill_child(processes, pid, n_files_processed)

    p_elapsed = dt.datetime.now() - p_start
    print("[INFO] *** All done. %s files in %s" % (file_count, p_elapsed))
