#!/usr/bin/env python3

import collections
import datetime as dt
import hashlib
import os
import re
import sys
import zipfile
from configparser import ConfigParser
from multiprocessing import Process, Queue

MULTIPLIER = 50000000

N_PROCESSES = 2
PROJECTS_BATCH = 20
dirs_config = {}
dirs_config["projects_list"] = 'projects-list.txt'
dirs_config["priority_projects_list"] = None
dirs_config["stats_folder"] = 'files_stats'
dirs_config["bookkeeping_folder"] = 'bookkeeping_projs'
dirs_config["tokens_file"] = 'files_tokens'
language_config = {}
file_count = 0


def read_config():
    global N_PROCESSES, PROJECTS_BATCH
    global dirs_config
    global language_config
    global init_file_id
    global init_proj_id

    config = ConfigParser()

    # parse existing file
    try:
        config.read(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.ini'))
    except IOError:
        print('ERROR - config.ini not found')
        sys.exit()

    # Get info from config.ini into global variables
    N_PROCESSES = config.getint('Main', 'N_PROCESSES')
    PROJECTS_BATCH = config.getint('Main', 'PROJECTS_BATCH')
    dirs_config["projects_list"] = config.get('Main', 'FILE_projects_list')
    if config.has_option('Main', 'priority_projects_list'):
        dirs_config["priority_projects_list"] = config.get('Main', 'FILE_priority_projects')
    dirs_config["stats_folder"] = config.get('Folders/Files', 'PATH_stats_file_folder')
    dirs_config["bookkeeping_folder"] = config.get('Folders/Files', 'PATH_bookkeeping_proj_folder')
    dirs_config["tokens_file"] = config.get('Folders/Files', 'PATH_tokens_file_folder')

    # Reading Language settings
    language_config["separators"] = config.get('Language', 'separators').strip('"').split(' ')
    language_config["comment_inline"] = re.escape(config.get('Language', 'comment_inline'))
    language_config["comment_inline_pattern"] = language_config["comment_inline"] + '.*?$'
    language_config["comment_open_tag"] = re.escape(config.get('Language', 'comment_open_tag'))
    language_config["comment_close_tag"] = re.escape(config.get('Language', 'comment_close_tag'))
    language_config["comment_open_close_pattern"] = language_config["comment_open_tag"] + '.*?' + language_config["comment_close_tag"]
    language_config["file_extensions"] = config.get('Language', 'File_extensions').split(' ')
    # Reading config settings
    init_file_id = config.getint('Config', 'init_file_id')
    init_proj_id = config.getint('Config', 'init_proj_id')


def count_lines(string, count_empty = True):
    result = string.count('\n')
    if not string.endswith('\n') and (count_empty or string != ""):
        result += 1
    return result


def md5_hash(string):
    m = hashlib.md5()
    m.update(string.encode("utf-8"))
    return m.hexdigest()


def tokenize_files(file_string):
    h_time = dt.datetime.now()
    file_hash = md5_hash(file_string)
    hash_time = (dt.datetime.now() - h_time).microseconds
    lines = count_lines(file_string)
    file_string = "".join([s for s in file_string.splitlines(True) if s.strip()])

    loc = count_lines(file_string)

    re_time = dt.datetime.now()
    # Remove tagged comments
    file_string = re.sub(comment_open_close_pattern, '', file_string, flags=re.DOTALL)
    # Remove end of line comments
    file_string = re.sub(comment_inline_pattern, '', file_string, flags=re.MULTILINE)
    re_time = (dt.datetime.now() - re_time).microseconds

    file_string = "".join([s for s in file_string.splitlines(True) if s.strip()]).strip()
    sloc = file_string.count('\n')
    if file_string != '' and not file_string.endswith('\n'):
        sloc += 1
    final_stats = (file_hash, lines, loc, sloc)
    # Rather a copy of the file string here for tokenization
    file_string_for_tokenization = file_string
    # Transform separators into spaces (remove them)
    s_time = dt.datetime.now()
    for x in separators:
        file_string_for_tokenization = file_string_for_tokenization.replace(x, ' ')
    s_time = (dt.datetime.now() - s_time).microseconds
    # Create a list of tokens
    file_string_for_tokenization = file_string_for_tokenization.split()
    # Total number of tokens
    tokens_count_total = len(file_string_for_tokenization)
    # Count occurrences
    file_string_for_tokenization = collections.Counter(file_string_for_tokenization)
    # Converting Counter to dict because according to StackOverflow is better
    file_string_for_tokenization = dict(file_string_for_tokenization)
    # Unique number of tokens
    tokens_count_unique = len(file_string_for_tokenization)
    t_time = dt.datetime.now()
    # SourcererCC formatting
    tokens = ','.join(['{}@@::@@{}'.format(k, v) for k, v in file_string_for_tokenization.items()])
    t_time = (dt.datetime.now() - t_time).microseconds
    # MD5
    h_time = dt.datetime.now()
    tokens_hash = md5_hash(tokens)
    hash_time += (dt.datetime.now() - h_time).microseconds
    final_tokens = (tokens_count_total, tokens_count_unique, tokens_hash, '@#@' + tokens)
    return final_stats, final_tokens, [s_time, t_time, hash_time, re_time]


def process_file_contents(file_string, proj_id, file_id, container_path, file_path, file_bytes, proj_url, FILE_tokens_file, FILE_stats_file):
    global file_count

    file_count += 1
    (final_stats, final_tokens, file_parsing_times) = tokenize_files(file_string)
    (file_hash, lines, LOC, SLOC) = final_stats
    (tokens_count_total, tokens_count_unique, token_hash, tokens) = final_tokens
    file_url = proj_url + '/' + file_path[7:].replace(' ', '%20')
    file_path = os.path.join(container_path, file_path)
    ww_time = dt.datetime.now()
    FILE_stats_file.write(','.join([proj_id, str(file_id), '\"' + file_path + '\"', '\"' + file_url + '\"', '\"' + file_hash + '\"', file_bytes, str(lines), str(LOC), str(SLOC)]) + '\n')
    w_time = (dt.datetime.now() - ww_time).microseconds
    ww_time = dt.datetime.now()
    FILE_tokens_file.write(','.join([proj_id, str(file_id), str(tokens_count_total), str(tokens_count_unique), token_hash + tokens]) + '\n')
    w_time += (dt.datetime.now() - ww_time).microseconds
    return file_parsing_times + [w_time]  # [s_time, t_time, w_time, hash_time, re_time]


def process_zip_ball(process_num, zip_file, proj_id, proj_path, proj_url, base_file_id, FILE_tokens_file, FILE_bookkeeping_proj, FILE_stats_file):
    zip_time = file_time = string_time = tokens_time = hash_time = write_time = regex_time = 0
    print("[INFO] " + 'Attempting to process_zip_ball ' + zip_file)
    with zipfile.ZipFile(proj_path, 'r') as my_file:
        for file in my_file.infolist():
            if not os.path.splitext(file.filename)[1] in file_extensions:
                continue

            file_id = process_num * MULTIPLIER + base_file_id + file_count
            file_bytes = str(file.file_size)
            z_time = dt.datetime.now()
            try:
                my_zip_file = my_file.open(file.filename, 'r')
            except:
                print("[WARNING] Unable to open file (1) <" + os.path.join(proj_path, file.filename) + '> (process ' + str(process_num) + ')')
                break
            zip_time += (dt.datetime.now() - z_time).microseconds

            if my_zip_file is None:
                print("[WARNING] Unable to open file (2) <" + os.path.join(proj_path, file.filename) + '> (process ' + str(process_num) + ')')
                break

            f_time = dt.datetime.now()
            file_string = my_zip_file.read().decode("utf-8")
            file_time += (dt.datetime.now() - f_time).microseconds

            file_path = file.filename
            times = process_file_contents(file_string, proj_id, file_id, zip_file, file_path, file_bytes, proj_url, FILE_tokens_file, FILE_stats_file)
            string_time += times[0]
            tokens_time += times[1]
            write_time += times[4]
            hash_time += times[2]
            regex_time += times[3]
    print("[INFO] Successfully ran process_zip_ball {zip_file}")
    return zip_time, file_time, string_time, tokens_time, write_time, hash_time, regex_time


def process_one_project(process_num, proj_id, proj_path, base_file_id, FILE_tokens_file, FILE_bookkeeping_proj, FILE_stats_file):
    p_start = dt.datetime.now()
    print(f"[INFO] Starting  project <{proj_id},{proj_path}> (process {process_num})")
    if not os.path.isfile(proj_path):
        print(f"[WARNING] Unable to open project <{proj_id},{proj_path}> (process {process_num})")
        return

    proj_url = 'NULL'
    zip_file = proj_path
    times = process_zip_ball(process_num, zip_file, proj_id, proj_path, proj_url, base_file_id, FILE_tokens_file, FILE_bookkeeping_proj, FILE_stats_file)
    zip_time, file_time, string_time, tokens_time, write_time, hash_time, regex_time = (times if times is not None else (-1, -1, -1, -1, -1, -1, -1))

    FILE_bookkeeping_proj.write(proj_id + ',\"' + proj_path + '\",\"' + proj_url + '\"\n')
    p_elapsed = dt.datetime.now() - p_start
    print(f"[INFO] Project finished <{proj_id},{proj_path}> (process {proccess_num}))")
    print(f"[INFO]  ({proccess_num}): Total: {p_elapsed} ms")
    print(f"[INFO]      Zip: {zip_time}")
    print(f"[INFO]      Read: {file_time}")
    print(f"[INFO]      Separators: {string_time} ms")
    print(f"[INFO]      Tokens: {tokens_time} ms")
    print(f"[INFO]      Write: {write_time} ms")
    print(f"[INFO]      Hash: {hash_time}")
    print(f"[INFO]      regex: {regex_time}")


def process_projects(process_num, list_projects, base_file_id, global_queue):
    file_files_stats_file = os.path.join(dirs_config["stats_folder"], 'files-stats-' + str(process_num) + '.stats')
    file_bookkeeping_proj_name = os.path.join(dirs_config["bookkeeping_folder"], 'bookkeeping-proj-{}.projs'.format(process_num))
    file_files_tokens_file = os.path.join(dirs_config["tokens_file"], 'files-tokens-{}.tokens'.format(process_num))

    global file_count
    file_count = 0
    with open(file_files_tokens_file, 'a+') as FILE_tokens, open(file_bookkeeping_proj_name, 'a+') as FILE_bookkeeping, open(file_files_stats_file, 'a+') as FILE_stats:
        print(f"[INFO] Process {process_num} starting")
        p_start = dt.datetime.now()
        for proj_id, proj_path in list_projects:
            process_one_project(process_num, str(proj_id), proj_path, base_file_id, FILE_tokens, FILE_bookkeeping, FILE_stats)

    p_elapsed = (dt.datetime.now() - p_start).seconds
    print(f"[INFO] Process {process_num} finished. {file_count} files in {p_elapsed}s.")

    # Let parent know
    global_queue.put((process_num, file_count))
    sys.exit(0)


def start_child(processes, global_queue, proj_paths, batch):
    # This is a blocking get. If the queue is empty, it waits
    pid, n_files_processed = global_queue.get()
    # OK, one of the processes finished. Let's get its data and kill it
    kill_child(processes, pid, n_files_processed)

    # Get a new batch of project paths ready
    paths_batch = proj_paths[:batch]
    del proj_paths[:batch]

    print("Starting new process %s" % pid)
    p = Process(name='Process ' + str(pid), target=process_projects,
                args=(pid, paths_batch, processes[pid][1], global_queue))
    processes[pid][0] = p
    p.start()


def kill_child(processes, pid, n_files_processed):
    global file_count
    file_count += n_files_processed
    if processes[pid][0] is not None:
        processes[pid][0] = None
        processes[pid][1] += n_files_processed
        print("Process %s finished, %s files processed (%s). Current total: %s" % (
            pid, n_files_processed, processes[pid][1], file_count))


def active_process_count(processes):
    return len(list(filter(lambda p: p[0] is not None, processes)))


if __name__ == '__main__':
    try:
        read_config()
    except Exception as e:
        print(e)
        sys.exit()
    p_start = dt.datetime.now()

    prio_proj_paths = []
    if dirs_config["priority_projects_list"] is not None:
        with open(dirs_config["priority_projects_list"]) as f:
            for line in f:
                line_split = line.strip('\n')
                prio_proj_paths.append(line_split)
        prio_proj_paths = zip(range(init_proj_id, len(prio_proj_paths) + init_proj_id), prio_proj_paths)

    proj_paths = []
    with open(FILE_projects_list) as f:
        for line in f:
            proj_paths.append(line.strip("\n"))
    proj_paths = list(zip(range(1, len(proj_paths) + 1), proj_paths))

    if os.path.exists(dirs_config["stats_folder"]) or os.path.exists(dirs_config["bookkeeping_folder"]) or os.path.exists(dirs_config["tokens_file"]):
        missing_files = filter(os.path.exists, [dirs_config["stats_folder"], dirs_config["bookkeeping_folder"], dirs_config["tokens_file"]])
        print('ERROR - Folder [' + '] or ['.join(missing_files) + '] already exists!')
        sys.exit(1)
    else:
        os.makedirs(dirs_config["stats_folder"])
        os.makedirs(dirs_config["bookkeeping_folder"])
        os.makedirs(dirs_config["tokens_file"])

    # Split list of projects into N_PROCESSES lists
    # proj_paths_list = [ proj_paths[i::N_PROCESSES] for i in xrange(N_PROCESSES) ]

    # Multiprocessing with N_PROCESSES
    # [process, file_count]
    processes = [[None, init_file_id] for i in range(N_PROCESSES)]
    # Multiprocessing shared variable instance for recording file_id
    # file_id_global_var = Value('i', 1)
    # The queue for processes to communicate back to the parent (this process)
    # Initialize it with N_PROCESSES number of (process_id, n_files_processed)
    global_queue = Queue()
    for i in range(N_PROCESSES):
        global_queue.put((i, 0))

    # Start the priority projects
    print("*** Starting priority projects...")
    while len(prio_proj_paths) > 0:
        start_child(processes, global_queue, prio_proj_paths, 1)

    # Start all other projects
    print("*** Starting regular projects...")
    while len(proj_paths) > 0:
        start_child(processes, global_queue, proj_paths, PROJECTS_BATCH)

    print("*** No more projects to process. Waiting for children to finish...")
    while active_process_count(processes) > 0:
        pid, n_files_processed = global_queue.get()
        kill_child(processes, pid, n_files_processed)

    p_elapsed = dt.datetime.now() - p_start
    print("*** All done. %s files in %s" % (file_count, p_elapsed))
